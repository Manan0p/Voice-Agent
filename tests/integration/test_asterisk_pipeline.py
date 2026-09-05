"""Integration tests for AsteriskVoicePipelineRunner coordinating ARI events and Pipecat pipelines."""

from unittest.mock import AsyncMock

import pytest

from apps.agent.llm.mock import MockLLMProvider
from apps.agent.stt.mock import MockSTTProvider
from apps.agent.telephony.asterisk_ari import AsteriskARIClient
from apps.agent.telephony.asterisk_pipeline import AsteriskVoicePipelineRunner
from apps.agent.telephony.state_machine import CallState
from apps.agent.tts.mock import MockTTSProvider
from apps.agent.voice.pipeline import VoicePipelineBuilder
from packages.schemas.asterisk import (
    AsteriskCallerID,
    AsteriskChannel,
    ChannelHangupRequestEvent,
    StasisEndEvent,
    StasisStartEvent,
)


@pytest.fixture
def mock_pipeline_builder() -> VoicePipelineBuilder:
    return VoicePipelineBuilder(
        stt_provider=MockSTTProvider(default_text="Hello, I am calling for Manan."),
        llm_provider=MockLLMProvider(
            default_response="Namaste! Main Manan ka AI assistant bol raha hoon."
        ),
        tts_provider=MockTTSProvider(),
    )


@pytest.mark.asyncio
async def test_runner_stasis_start_and_end_lifecycle(
    mock_pipeline_builder: VoicePipelineBuilder,
) -> None:
    ari_client = AsteriskARIClient()
    ari_client.answer_channel = AsyncMock(return_value=True)
    ari_client.hangup_channel = AsyncMock(return_value=True)

    runner = AsteriskVoicePipelineRunner(
        ari_client=ari_client,
        pipeline_builder=mock_pipeline_builder,
        auto_answer=True,
    )

    channel = AsteriskChannel(
        id="channel-pjsip-001",
        name="PJSIP/1001-00000001",
        state="Ring",
        caller=AsteriskCallerID(name="Test User", number="+919876543210"),
    )

    # 1. Trigger StasisStart
    start_event = StasisStartEvent(
        application="voice_agent_app",
        channel=channel,
        args=["voice_agent_app"],
    )
    await runner.on_stasis_start(start_event)

    assert "channel-pjsip-001" in runner.active_sessions
    session = runner.active_sessions["channel-pjsip-001"]
    assert session.state == CallState.CONNECTED
    assert session.phone_number == "+919876543210"
    assert "channel-pjsip-001" in runner.active_bridges
    assert "channel-pjsip-001" in runner.active_tasks

    ari_client.answer_channel.assert_called_once_with("channel-pjsip-001")

    # 2. Push inbound audio
    pcm_audio = b"\x00\x00" * 320
    pushed = await runner.push_inbound_audio("channel-pjsip-001", pcm_audio)
    assert pushed is True

    # 3. Check session status
    status = runner.get_session_status("channel-pjsip-001")
    assert status is not None
    assert status["state"] == CallState.CONNECTED.value
    assert status["caller_phone"] == "+919876543210"

    # 4. Trigger StasisEnd
    end_event = StasisEndEvent(
        application="voice_agent_app",
        channel=channel,
    )
    await runner.on_stasis_end(end_event)

    assert "channel-pjsip-001" not in runner.active_sessions
    assert "channel-pjsip-001" not in runner.active_bridges
    assert "channel-pjsip-001" not in runner.active_tasks


@pytest.mark.asyncio
async def test_runner_hangup_request_cleanup(
    mock_pipeline_builder: VoicePipelineBuilder,
) -> None:
    ari_client = AsteriskARIClient()
    ari_client.answer_channel = AsyncMock(return_value=True)

    runner = AsteriskVoicePipelineRunner(
        ari_client=ari_client,
        pipeline_builder=mock_pipeline_builder,
        auto_answer=True,
    )

    channel = AsteriskChannel(
        id="channel-pjsip-002",
        name="PJSIP/1002-00000002",
        state="Ring",
        caller=AsteriskCallerID(name="Caller Two", number="+911122334455"),
    )

    start_event = StasisStartEvent(
        application="voice_agent_app",
        channel=channel,
    )
    await runner.on_stasis_start(start_event)
    assert "channel-pjsip-002" in runner.active_sessions

    # Trigger Hangup Request
    hangup_event = ChannelHangupRequestEvent(
        application="voice_agent_app",
        channel=channel,
        cause=16,
    )
    await runner.on_hangup_request(hangup_event)

    assert "channel-pjsip-002" not in runner.active_sessions
    assert "channel-pjsip-002" not in runner.active_bridges
