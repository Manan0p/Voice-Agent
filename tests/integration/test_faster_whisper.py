import os

import pytest

from apps.agent.stt.whisper import FasterWhisperProvider


@pytest.mark.integration
def test_faster_whisper_live_transcription() -> None:
    """Verify live faster-whisper transcription on a sample audio file."""
    audio_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "audio", "sample_en.wav")
    if not os.path.exists(audio_path):
        pytest.skip("Audio fixture not found")

    provider = FasterWhisperProvider(model_size="tiny", device="auto")
    result = provider.transcribe(audio_path)

    assert result.duration > 0.0
    assert result.latency_ms > 0.0
    assert result.rtf > 0.0
    assert result.language is not None
