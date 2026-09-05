"""Unit tests for HandoffManager, state transitions, audio cut-off, and mixing bridge creation."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.agent.telephony.asterisk_ari import AsteriskARIClient
from apps.agent.telephony.asterisk_bridge import AsteriskMediaBridge
from apps.agent.telephony.handoff import HandoffManager
from packages.schemas.asterisk import AsteriskBridge
from packages.schemas.handoff import HandoffState


@pytest.fixture
def mock_ari_client() -> AsteriskARIClient:
    client = AsteriskARIClient()
    client.create_bridge = AsyncMock(
        return_value=AsteriskBridge(
            id="bridge-test-123",
            technology="simple_bridge",
            bridge_type="mixing",
            name="handoff_bridge_call-001",
        )
    )
    client.add_channel_to_bridge = AsyncMock(return_value=True)
    client.remove_channel_from_bridge = AsyncMock(return_value=True)
    client.hangup_channel = AsyncMock(return_value=True)
    return client


@pytest.mark.asyncio
async def test_handoff_register_and_get_status() -> None:
    manager = HandoffManager()
    session = manager.register_call("call-001", caller_phone="+919876543210")

    assert session.call_id == "call-001"
    assert session.state == HandoffState.AI_HANDLING

    status = manager.get_status("call-001")
    assert status.call_id == "call-001"
    assert status.caller_phone == "+919876543210"
    assert status.state == HandoffState.AI_HANDLING
    assert status.is_speaking_ai is False


@pytest.mark.asyncio
async def test_handoff_take_call_mutes_audio_and_creates_bridge(
    mock_ari_client: AsteriskARIClient,
) -> None:
    media_bridge = MagicMock(spec=AsteriskMediaBridge)
    media_bridge.output_processor = MagicMock()
    media_bridge.output_processor.is_speaking = True

    manager = HandoffManager(ari_client=mock_ari_client)
    manager.register_call("call-001", caller_phone="+919876543210", media_bridge=media_bridge)

    resp = await manager.take_call(
        call_id="call-001",
        target_endpoint="PJSIP/1002",
        reason="VIP Escalation",
    )

    assert resp.success is True
    assert resp.current_state == HandoffState.HUMAN_HANDLING
    assert resp.previous_state == HandoffState.AI_HANDLING
    assert resp.bridge_id == "bridge-test-123"

    # AI audio buffer must be flushed immediately
    media_bridge.handle_barge_in.assert_called_once()

    # Asterisk mixing bridge must be created and channel added
    mock_ari_client.create_bridge.assert_called_once_with(
        bridge_type="mixing", name="handoff_bridge_call-001"
    )
    mock_ari_client.add_channel_to_bridge.assert_called_once_with("bridge-test-123", "call-001")


@pytest.mark.asyncio
async def test_handoff_keep_ai(mock_ari_client: AsteriskARIClient) -> None:
    manager = HandoffManager(ari_client=mock_ari_client)
    manager.register_call("call-002", caller_phone="+911122334455")

    resp = await manager.keep_ai(call_id="call-002", reason="Dismissed urgency")
    assert resp.success is True
    assert resp.current_state == HandoffState.AI_HANDLING


@pytest.mark.asyncio
async def test_handoff_end_call(mock_ari_client: AsteriskARIClient) -> None:
    media_bridge = MagicMock(spec=AsteriskMediaBridge)
    manager = HandoffManager(ari_client=mock_ari_client)
    manager.register_call("call-003", caller_phone="+911122334455", media_bridge=media_bridge)

    resp = await manager.end_call(call_id="call-003", reason="User force hangup")
    assert resp.success is True
    assert resp.current_state == HandoffState.COMPLETED
    mock_ari_client.hangup_channel.assert_called_once_with("call-003", reason="normal")
    media_bridge.handle_barge_in.assert_called_once()


@pytest.mark.asyncio
async def test_handoff_resume_ai(mock_ari_client: AsteriskARIClient) -> None:
    manager = HandoffManager(ari_client=mock_ari_client)
    session = manager.register_call("call-004", caller_phone="+911122334455")
    session.bridge_id = "bridge-test-999"
    session.state = HandoffState.HUMAN_HANDLING

    resp = await manager.resume_ai(call_id="call-004", reason="Transfer back")
    assert resp.success is True
    assert resp.current_state == HandoffState.AI_RESUMED
    mock_ari_client.remove_channel_from_bridge.assert_called_once_with(
        "bridge-test-999", "call-004"
    )
