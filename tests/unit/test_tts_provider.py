import os
import tempfile

import numpy as np

from apps.agent.tts.base import TTSResult, samples_to_wav_bytes
from apps.agent.tts.factory import get_tts_provider
from apps.agent.tts.mock import MockTTSProvider
from packages.shared.config import Settings


def test_samples_to_wav_bytes() -> None:
    """Verify converting float32 numpy audio samples to WAV bytes."""
    samples = np.sin(np.linspace(0, 2 * np.pi * 440, 24000, dtype=np.float32))
    wav_bytes = samples_to_wav_bytes(samples, sample_rate=24000)
    assert len(wav_bytes) > 0
    assert wav_bytes[:4] == b"RIFF"


def test_tts_result_save_and_rtf() -> None:
    """Verify TTSResult save method and RTF calculation."""
    wav_bytes = b"RIFFfakebytes"
    result = TTSResult(
        audio_bytes=wav_bytes,
        sample_rate=24000,
        duration_seconds=2.0,
        latency_ms=400.0,
    )
    assert result.rtf == 0.20

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        saved = result.save(tmp_path)
        assert os.path.exists(saved)
        assert os.path.getsize(saved) == len(wav_bytes)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_mock_tts_provider() -> None:
    """Verify MockTTSProvider generates valid WAV output and tracks calls."""
    mock = MockTTSProvider(sample_rate=24000)
    result = mock.synthesize("Hello from testing!")
    assert result.duration_seconds > 0.0
    assert result.latency_ms > 0.0
    assert len(result.audio_bytes) > 0
    assert result.audio_bytes[:4] == b"RIFF"
    assert len(mock.synthesize_calls) == 1


def test_tts_factory_mock() -> None:
    """Verify factory returns MockTTSProvider when configured."""
    settings = Settings(tts_provider="mock")
    provider = get_tts_provider(settings)
    assert isinstance(provider, MockTTSProvider)


def test_hinglish_phonetic_preprocessing() -> None:
    """Verify Romanized Hindi words are phonetically mapped for Kokoro."""
    from apps.agent.tts.phonetics import preprocess_hinglish_for_tts

    sample = "Namaste! Aapka swagat hai, bataiyega."
    processed = preprocess_hinglish_for_tts(sample)
    assert "Nuh-muh-stay" in processed
    assert "swaa-gut" in processed
    assert "buh-taa-ee-yay-gah" in processed
