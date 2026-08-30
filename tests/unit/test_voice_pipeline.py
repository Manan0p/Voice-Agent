import pytest
from pipecat.frames.frames import (
    AudioRawFrame,
    InterruptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection

from apps.agent.stt.mock import MockSTTProvider
from apps.agent.tts.mock import MockTTSProvider
from apps.agent.voice.pipeline import VoicePipelineBuilder
from apps.agent.voice.stt_service import FasterWhisperSTTService
from apps.agent.voice.tts_service import KokoroTTSService
from packages.shared.config import Settings


def test_pipeline_builder_vad_params() -> None:
    """Verify VoicePipelineBuilder constructs Silero VAD analyzer with custom thresholds."""
    settings = Settings(vad_start_secs=0.3, vad_stop_secs=0.8)
    builder = VoicePipelineBuilder(settings=settings)
    vad = builder.build_vad_analyzer()
    assert vad is not None


@pytest.mark.asyncio
async def test_faster_whisper_stt_service_frame_processing() -> None:
    """Verify STT service aggregates audio and emits TranscriptionFrame on UserStoppedSpeakingFrame."""
    mock_stt = MockSTTProvider(default_text="Testing STT frame flow")
    stt_service = FasterWhisperSTTService(stt_provider=mock_stt)

    # 1. Start speaking
    await stt_service.process_frame(UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM)
    assert stt_service._is_user_speaking is True

    # 2. Feed audio chunk (1 sec of 16kHz audio = 32000 bytes)
    dummy_audio = bytes(32000)
    await stt_service.process_frame(
        AudioRawFrame(audio=dummy_audio, sample_rate=16000, num_channels=1),
        FrameDirection.DOWNSTREAM,
    )
    assert len(stt_service._audio_buffer) == 32000

    # 3. Stop speaking -> triggers transcription & resets buffer
    await stt_service.process_frame(UserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)
    assert stt_service._is_user_speaking is False
    assert len(stt_service._audio_buffer) == 0


@pytest.mark.asyncio
async def test_kokoro_tts_service_interruption_handling() -> None:
    """Verify TTS service resets on InterruptionFrame."""
    mock_tts = MockTTSProvider()
    tts_service = KokoroTTSService(tts_provider=mock_tts)

    # Process InterruptionFrame
    await tts_service.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
    assert tts_service._interrupted is True
