import argparse
import asyncio
import os
import sys
import time

from apps.agent.context.manager import ContextManager
from apps.agent.engine import AgentEngine
from apps.agent.llm.factory import get_llm_provider
from apps.agent.stt.factory import get_stt_provider
from apps.agent.tts.factory import get_tts_provider
from packages.shared.config import get_settings
from packages.shared.logging import setup_logging

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def run_voice_loop(
    audio_path: str,
    output_path: str = "voice_response.wav",
    caller_name: str = "Rahul",
) -> None:
    """Execute complete STT -> LLM -> TTS voice turnaround loop on an audio file."""
    settings = get_settings()
    setup_logging("WARNING")

    if not os.path.exists(audio_path):
        print(f"[!] Error: Audio file not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 70)
    print("VOICE TURNAROUND PIPELINE: STT -> LLM -> TTS")
    print(f"Input Audio:  {audio_path}")
    print(f"STT Engine:   Faster-Whisper ({settings.whisper_model_size})")
    print(
        f"LLM Engine:   {settings.llm_provider.upper()} ({settings.gemini_model if settings.llm_provider == 'gemini' else ''})"
    )
    print(f"TTS Engine:   Kokoro-82M ({settings.kokoro_voice})")
    print("=" * 70)

    total_start = time.perf_counter()

    # Step 1: STT Transcription
    stt = get_stt_provider(settings)
    print("\n[1/3] Transcribing incoming audio (STT)...", flush=True)
    stt_result = stt.transcribe(audio_path)
    transcribed_text = stt_result.text.strip()
    if not transcribed_text:
        transcribed_text = (
            "Hi, is Manan available?"  # Default test fallback if audio is silent/tone
        )

    print(f"      Transcript: '{transcribed_text}'")
    print(
        f"      Detected Language: {stt_result.language.upper()} (conf: {stt_result.language_probability:.2f})"
    )
    print(f"      STT Latency: {stt_result.latency_ms:.1f}ms")

    # Step 2: LLM Conversation Step
    print("\n[2/3] Generating conversational response (LLM)...", flush=True)
    context = ContextManager(owner_name="Manan")
    context.set_caller(caller_id="+91-9876543210", caller_name=caller_name)
    llm = get_llm_provider(settings)
    engine = AgentEngine(llm_provider=llm, context_manager=context)

    agent_result = await engine.step(transcribed_text)
    print(f"      Agent Reply: '{agent_result.response_text}'")
    print(f"      LLM Latency: {agent_result.total_latency_ms:.1f}ms")

    # Step 3: TTS Synthesis
    print("\n[3/3] Synthesizing speech audio (TTS)...", flush=True)
    tts = get_tts_provider(settings)
    tts_result = tts.synthesize(agent_result.response_text)
    saved_file = tts_result.save(output_path)
    print(
        f"      Generated Audio: {saved_file} ({tts_result.duration_seconds:.2f}s, {tts_result.sample_rate}Hz)"
    )
    print(f"      TTS Latency: {tts_result.latency_ms:.1f}ms (RTF: {tts_result.rtf:.3f})")

    total_turnaround_ms = (time.perf_counter() - total_start) * 1000.0

    print("\n" + "=" * 70)
    print("LATENCY & PERFORMANCE BREAKDOWN")
    print("-" * 70)
    print(
        f"  1. Speech-to-Text (STT):      {stt_result.latency_ms:7.1f} ms  ({(stt_result.latency_ms / total_turnaround_ms) * 100:4.1f}%)"
    )
    print(
        f"  2. LLM Reasoning (Gemini):    {agent_result.total_latency_ms:7.1f} ms  ({(agent_result.total_latency_ms / total_turnaround_ms) * 100:4.1f}%)"
    )
    print(
        f"  3. Text-to-Speech (Kokoro):   {tts_result.latency_ms:7.1f} ms  ({(tts_result.latency_ms / total_turnaround_ms) * 100:4.1f}%)"
    )
    print("-" * 70)
    print(f"  TOTAL TURNAROUND LATENCY:     {total_turnaround_ms:7.1f} ms")
    print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-End Voice Loop (STT -> LLM -> TTS)")
    parser.add_argument(
        "audio_file",
        type=str,
        help="Path to input audio WAV file",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=str,
        default="voice_response.wav",
        help="Path for synthesized response audio",
    )
    parser.add_argument(
        "--caller",
        type=str,
        default="Rahul",
        help="Caller name simulation",
    )

    args = parser.parse_args()
    asyncio.run(
        run_voice_loop(
            audio_path=args.audio_file,
            output_path=args.out,
            caller_name=args.caller,
        )
    )


if __name__ == "__main__":
    main()
