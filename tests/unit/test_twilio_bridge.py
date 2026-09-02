import json

from apps.agent.telephony.state_machine import CallState, TelephonyCallSession
from apps.agent.telephony.twilio_bridge import TwilioMediaStreamBridge


def test_generate_twiml_xml() -> None:
    """Verify TwiML XML formatting with Stream instruction."""
    twiml = TwilioMediaStreamBridge.generate_twiml(
        stream_url="wss://api.example.com/api/telephony/twilio/stream",
        welcome_greeting="Hello from AI Voice Agent",
    )
    assert "<Response>" in twiml
    assert '<Stream url="wss://api.example.com/api/telephony/twilio/stream"/>' in twiml
    assert "<Say>Hello from AI Voice Agent</Say>" in twiml


def test_twilio_bridge_event_handling() -> None:
    """Verify Twilio Media Streams incoming event parsing."""
    session = TelephonyCallSession(call_sid="test_call_sid")
    bridge = TwilioMediaStreamBridge(session=session)

    # 1. Connected Event
    res_conn = bridge.handle_inbound_message(json.dumps({"event": "connected", "protocol": "Call"}))
    assert res_conn["event"] == "connected"

    # 2. Start Event
    start_payload = {
        "event": "start",
        "streamSid": "MZ_123",
        "start": {
            "callSid": "CA_456",
            "accountSid": "AC_789",
            "customParameters": {"From": "+91-9876543210"},
        },
    }
    res_start = bridge.handle_inbound_message(json.dumps(start_payload))
    assert res_start["event"] == "start"
    assert res_start["call_sid"] == "CA_456"
    assert session.stream_sid == "MZ_123"
    assert session.phone_number == "+91-9876543210"
    assert session.state == CallState.CONNECTED

    # 3. Media Event
    media_payload = {
        "event": "media",
        "streamSid": "MZ_123",
        "media": {
            "payload": "////////",  # base64 mu-law
            "track": "inbound",
            "chunk": "1",
        },
    }
    res_media = bridge.handle_inbound_message(json.dumps(media_payload))
    assert res_media["event"] == "media"
    assert len(res_media["pcm16_bytes"]) > 0
    assert session.packet_count_in == 1
    assert session.state == CallState.STREAMING

    # 4. Stop Event
    res_stop = bridge.handle_inbound_message(json.dumps({"event": "stop", "streamSid": "MZ_123"}))
    assert res_stop["event"] == "stop"
    assert session.state == CallState.COMPLETED


def test_twilio_bridge_outbound_framing_and_clear() -> None:
    """Verify creation of media frames and barge-in clear messages."""
    frames = TwilioMediaStreamBridge.create_media_frames(
        pcm_or_mulaw_audio=b"\x00" * 320,
        stream_sid="MZ_123",
        is_already_mulaw=True,
    )
    assert len(frames) == 2
    parsed_first = json.loads(frames[0])
    assert parsed_first["event"] == "media"
    assert parsed_first["streamSid"] == "MZ_123"

    clear_msg = TwilioMediaStreamBridge.create_clear_message(stream_sid="MZ_123")
    parsed_clear = json.loads(clear_msg)
    assert parsed_clear["event"] == "clear"
    assert parsed_clear["streamSid"] == "MZ_123"
