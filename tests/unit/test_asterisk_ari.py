"""Unit tests for Asterisk REST Interface (ARI) client and event dispatcher."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.agent.telephony.asterisk_ari import AsteriskARIClient
from packages.schemas.asterisk import (
    AsteriskBridge,
    AsteriskChannel,
    ChannelHangupRequestEvent,
    ChannelStateChangeEvent,
    StasisEndEvent,
    StasisStartEvent,
)


@pytest.fixture
def sample_stasis_start_payload() -> str:
    return json.dumps(
        {
            "type": "StasisStart",
            "application": "voice_agent_app",
            "timestamp": "2026-09-05T12:00:00.000+0000",
            "channel": {
                "id": "channel-12345",
                "name": "PJSIP/1001-00000001",
                "state": "Ring",
                "caller": {"name": "Test Caller", "number": "+919876543210"},
                "connected": {"name": "", "number": ""},
                "creationtime": "2026-09-05T12:00:00.000+0000",
                "language": "en",
                "dialplan": {"context": "from-internal", "exten": "1000", "priority": 1},
            },
            "args": ["voice_agent_app"],
        }
    )


@pytest.fixture
def sample_stasis_end_payload() -> str:
    return json.dumps(
        {
            "type": "StasisEnd",
            "application": "voice_agent_app",
            "timestamp": "2026-09-05T12:01:00.000+0000",
            "channel": {
                "id": "channel-12345",
                "name": "PJSIP/1001-00000001",
                "state": "Up",
                "caller": {"name": "Test Caller", "number": "+919876543210"},
            },
        }
    )


@pytest.fixture
def sample_state_change_payload() -> str:
    return json.dumps(
        {
            "type": "ChannelStateChange",
            "application": "voice_agent_app",
            "timestamp": "2026-09-05T12:00:05.000+0000",
            "channel": {
                "id": "channel-12345",
                "name": "PJSIP/1001-00000001",
                "state": "Up",
                "caller": {"name": "Test Caller", "number": "+919876543210"},
            },
        }
    )


@pytest.fixture
def sample_hangup_request_payload() -> str:
    return json.dumps(
        {
            "type": "ChannelHangupRequest",
            "application": "voice_agent_app",
            "timestamp": "2026-09-05T12:01:00.000+0000",
            "channel": {
                "id": "channel-12345",
                "name": "PJSIP/1001-00000001",
                "state": "Up",
                "caller": {"name": "Test Caller", "number": "+919876543210"},
            },
            "cause": 16,
        }
    )


@pytest.mark.asyncio
async def test_ari_client_init() -> None:
    client = AsteriskARIClient(
        base_url="http://127.0.0.1:8088",
        username="voice_agent",
        password="test_password",
        app_name="voice_agent_app",
    )
    assert client.base_url == "http://127.0.0.1:8088"
    assert client.username == "voice_agent"
    assert client.app_name == "voice_agent_app"
    assert len(client.active_channels) == 0


@pytest.mark.asyncio
async def test_dispatch_stasis_start_event(
    sample_stasis_start_payload: str,
) -> None:
    client = AsteriskARIClient()
    received_event = None

    async def on_stasis_start(event: StasisStartEvent) -> None:
        nonlocal received_event
        received_event = event

    client.on("StasisStart", on_stasis_start)
    await client._dispatch_raw_event(sample_stasis_start_payload)

    assert received_event is not None
    assert isinstance(received_event, StasisStartEvent)
    assert received_event.channel.id == "channel-12345"
    assert received_event.channel.caller.number == "+919876543210"
    assert "channel-12345" in client.active_channels
    assert client.active_channels["channel-12345"].state == "Ring"


@pytest.mark.asyncio
async def test_dispatch_stasis_end_event(
    sample_stasis_start_payload: str,
    sample_stasis_end_payload: str,
) -> None:
    client = AsteriskARIClient()
    await client._dispatch_raw_event(sample_stasis_start_payload)
    assert "channel-12345" in client.active_channels

    received_end_event = None

    async def on_stasis_end(event: StasisEndEvent) -> None:
        nonlocal received_end_event
        received_end_event = event

    client.on("StasisEnd", on_stasis_end)
    await client._dispatch_raw_event(sample_stasis_end_payload)

    assert received_end_event is not None
    assert isinstance(received_end_event, StasisEndEvent)
    assert "channel-12345" not in client.active_channels


@pytest.mark.asyncio
async def test_dispatch_channel_state_change(
    sample_stasis_start_payload: str,
    sample_state_change_payload: str,
) -> None:
    client = AsteriskARIClient()
    await client._dispatch_raw_event(sample_stasis_start_payload)
    assert client.active_channels["channel-12345"].state == "Ring"

    received_state_event = None

    async def on_state_change(event: ChannelStateChangeEvent) -> None:
        nonlocal received_state_event
        received_state_event = event

    client.on("ChannelStateChange", on_state_change)
    await client._dispatch_raw_event(sample_state_change_payload)

    assert received_state_event is not None
    assert received_state_event.channel.state == "Up"
    assert client.active_channels["channel-12345"].state == "Up"


@pytest.mark.asyncio
async def test_dispatch_channel_hangup_request(
    sample_hangup_request_payload: str,
) -> None:
    client = AsteriskARIClient()
    received_hangup_event = None

    async def on_hangup_req(event: ChannelHangupRequestEvent) -> None:
        nonlocal received_hangup_event
        received_hangup_event = event

    client.on("ChannelHangupRequest", on_hangup_req)
    await client._dispatch_raw_event(sample_hangup_request_payload)

    assert received_hangup_event is not None
    assert isinstance(received_hangup_event, ChannelHangupRequestEvent)
    assert received_hangup_event.cause == 16


@pytest.mark.asyncio
async def test_rest_answer_channel() -> None:
    client = AsteriskARIClient()
    mock_resp = MagicMock()
    mock_resp.status = 204
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.post.return_value = mock_resp
    client._session = mock_session

    success = await client.answer_channel("channel-12345")
    assert success is True
    mock_session.post.assert_called_once_with(
        "http://127.0.0.1:8088/ari/channels/channel-12345/answer"
    )


@pytest.mark.asyncio
async def test_rest_hangup_channel() -> None:
    client = AsteriskARIClient()
    client.active_channels["channel-12345"] = AsteriskChannel(
        id="channel-12345", name="PJSIP/1001-00000001"
    )

    mock_resp = MagicMock()
    mock_resp.status = 204
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.delete.return_value = mock_resp
    client._session = mock_session

    success = await client.hangup_channel("channel-12345", reason="normal")
    assert success is True
    assert "channel-12345" not in client.active_channels
    mock_session.delete.assert_called_once_with(
        "http://127.0.0.1:8088/ari/channels/channel-12345",
        params={"reason": "normal"},
    )


@pytest.mark.asyncio
async def test_rest_play_media() -> None:
    client = AsteriskARIClient()
    mock_resp = MagicMock()
    mock_resp.status = 201
    mock_resp.json = AsyncMock(return_value={"id": "playback-01", "state": "playing"})
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.post.return_value = mock_resp
    client._session = mock_session

    res = await client.play_media("channel-12345", "sound:hello-world")
    assert res == {"id": "playback-01", "state": "playing"}
    mock_session.post.assert_called_once_with(
        "http://127.0.0.1:8088/ari/channels/channel-12345/play",
        params={"media": "sound:hello-world"},
    )


@pytest.mark.asyncio
async def test_rest_bridge_lifecycle() -> None:
    client = AsteriskARIClient()

    # 1. Create bridge
    mock_resp_create = MagicMock()
    mock_resp_create.status = 200
    mock_resp_create.json = AsyncMock(
        return_value={
            "id": "bridge-999",
            "technology": "simple_bridge",
            "bridge_type": "mixing",
            "bridge_class": "default",
            "creator": "voice_agent_app",
            "name": "call_bridge",
            "channels": [],
        }
    )
    mock_resp_create.__aenter__.return_value = mock_resp_create
    mock_resp_create.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.post.return_value = mock_resp_create
    client._session = mock_session

    bridge = await client.create_bridge(name="call_bridge")
    assert isinstance(bridge, AsteriskBridge)
    assert bridge.id == "bridge-999"

    # 2. Add channel to bridge
    mock_resp_add = MagicMock()
    mock_resp_add.status = 204
    mock_resp_add.__aenter__.return_value = mock_resp_add
    mock_resp_add.__aexit__.return_value = None
    mock_session.post.return_value = mock_resp_add

    added = await client.add_channel_to_bridge("bridge-999", "channel-12345")
    assert added is True

    # 3. Remove channel from bridge
    mock_resp_rem = MagicMock()
    mock_resp_rem.status = 204
    mock_resp_rem.__aenter__.return_value = mock_resp_rem
    mock_resp_rem.__aexit__.return_value = None
    mock_session.post.return_value = mock_resp_rem

    removed = await client.remove_channel_from_bridge("bridge-999", "channel-12345")
    assert removed is True


@pytest.mark.asyncio
async def test_rest_external_media() -> None:
    client = AsteriskARIClient()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(
        return_value={
            "id": "external-channel-01",
            "name": "UnicastRTP/127.0.0.1:12345",
            "state": "Up",
        }
    )
    mock_resp.__aenter__.return_value = mock_resp
    mock_resp.__aexit__.return_value = None

    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.post.return_value = mock_resp
    client._session = mock_session

    chan = await client.external_media("127.0.0.1:12345", audio_format="slin16")
    assert isinstance(chan, AsteriskChannel)
    assert chan.id == "external-channel-01"
    assert chan.name == "UnicastRTP/127.0.0.1:12345"
