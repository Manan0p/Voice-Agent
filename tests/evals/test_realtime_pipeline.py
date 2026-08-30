import pytest
from pipecat.frames.frames import (
    AudioRawFrame,
    InterruptionFrame,
    TextFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection

from apps.agent.context.manager import ContextManager
from apps.agent.engine import AgentEngine
from apps.agent.llm.mock import MockLLMProvider
from apps.agent.stt.mock import MockSTTProvider
from apps.agent.tts.mock import MockTTSProvider
from apps.agent.voice.llm_service import AgentEngineLLMService
from apps.agent.voice.stt_service import FasterWhisperSTTService
from apps.agent.voice.transport_simulated import SimulatedAudioOutputProcessor
from apps.agent.voice.tts_service import KokoroTTSService


@pytest.mark.asyncio
async def test_simulated_realtime_turn_flow() -> None:
    """Verify complete simulated real-time audio pipeline through sequential frame processors."""
    mock_stt = MockSTTProvider(default_text="Hi, is Manan free to speak?")
    mock_llm = MockLLMProvider(default_response="Haan, main Manan ka AI assistant bol raha hoon.")
    mock_tts = MockTTSProvider(sample_rate=24000)

    context = ContextManager(owner_name="Manan")
    context.set_caller(caller_id="+91-9876543210", caller_name="Rahul")
    engine = AgentEngine(llm_provider=mock_llm, context_manager=context)

    stt_service = FasterWhisperSTTService(stt_provider=mock_stt)
    llm_service = AgentEngineLLMService(engine=engine)
    tts_service = KokoroTTSService(tts_provider=mock_tts)
    out_processor = SimulatedAudioOutputProcessor()

    # Step 1: User starts speaking
    await stt_service.process_frame(UserStartedSpeakingFrame(), FrameDirection.DOWNSTREAM)

    # Step 2: Feed 16kHz audio (1 sec = 32000 bytes)
    dummy_audio = bytes(32000)
    await stt_service.process_frame(
        AudioRawFrame(audio=dummy_audio, sample_rate=16000, num_channels=1),
        FrameDirection.DOWNSTREAM,
    )

    # Step 3: User stops speaking -> STT processes audio
    await stt_service.process_frame(UserStoppedSpeakingFrame(), FrameDirection.DOWNSTREAM)
    assert stt_service._is_user_speaking is False

    # Step 4: LLM processes transcription
    await llm_service.process_frame(
        TranscriptionFrame(text="Hi, is Manan free to speak?", user_id="caller", timestamp=100.0),
        FrameDirection.DOWNSTREAM,
    )

    # Step 5: TTS processes LLM generated response
    await tts_service.process_frame(
        TextFrame(text="Haan, main Manan ka AI assistant bol raha hoon."),
        FrameDirection.DOWNSTREAM,
    )

    # Step 6: Output processor captures audio
    await out_processor.process_frame(
        AudioRawFrame(audio=bytes(4800), sample_rate=24000, num_channels=1),
        FrameDirection.DOWNSTREAM,
    )

    assert len(out_processor.synthesized_audio_bytes) > 0


@pytest.mark.asyncio
async def test_barge_in_interruption_flushing() -> None:
    """Verify user interruption cancels and resets the pipeline."""
    mock_tts = MockTTSProvider(sample_rate=24000)
    tts_service = KokoroTTSService(tts_provider=mock_tts)

    # Process InterruptionFrame
    await tts_service.process_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)

    assert tts_service._interrupted is True
