"""Integration tests for carrier forwarded calls entering Asterisk voice agent."""

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
    StasisEndEvent,
    StasisStartEvent,
)


@pytest.fixture
def pipeline_builder() -> VoicePipelineBuilder:
    return VoicePipelineBuilder(
        stt_provider=MockSTTProvider(default_text="Hi, I am calling about a delivery."),
        llm_provider=MockLLMProvider(
            default_response="Haan ji, delivery ke regarding note kar liya hai."
        ),
        tts_provider=MockTTSProvider(),
    )


@pytest.mark.asyncio
async def test_carrier_forwarded_call_flow(
    pipeline_builder: VoicePipelineBuilder,
) -> None:
    ari_client = AsteriskARIClient()
    ari_client.answer_channel = AsyncMock(return_value=True)

    runner = AsteriskVoicePipelineRunner(
        ari_client=ari_client,
        pipeline_builder=pipeline_builder,
        auto_answer=True,
    )

    channel = AsteriskChannel(
        id="channel-trunk-001",
        name="PJSIP/trunk-endpoint-00000001",
        state="Ring",
        caller=AsteriskCallerID(name="Swiggy Delivery", number="9988776655"),
    )

    # StasisStartEvent with carrier forwarded headers in args:
    # args[0] = CallerID ('9988776655')
    # args[1] = Diversion ('<sip:+919876543210@airtel.in>;reason=unconditional')
    # args[2] = P-Asserted-Identity ('')
    # args[3] = Dialed DID ('+918000000000')
    start_event = StasisStartEvent(
        application="voice_agent_app",
        channel=channel,
        args=[
            "9988776655",
            "<sip:+919876543210@airtel.in>;reason=unconditional",
            "",
            "+918000000000",
        ],
    )

    await runner.on_stasis_start(start_event)

    assert "channel-trunk-001" in runner.active_sessions
    session = runner.active_sessions["channel-trunk-001"]

    # True caller normalized from 9988776655 -> +919988776655
    assert session.phone_number == "+919988776655"
    assert session.state == CallState.CONNECTED
    ari_client.answer_channel.assert_called_once_with("channel-trunk-001")

    # Push inbound audio chunk
    pcm_audio = b"\x00\x00" * 320
    pushed = await runner.push_inbound_audio("channel-trunk-001", pcm_audio)
    assert pushed is True

    # Check session status
    status = runner.get_session_status("channel-trunk-001")
    assert status is not None
    assert status["caller_phone"] == "+919988776655"
    assert status["state"] == CallState.CONNECTED.value

    # Hangup / End Stasis
    end_event = StasisEndEvent(
        application="voice_agent_app",
        channel=channel,
    )
    await runner.on_stasis_end(end_event)

    assert "channel-trunk-001" not in runner.active_sessions
    assert "channel-trunk-001" not in runner.active_bridges
