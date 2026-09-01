import asyncio
import sys

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams, VADState
from pipecat.frames.frames import (
    EndFrame,
    InputAudioRawFrame,
    TextFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask

from apps.agent.context.manager import ContextManager
from apps.agent.engine import AgentEngine
from apps.agent.voice.llm_service import AgentEngineLLMService
from apps.agent.voice.stt_service import FasterWhisperSTTService
from apps.agent.voice.transport_sounddevice import (
    SoundDeviceInputProcessor,
    SoundDeviceOutputProcessor,
)
from apps.agent.voice.tts_service import KokoroTTSService
from packages.shared.config import get_settings
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.voice.runner")

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class LiveVoiceAgentRunner:
    """Runs a live interactive voice agent with acoustic echo suppression."""

    def __init__(self, caller_name: str = "User") -> None:
        self.settings = get_settings()
        self.caller_name = caller_name
        self.context = ContextManager(owner_name="Manan")
        self.context.set_caller(caller_id="+91-9876543210", caller_name=caller_name)

    async def run(self) -> None:
        """Run the real-time voice pipeline loop until interrupted."""
        print("\n" + "=" * 70, flush=True)
        print("🎙️  PERSONAL AI VOICE AGENT — LIVE REAL-TIME PIPELINE (Phase 4)", flush=True)
        print(
            f"📡 LLM:  {self.settings.llm_provider.upper()} ({self.settings.gemini_model if self.settings.llm_provider == 'gemini' else ''})",
            flush=True,
        )
        print(f"🎙️ STT:  Faster-Whisper ({self.settings.whisper_model_size})", flush=True)
        print(f"🗣️ TTS:  Kokoro-82M ({self.settings.kokoro_voice})", flush=True)
        print(f"👤 User: {self.caller_name} (+91-9876543210)", flush=True)
        print("=" * 70, flush=True)
        print("Ready! Speak naturally into your microphone. (Ctrl+C to exit)\n", flush=True)

        engine = AgentEngine(context_manager=self.context)
        input_proc = SoundDeviceInputProcessor(sample_rate=self.settings.audio_input_sample_rate)
        output_proc = SoundDeviceOutputProcessor(sample_rate=self.settings.audio_output_sample_rate)

        stt_service = FasterWhisperSTTService()
        llm_service = AgentEngineLLMService(engine=engine)
        tts_service = KokoroTTSService()

        vad_params = VADParams(
            confidence=0.6,
            start_secs=self.settings.vad_start_secs,
            stop_secs=self.settings.vad_stop_secs,
            min_volume=0.04,
        )
        vad_analyzer = SileroVADAnalyzer(
            sample_rate=self.settings.audio_input_sample_rate,
            params=vad_params,
        )
        vad_analyzer.set_sample_rate(self.settings.audio_input_sample_rate)

        pipeline = Pipeline(
            [
                stt_service,
                llm_service,
                tts_service,
                output_proc,
            ]
        )

        task = PipelineTask(
            pipeline,
            params=PipelineParams(allow_interruptions=True, enable_metrics=True),
        )
        runner = PipelineRunner()

        input_proc.start()
        output_proc.start()
        loop = asyncio.get_running_loop()

        # Send initial spoken greeting
        async def send_greeting() -> None:
            await asyncio.sleep(0.5)
            greeting = "Hello! I am Manan's AI voice assistant. How can I help you today?"
            print(f"\n🤖 [Agent]: {greeting}", flush=True)
            await task.queue_frame(TextFrame(text=greeting))

        asyncio.create_task(send_greeting())

        async def feed_mic_to_pipeline() -> None:
            try:
                while input_proc._running:
                    chunk = await loop.run_in_executor(None, input_proc.get_chunk)

                    # Acoustic Echo Suppression: Ignore microphone input while agent is actively speaking
                    if output_proc.is_playing:
                        continue

                    frame = InputAudioRawFrame(
                        audio=chunk,
                        sample_rate=self.settings.audio_input_sample_rate,
                        num_channels=1,
                    )
                    # Run VAD analysis on 16kHz audio
                    vad_state = await vad_analyzer.analyze_audio(chunk)
                    if vad_state == VADState.STARTING:
                        print("\n🎙️ [Listening: User speaking...]", flush=True)
                        await task.queue_frame(UserStartedSpeakingFrame())
                    elif vad_state == VADState.STOPPING:
                        print("⏳ [Processing speech...]", flush=True)
                        await task.queue_frame(UserStoppedSpeakingFrame())

                    await task.queue_frame(frame)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("Microphone feeder error: %s", str(e), exc_info=True)

        feeder_task = asyncio.create_task(feed_mic_to_pipeline())

        try:
            await runner.run(task)
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("\n[Voice Agent Stopped]", flush=True)
        finally:
            feeder_task.cancel()
            input_proc.stop()
            output_proc.stop()
            try:
                await task.queue_frame(EndFrame())
            except Exception:
                pass
