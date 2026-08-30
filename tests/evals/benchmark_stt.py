import os
import sys
import time

from apps.agent.stt.whisper import FasterWhisperProvider

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_stt_benchmark() -> None:
    """Benchmark faster-whisper model sizes on sample audio files."""
    fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "audio")
    sample_files = [
        ("English", os.path.join(fixtures_dir, "sample_en.wav")),
        ("Hindi", os.path.join(fixtures_dir, "sample_hi.wav")),
        ("Hinglish", os.path.join(fixtures_dir, "sample_hinglish.wav")),
        ("Noisy", os.path.join(fixtures_dir, "sample_noisy.wav")),
    ]

    models_to_test = ["tiny", "base"]

    print("\n" + "=" * 75, flush=True)
    print("FASTER-WHISPER MODEL BENCHMARKING REPORT", flush=True)
    print("=" * 75, flush=True)
    print(
        f"{'Model':<8} | {'Audio Type':<10} | {'Duration':<8} | {'Latency':<9} | {'RTF':<6} | {'Lang':<5} | {'Prob':<5}",
        flush=True,
    )
    print("-" * 75, flush=True)

    for model_name in models_to_test:
        load_start = time.perf_counter()
        provider = FasterWhisperProvider(model_size=model_name, device="auto")
        load_ms = (time.perf_counter() - load_start) * 1000.0
        print(f"[{model_name.upper()} model loaded in {load_ms:.0f}ms]", flush=True)

        for label, path in sample_files:
            if not os.path.exists(path):
                continue
            res = provider.transcribe(path)
            print(
                f"{model_name:<8} | {label:<10} | {res.duration:6.2f}s  | {res.latency_ms:6.1f}ms  | {res.rtf:5.3f} | {res.language:<5} | {res.language_probability:4.2f}",
                flush=True,
            )
        print("-" * 75, flush=True)

    print("=" * 75 + "\n", flush=True)


if __name__ == "__main__":
    run_stt_benchmark()
