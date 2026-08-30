import io
import math
import struct
import wave
from typing import Any

from apps.agent.tts.base import TTSProvider, TTSResult


class MockTTSProvider(TTSProvider):
    """Deterministic Mock TTS Provider generating synthetic audio for unit testing."""

    def __init__(self, sample_rate: int = 24000) -> None:
        self.sample_rate = sample_rate
        self.synthesize_calls: list[str] = []

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
        **kwargs: Any,
    ) -> TTSResult:
        """Generate a simulated 16-bit PCM WAV audio."""
        self.synthesize_calls.append(text)
        duration_seconds = max(0.5, len(text.split()) * 0.3)
        num_samples = int(self.sample_rate * duration_seconds)

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)

            # Generate gentle 440Hz tone
            frames = bytearray()
            for i in range(num_samples):
                t = i / self.sample_rate
                s = 0.2 * math.sin(2.0 * math.pi * 440.0 * t)
                val = int(s * 32767.0)
                frames.extend(struct.pack("<h", val))
            wf.writeframes(frames)

        wav_bytes = buffer.getvalue()
        return TTSResult(
            audio_bytes=wav_bytes,
            sample_rate=self.sample_rate,
            duration_seconds=duration_seconds,
            latency_ms=15.0,
        )
