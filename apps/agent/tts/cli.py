import argparse
import sys

from apps.agent.tts.kokoro import KokoroTTSProvider
from packages.shared.config import get_settings

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    """CLI tool for local text-to-speech synthesis using Kokoro-82M."""
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Local Text-to-Speech Synthesis using Kokoro-82M")
    parser.add_argument(
        "text",
        type=str,
        help="Text to synthesize",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output.wav",
        help="Output WAV file path (default: output.wav)",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=settings.kokoro_voice,
        help=f"Kokoro voice name (af_heart, af_bella, am_adam, etc.) [default: {settings.kokoro_voice}]",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=settings.kokoro_speed,
        help="Speech speed multiplier (default: 1.0)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("KOKORO-82M LOCAL TEXT-TO-SPEECH")
    print(f"Voice:  {args.voice} | Speed: {args.speed}")
    print(f"Text:   {args.text}")
    print("=" * 60)

    try:
        provider = KokoroTTSProvider(
            default_voice=args.voice,
            model_dir=settings.kokoro_model_dir,
        )

        result = provider.synthesize(
            text=args.text,
            voice=args.voice,
            speed=args.speed,
        )

        saved_path = result.save(args.output)

        print(f"\n[Audio]     Generated: {saved_path}")
        print(
            f"[Audio]     Sample Rate: {result.sample_rate}Hz | Duration: {result.duration_seconds:.2f}s"
        )
        print(f"[Timing]    Synthesis Latency: {result.latency_ms:.1f}ms")
        print(f"[Speed]     Real-Time Factor: {result.rtf:.3f} (< 1.0 is faster than real-time)")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n[!] Synthesis error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
