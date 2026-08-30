import sys

from apps.agent.tts.kokoro import KokoroTTSProvider
from packages.shared.config import get_settings

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_tts_benchmark() -> None:
    """Benchmark Kokoro TTS across representative English, Hindi, and Hinglish sentences."""
    settings = get_settings()

    test_sentences = [
        ("Short English", "Hi, I am Manan's AI assistant."),
        ("Phone Response", "Manan is currently unavailable, but I can take a message for him."),
        ("Hinglish Mirroring", "Haan bhai, kal Wednesday meeting ke baare mein note kar liya hai."),
        ("Hindi Transliterated", "Namaste, Manan abhi free nahi hai. Main unhe bata dunga."),
        (
            "Long Dialogue",
            "Hello Rahul, thanks for calling. I have recorded your message regarding the staging deployment update.",
        ),
    ]

    voices_to_test = ["af_bella", "af_sarah", "am_adam"]

    print("\n" + "=" * 80, flush=True)
    print("KOKORO-82M TTS BENCHMARKING REPORT", flush=True)
    print("=" * 80, flush=True)
    print(
        f"{'Voice':<10} | {'Test Case':<20} | {'Audio Dur':<10} | {'Latency':<10} | {'RTF':<7} | {'Sample Rate':<11}",
        flush=True,
    )
    print("-" * 80, flush=True)

    provider = KokoroTTSProvider(model_dir=settings.kokoro_model_dir)

    for voice in voices_to_test:
        for label, text in test_sentences:
            try:
                res = provider.synthesize(text=text, voice=voice)
                print(
                    f"{voice:<10} | {label:<20} | {res.duration_seconds:6.2f}s    | {res.latency_ms:6.1f}ms   | {res.rtf:5.3f} | {res.sample_rate}Hz",
                    flush=True,
                )
            except Exception as e:
                print(f"{voice:<10} | {label:<20} | ERROR: {e}", flush=True)
        print("-" * 80, flush=True)

    print("=" * 80 + "\n", flush=True)


if __name__ == "__main__":
    run_tts_benchmark()
