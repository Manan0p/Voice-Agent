import io
import os
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class TTSResult:
    """Result container for text-to-speech audio synthesis."""

    audio_bytes: bytes
    sample_rate: int = 24000
    duration_seconds: float = 0.0
    latency_ms: float = 0.0
    samples: np.ndarray | None = None

    @property
    def rtf(self) -> float:
        """Real-Time Factor: synthesis latency / audio duration (<1.0 is faster than real-time)."""
        if self.duration_seconds <= 0:
            return 0.0
        return (self.latency_ms / 1000.0) / self.duration_seconds

    def save(self, filepath: str) -> str:
        """Save synthesized audio bytes to a WAV file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(self.audio_bytes)
        return filepath


def samples_to_wav_bytes(samples: np.ndarray, sample_rate: int = 24000) -> bytes:
    """Convert float32 numpy audio samples [-1.0, 1.0] to 16-bit PCM WAV bytes."""
    # Clamp and convert to 16-bit int
    clamped = np.clip(samples, -1.0, 1.0)
    pcm16 = (clamped * 32767.0).astype(np.int16)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16.tobytes())

    return buffer.getvalue()


class TTSProvider(ABC):
    """Abstract interface for Text-to-Speech synthesis backends."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        **kwargs: Any,
    ) -> TTSResult:
        """Synthesize input text to speech audio."""
        ...
