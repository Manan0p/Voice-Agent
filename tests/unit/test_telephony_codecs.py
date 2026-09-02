import numpy as np

from apps.agent.telephony.codecs import (
    base64_to_mulaw,
    chunk_audio,
    mulaw_to_base64,
    mulaw_to_pcm16_bytes,
    pcm_to_mulaw_bytes,
)


def test_pcm_to_mulaw_and_back_roundtrip() -> None:
    """Verify that Linear PCM can be encoded to mu-law and decoded back cleanly."""
    # Generate 1 second of 440Hz sine wave @ 24kHz (Kokoro TTS output format)
    t = np.linspace(0, 1.0, 24000, endpoint=False)
    original_audio = 0.5 * np.sin(2 * np.pi * 440.0 * t).astype(np.float32)

    # 1. Encode 24kHz PCM to 8kHz mu-law
    mulaw_bytes = pcm_to_mulaw_bytes(original_audio, source_sample_rate=24000)
    assert len(mulaw_bytes) == 8000  # 1 second @ 8kHz

    # 2. Decode 8kHz mu-law to 16kHz PCM (Whisper STT input format)
    pcm16_bytes = mulaw_to_pcm16_bytes(mulaw_bytes, target_sample_rate=16000)
    assert len(pcm16_bytes) == 16000 * 2  # 16000 samples * 2 bytes/sample (int16)

    # Verify audio content is non-silent
    pcm16_np = np.frombuffer(pcm16_bytes, dtype=np.int16)
    max_amp = np.max(np.abs(pcm16_np))
    assert max_amp > 5000


def test_chunk_audio_frames() -> None:
    """Verify chunk_audio produces exact 160-byte 20ms frames."""
    # 500 bytes of audio
    raw_audio = b"\x55" * 500
    chunks = list(chunk_audio(raw_audio, chunk_size_bytes=160))

    # 500 / 160 = 3.125 -> 4 chunks (last chunk padded to 160)
    assert len(chunks) == 4
    for chunk in chunks:
        assert len(chunk) == 160


def test_base64_conversions() -> None:
    """Verify base64 audio payload encoding and decoding."""
    test_bytes = b"\x01\x02\x03\x04\x05\xff\xaa"
    b64 = mulaw_to_base64(test_bytes)
    assert isinstance(b64, str)

    decoded = base64_to_mulaw(b64)
    assert decoded == test_bytes
