import os
import tempfile

import pytest

from apps.agent.context.manager import ContextManager
from apps.agent.engine import AgentEngine
from apps.agent.llm.mock import MockLLMProvider
from apps.agent.stt.mock import MockSTTProvider
from apps.agent.tts.mock import MockTTSProvider


@pytest.mark.asyncio
async def test_end_to_end_voice_turnaround() -> None:
    """Verify complete STT -> LLM -> TTS pipeline data flow and latency accounting."""
    # 1. Mock STT
    mock_stt = MockSTTProvider(
        default_text="Hi, can I speak to Manan regarding tomorrow's meeting?",
        default_language="en",
    )
    stt_res = mock_stt.transcribe("fake_input.wav")
    assert stt_res.text == "Hi, can I speak to Manan regarding tomorrow's meeting?"

    # 2. LLM Turn
    mock_llm = MockLLMProvider(
        default_response="Hi! Manan is currently unavailable, but I can take a message for him."
    )
    context = ContextManager(owner_name="Manan")
    context.set_caller(caller_id="+91-9876543210", caller_name="Rahul")
    engine = AgentEngine(llm_provider=mock_llm, context_manager=context)

    agent_res = await engine.step(stt_res.text)
    assert "Manan is currently unavailable" in agent_res.response_text

    # 3. TTS Synthesis
    mock_tts = MockTTSProvider(sample_rate=24000)
    tts_res = mock_tts.synthesize(agent_res.response_text)
    assert tts_res.duration_seconds > 0.0
    assert len(tts_res.audio_bytes) > 0

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name

    try:
        saved = tts_res.save(out_path)
        assert os.path.exists(saved)
        assert os.path.getsize(saved) > 100
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
