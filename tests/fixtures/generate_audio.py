import math
import os
import random
import struct
import wave


def generate_synthetic_speech_wav(
    filepath: str,
    duration_seconds: float = 3.0,
    sample_rate: int = 16000,
    add_noise: bool = False,
) -> str:
    """Generate a valid 16kHz mono PCM WAV file using pure Python wave & struct."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    num_samples = int(sample_rate * duration_seconds)

    frames = bytearray()
    phase = 0.0

    for i in range(num_samples):
        t = i / sample_rate
        # Simulating speech-like pitch variation (F0 around 130 Hz)
        f0 = 130.0 + 15.0 * math.sin(2.0 * math.pi * 2.0 * t)
        phase += 2.0 * math.pi * f0 / sample_rate

        # Multi-harmonic formant simulation
        s = (
            0.5 * math.sin(phase)
            + 0.3 * math.sin(3.8 * phase)
            + 0.2 * math.sin(11.5 * phase)
            + 0.1 * math.sin(19.2 * phase)
        )

        # Syllable cadence modulation (~3.5 Hz)
        syllable = max(0.0, math.sin(2.0 * math.pi * 3.5 * t)) ** 2
        s *= syllable

        if add_noise:
            s += (random.random() - 0.5) * 0.15

        # Clamp and convert to 16-bit PCM integer
        s_clamped = max(-1.0, min(1.0, s))
        val = int(s_clamped * 32767.0)
        frames.extend(struct.pack("<h", val))

    with wave.open(filepath, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)

    return filepath


def generate_all_sample_fixtures() -> dict[str, str]:
    """Generate baseline test audio fixtures in tests/fixtures/audio/."""
    fixtures_dir = os.path.join(os.path.dirname(__file__), "audio")
    os.makedirs(fixtures_dir, exist_ok=True)

    samples = {
        "en": os.path.join(fixtures_dir, "sample_en.wav"),
        "hi": os.path.join(fixtures_dir, "sample_hi.wav"),
        "hinglish": os.path.join(fixtures_dir, "sample_hinglish.wav"),
        "noisy": os.path.join(fixtures_dir, "sample_noisy.wav"),
    }

    generate_synthetic_speech_wav(samples["en"], duration_seconds=3.0, add_noise=False)
    generate_synthetic_speech_wav(samples["hi"], duration_seconds=3.5, add_noise=False)
    generate_synthetic_speech_wav(samples["hinglish"], duration_seconds=4.0, add_noise=False)
    generate_synthetic_speech_wav(samples["noisy"], duration_seconds=3.0, add_noise=True)

    return samples


if __name__ == "__main__":
    generated = generate_all_sample_fixtures()
    print("Successfully generated test audio fixtures:")
    for k, path in generated.items():
        print(f" - {k}: {path} ({os.path.getsize(path)} bytes)")
