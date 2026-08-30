from typing import Any

from apps.agent.stt.base import STTProvider, TranscriptionResult, TranscriptionSegment


class MockSTTProvider(STTProvider):
    """Deterministic Mock STT Provider for unit tests."""

    def __init__(
        self,
        default_text: str = "Hello, can I speak to Manan?",
        default_language: str = "en",
    ) -> None:
        self.default_text = default_text
        self.default_language = default_language
        self.transcribe_calls: list[Any] = []

    def transcribe(
        self,
        audio: str | bytes | Any,
        language: str | None = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        initial_prompt: str | None = None,
    ) -> TranscriptionResult:
        """Return simulated transcription result."""
        self.transcribe_calls.append(audio)
        return TranscriptionResult(
            text=self.default_text,
            language=language or self.default_language,
            language_probability=0.98,
            duration=2.5,
            latency_ms=12.0,
            segments=[
                TranscriptionSegment(
                    id=0,
                    start=0.0,
                    end=2.5,
                    text=self.default_text,
                    avg_logprob=-0.15,
                    no_speech_prob=0.01,
                )
            ],
        )
