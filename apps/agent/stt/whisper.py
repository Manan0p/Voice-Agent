import os
import sys
import time
from typing import Any

from faster_whisper import WhisperModel

from apps.agent.stt.base import STTProvider, TranscriptionResult, TranscriptionSegment
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.stt.whisper")


def _setup_windows_cuda_paths() -> None:
    """Add virtualenv nvidia site-packages DLL directories to Windows search path."""
    if sys.platform != "win32":
        return

    # Check site-packages for nvidia packages
    import site

    candidate_dirs = site.getsitepackages()
    for base in candidate_dirs:
        nvidia_base = os.path.join(base, "nvidia")
        if os.path.exists(nvidia_base):
            for sub in os.listdir(nvidia_base):
                bin_dir = os.path.join(nvidia_base, sub, "bin")
                if os.path.isdir(bin_dir):
                    if hasattr(os, "add_dll_directory"):
                        try:
                            os.add_dll_directory(bin_dir)
                        except Exception:
                            pass
                    if bin_dir not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")


class FasterWhisperProvider(STTProvider):
    """Faster-Whisper STT implementation using CTranslate2 with auto-device fallback."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        cpu_threads: int = 4,
    ) -> None:
        self.model_size = model_size
        self.requested_device = device
        self.requested_compute_type = compute_type
        self.cpu_threads = cpu_threads

        _setup_windows_cuda_paths()

        self.model, self.device, self.compute_type = self._init_model_with_fallback(
            model_size=self.model_size,
            device=self.requested_device,
            compute_type=self.requested_compute_type,
            cpu_threads=self.cpu_threads,
        )

    def _init_model_with_fallback(
        self,
        model_size: str,
        device: str,
        compute_type: str,
        cpu_threads: int,
    ) -> tuple[WhisperModel, str, str]:
        """Attempt CUDA initialization if DLLs are present, with fallback to CPU."""
        start = time.perf_counter()

        has_cuda_runtime = False
        if device in ("auto", "cuda"):
            import ctypes.util

            has_cuda_runtime = bool(
                ctypes.util.find_library("cublas64_12")
                or ctypes.util.find_library("cublas64_11")
                or ctypes.util.find_library("cublas")
            )
            if not has_cuda_runtime and device == "cuda":
                logger.warning("CUDA explicitly requested but cuBLAS DLL not detected.")
                has_cuda_runtime = True  # Try anyway if explicitly forced

        if has_cuda_runtime:
            try:
                ct = compute_type if compute_type != "auto" else "float16"
                logger.info("Initializing faster-whisper on CUDA (%s)...", ct)
                model = WhisperModel(
                    model_size_or_path=model_size,
                    device="cuda",
                    compute_type=ct,
                )
                load_time = (time.perf_counter() - start) * 1000.0
                logger.info("Faster-whisper verified on CUDA in %.1fms", load_time)
                return model, "cuda", ct
            except Exception as e:
                if device == "cuda":
                    raise
                logger.warning("CUDA initialization failed (%s); using CPU.", str(e))

        # CPU int8
        ct = compute_type if compute_type != "auto" else "int8"
        logger.info("Initializing faster-whisper on CPU (%s)...", ct)
        model = WhisperModel(
            model_size_or_path=model_size,
            device="cpu",
            compute_type=ct,
            cpu_threads=cpu_threads,
        )
        load_time = (time.perf_counter() - start) * 1000.0
        logger.info("Faster-whisper loaded on CPU in %.1fms", load_time)
        return model, "cpu", ct

    def transcribe(
        self,
        audio: str | bytes | Any,
        language: str | None = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        initial_prompt: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio input and return structured result with latency metrics."""
        if initial_prompt is None:
            initial_prompt = (
                "This is a bilingual conversation in English, Hindi, and Hinglish. "
                "Names and key vocabulary: Manan, Rahul, Namaste, meeting, call, message, "
                "available, urgent, schedule, note, phone, haan, nahi, baat."
            )

        start_time = time.perf_counter()
        try:
            segments_gen, info = self.model.transcribe(
                audio=audio,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                vad_parameters={"min_silence_duration_ms": 500},
                initial_prompt=initial_prompt,
            )

            segments: list[TranscriptionSegment] = []
            full_text_parts: list[str] = []

            for seg in segments_gen:
                seg_text = seg.text.strip()
                if not seg_text:
                    continue

                # Filter out known Whisper hallucination artifacts on short background noise
                lower_text = seg_text.lower().rstrip(".").strip()
                if lower_text in {
                    "thank you",
                    "thank you for watching",
                    "thank you very much",
                    "thanks for watching",
                    "subtitles by",
                    "amara.org",
                    "you",
                } and (seg.end - seg.start < 1.0):
                    logger.debug("Filtered Whisper silence hallucination: '%s'", seg_text)
                    continue

                segments.append(
                    TranscriptionSegment(
                        id=seg.id,
                        start=seg.start,
                        end=seg.end,
                        text=seg_text,
                        avg_logprob=seg.avg_logprob,
                        no_speech_prob=seg.no_speech_prob,
                    )
                )
                full_text_parts.append(seg_text)

            latency_ms = (time.perf_counter() - start_time) * 1000.0
            full_text = " ".join(full_text_parts)

            return TranscriptionResult(
                text=full_text,
                language=info.language,
                language_probability=info.language_probability,
                duration=info.duration,
                latency_ms=latency_ms,
                segments=segments,
            )
        except Exception as e:
            logger.error("Transcription error: %s", str(e))
            raise
