import argparse
import os
import sys

from apps.agent.stt.whisper import FasterWhisperProvider
from packages.shared.config import get_settings

# Ensure UTF-8 output on Windows console
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    """CLI tool for local audio transcription with faster-whisper."""
    settings = get_settings()

    parser = argparse.ArgumentParser(
        description="Local Speech-to-Text Transcription using faster-whisper"
    )
    parser.add_argument(
        "audio_file",
        type=str,
        help="Path to audio file (.wav, .mp3, .ogg, etc.)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=settings.whisper_model_size,
        help=f"Whisper model size (tiny, base, small, medium, large-v3) [default: {settings.whisper_model_size}]",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=settings.whisper_device,
        help=f"Compute device (auto, cuda, cpu) [default: {settings.whisper_device}]",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (en, hi, etc. or None for auto-detection)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.audio_file):
        print(f"[!] Error: Audio file not found: {args.audio_file}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 60)
    print("FASTER-WHISPER LOCAL TRANSCRIPTION")
    print(f"File:   {args.audio_file}")
    print(f"Model:  {args.model} | Device: {args.device}")
    print("=" * 60)

    try:
        provider = FasterWhisperProvider(
            model_size=args.model,
            device=args.device,
        )

        result = provider.transcribe(
            audio=args.audio_file,
            language=args.language,
        )

        print(
            f"\n[Language]  Detected: {result.language.upper()} (confidence: {result.language_probability:.2f})"
        )
        print(f"[Timing]    Duration: {result.duration:.2f}s | Latency: {result.latency_ms:.1f}ms")
        print(f"[Speed]     Real-Time Factor: {result.rtf:.3f} (< 1.0 is real-time)")
        print("\n" + "-" * 60)
        print("TRANSCRIPT:")
        print(f"{result.text if result.text else '(Silence or no distinct speech detected)'}")
        print("-" * 60)

        if result.segments:
            print("\nSEGMENTS:")
            for seg in result.segments:
                print(f"  [{seg.start:05.2f}s -> {seg.end:05.2f}s] {seg.text}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n[!] Transcription error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
