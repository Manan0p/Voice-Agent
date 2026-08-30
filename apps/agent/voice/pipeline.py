from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameProcessor

from apps.agent.context.manager import ContextManager
from apps.agent.engine import AgentEngine
from apps.agent.llm.base import LLMProvider
from apps.agent.stt.base import STTProvider
from apps.agent.tts.base import TTSProvider
from apps.agent.voice.llm_service import AgentEngineLLMService
from apps.agent.voice.stt_service import FasterWhisperSTTService
from apps.agent.voice.tts_service import KokoroTTSService
from packages.shared.config import Settings, get_settings
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.voice.pipeline")


class VoicePipelineBuilder:
    """Builder that constructs real-time voice pipelines with Silero VAD, STT, LLM, and TTS."""

    def __init__(
        self,
        settings: Settings | None = None,
        stt_provider: STTProvider | None = None,
        llm_provider: LLMProvider | None = None,
        tts_provider: TTSProvider | None = None,
        context_manager: ContextManager | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.stt_provider = stt_provider
        self.llm_provider = llm_provider
        self.tts_provider = tts_provider
        self.context = context_manager or ContextManager()

    def build_vad_analyzer(self) -> SileroVADAnalyzer:
        """Initialize Silero VAD with speech thresholds."""
        params = VADParams(
            start_secs=self.settings.vad_start_secs,
            stop_secs=self.settings.vad_stop_secs,
            min_volume=0.4,
        )
        vad = SileroVADAnalyzer(
            sample_rate=self.settings.audio_input_sample_rate,
            params=params,
        )
        vad.set_sample_rate(self.settings.audio_input_sample_rate)
        return vad

    def build_processors(
        self,
        output_processor: FrameProcessor,
    ) -> list[FrameProcessor]:
        """Construct sequential pipeline processors."""
        engine = AgentEngine(
            llm_provider=self.llm_provider,
            context_manager=self.context,
        )

        stt_service = FasterWhisperSTTService(stt_provider=self.stt_provider)
        llm_service = AgentEngineLLMService(engine=engine)
        tts_service = KokoroTTSService(tts_provider=self.tts_provider)

        return [
            stt_service,
            llm_service,
            tts_service,
            output_processor,
        ]

    def build_pipeline_task(
        self,
        processors: list[FrameProcessor],
        enable_interruptions: bool = True,
    ) -> PipelineTask:
        """Create Pipecat Pipeline and Task with interruption support."""
        pipeline = Pipeline(processors)
        params = PipelineParams(
            allow_interruptions=enable_interruptions,
            enable_metrics=True,
        )
        return PipelineTask(pipeline, params=params)
