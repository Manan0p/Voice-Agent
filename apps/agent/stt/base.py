from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TranscriptionSegment:
    """A single transcribed segment with timing and confidence data."""

    id: int
    start: float
    end: float
    text: str
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0


@dataclass
class TranscriptionResult:
    """Full result container from an STT transcription task."""

    text: str
    language: str = "en"
    language_probability: float = 1.0
    duration: float = 0.0
    latency_ms: float = 0.0
    segments: list[TranscriptionSegment] = field(default_factory=list)

    @property
    def rtf(self) -> float:
        """Real-Time Factor: processing time / audio duration (lower is better, <1.0 is realtime)."""
        if self.duration <= 0:
            return 0.0
        return (self.latency_ms / 1000.0) / self.duration


class STTProvider(ABC):
    """Abstract interface for Speech-to-Text inference backends."""

    @abstractmethod
    def transcribe(
        self,
        audio: str | bytes | Any,
        language: str | None = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        initial_prompt: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file, bytes buffer, or waveform."""
        ...
