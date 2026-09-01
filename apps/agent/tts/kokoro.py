import os
import time
import urllib.request
from typing import Any

from kokoro_onnx import Kokoro

from apps.agent.tts.base import TTSProvider, TTSResult, samples_to_wav_bytes
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.tts.kokoro")

# Model and voices download URLs
KOKORO_MODEL_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx"
)
KOKORO_VOICES_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin"
)


def ensure_kokoro_model_files(model_dir: str = "models/kokoro") -> tuple[str, str]:
    """Ensure Kokoro ONNX model and voice files exist locally, downloading if necessary."""
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "kokoro-v0_19.onnx")
    voices_path = os.path.join(model_dir, "voices.bin")

    if not os.path.exists(model_path):
        logger.info("Downloading Kokoro ONNX model (82MB) from %s...", KOKORO_MODEL_URL)
        urllib.request.urlretrieve(KOKORO_MODEL_URL, model_path)
        logger.info("Kokoro model saved to %s", model_path)

    if not os.path.exists(voices_path):
        logger.info("Downloading Kokoro voices file from %s...", KOKORO_VOICES_URL)
        urllib.request.urlretrieve(KOKORO_VOICES_URL, voices_path)
        logger.info("Kokoro voices saved to %s", voices_path)

    return model_path, voices_path


class KokoroTTSProvider(TTSProvider):
    """Local Text-to-Speech provider using Kokoro-82M ONNX runtime."""

    def __init__(
        self,
        default_voice: str = "af_bella",
        model_dir: str = "models/kokoro",
    ) -> None:
        self.default_voice = default_voice
        self.model_dir = model_dir
        self.sample_rate = 24000

        model_path, voices_path = ensure_kokoro_model_files(self.model_dir)

        start = time.perf_counter()
        logger.info("Loading Kokoro TTS engine...")
        self.kokoro = Kokoro(model_path, voices_path)
        self.available_voices = set(self.kokoro.get_voices())
        load_time = (time.perf_counter() - start) * 1000.0
        logger.info(
            "Kokoro TTS initialized in %.1fms (voices: %s)", load_time, len(self.available_voices)
        )

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        **kwargs: Any,
    ) -> TTSResult:
        """Synthesize input text into 24kHz audio."""
        selected_voice = voice or self.default_voice
        if selected_voice not in self.available_voices:
            fallback = (
                "af_bella"
                if "af_bella" in self.available_voices
                else next(iter(self.available_voices))
            )
            logger.warning("Voice '%s' not found; using fallback '%s'.", selected_voice, fallback)
            selected_voice = fallback

        clean_text = text.strip()
        if not clean_text:
            return TTSResult(audio_bytes=b"", sample_rate=self.sample_rate)

        # Apply phonetic preprocessing for Indian English and Hinglish natural pronunciation
        from apps.agent.tts.phonetics import preprocess_hinglish_for_tts

        phonetic_text = preprocess_hinglish_for_tts(clean_text)

        start = time.perf_counter()
        try:
            samples, sample_rate = self.kokoro.create(
                text=phonetic_text,
                voice=selected_voice,
                speed=speed,
                lang="en-us",
            )

            latency_ms = (time.perf_counter() - start) * 1000.0
            duration_seconds = len(samples) / float(sample_rate)

            wav_bytes = samples_to_wav_bytes(samples, sample_rate=sample_rate)

            return TTSResult(
                audio_bytes=wav_bytes,
                sample_rate=sample_rate,
                duration_seconds=duration_seconds,
                latency_ms=latency_ms,
                samples=samples,
            )
        except Exception as e:
            logger.error("Kokoro synthesis error: %s", str(e))
            raise
