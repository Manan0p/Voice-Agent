import base64
from collections.abc import Generator

import numpy as np

# Standard G.711 mu-law decoding table
# Precomputed 8-bit to 16-bit linear PCM conversion
MULAW_TO_LINEAR = np.zeros(256, dtype=np.int16)
for i in range(256):
    inv = ~i & 0xFF
    sign = -1 if (inv & 0x80) else 1
    exponent = (inv >> 4) & 0x07
    mantissa = inv & 0x0F
    sample = sign * ((mantissa << (exponent + 3)) + (0x84 << exponent) - 0x84)
    MULAW_TO_LINEAR[i] = np.clip(sample, -32768, 32767)


def mulaw_to_pcm16_bytes(mulaw_bytes: bytes, target_sample_rate: int = 16000) -> bytes:
    """Convert 8kHz G.711 mu-law audio bytes into 16kHz 16-bit Linear PCM bytes."""
    if not mulaw_bytes:
        return b""

    # 1. Decode mu-law to 8kHz int16 PCM
    indices = np.frombuffer(mulaw_bytes, dtype=np.uint8)
    pcm_8k = MULAW_TO_LINEAR[indices]

    # 2. Resample from 8kHz to 16kHz if needed (2x linear interpolation)
    if target_sample_rate == 16000:
        # Fast 2x linear upsampling
        pcm_16k = np.repeat(pcm_8k, 2)
        return pcm_16k.astype(np.int16).tobytes()
    elif target_sample_rate == 8000:
        return pcm_8k.astype(np.int16).tobytes()

    # Generic ratio resampling
    ratio = target_sample_rate / 8000.0
    target_length = int(len(pcm_8k) * ratio)
    resampled = np.interp(
        np.linspace(0, len(pcm_8k), target_length, endpoint=False),
        np.arange(len(pcm_8k)),
        pcm_8k,
    )
    return resampled.astype(np.int16).tobytes()


def pcm_to_mulaw_bytes(
    pcm_audio: np.ndarray | bytes,
    source_sample_rate: int = 24000,
) -> bytes:
    """Convert Linear PCM audio (e.g. 24kHz float32 from Kokoro TTS) to 8kHz G.711 mu-law bytes."""
    # Convert bytes to numpy if needed
    if isinstance(pcm_audio, bytes):
        pcm_np = np.frombuffer(pcm_audio, dtype=np.int16).astype(np.float32) / 32768.0
    else:
        pcm_np = pcm_audio.astype(np.float32)

    if len(pcm_np) == 0:
        return b""

    # 1. Downsample to 8kHz
    if source_sample_rate != 8000:
        target_len = int(len(pcm_np) * (8000.0 / source_sample_rate))
        if target_len == 0:
            return b""
        indices = np.linspace(0, len(pcm_np), target_len, endpoint=False)
        pcm_8k = np.interp(indices, np.arange(len(pcm_np)), pcm_np)
    else:
        pcm_8k = pcm_np

    # 2. Scale float32 (-1.0 to 1.0) to int16 (-32768 to 32767)
    pcm_int16 = np.clip(pcm_8k * 32767.0, -32768, 32767).astype(np.int16)

    # 3. Encode to G.711 mu-law
    # Quantize: sign | exponent | mantissa
    sign = (pcm_int16 < 0).astype(np.uint8)
    magnitude = np.abs(pcm_int16) + 132  # Add bias
    magnitude = np.clip(magnitude, 0, 32767)

    # Exponent is log2 position of highest bit
    exponent = np.clip((np.floor(np.log2(np.maximum(magnitude, 1))) - 7).astype(np.int32), 0, 7)
    mantissa = ((magnitude >> (exponent + 3)) & 0x0F).astype(np.uint8)

    mulaw = ~((sign << 7) | (exponent.astype(np.uint8) << 4) | mantissa) & 0xFF
    return mulaw.astype(np.uint8).tobytes()


def chunk_audio(
    audio_bytes: bytes,
    chunk_size_bytes: int = 160,
) -> Generator[bytes, None, None]:
    """Chunk audio bytes into fixed-size telephony frames (e.g. 20ms = 160 bytes @ 8kHz mu-law)."""
    for i in range(0, len(audio_bytes), chunk_size_bytes):
        chunk = audio_bytes[i : i + chunk_size_bytes]
        if len(chunk) == chunk_size_bytes:
            yield chunk
        else:
            # Zero-pad final chunk to maintain telephony framing
            yield chunk + b"\x00" * (chunk_size_bytes - len(chunk))


def base64_to_mulaw(payload_b64: str) -> bytes:
    """Decode base64 payload from Twilio media frame."""
    return base64.b64decode(payload_b64)


def mulaw_to_base64(mulaw_bytes: bytes) -> str:
    """Encode mu-law bytes into base64 payload for Twilio media frame."""
    return base64.b64encode(mulaw_bytes).decode("ascii")
