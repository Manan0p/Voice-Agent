import json
from typing import Any

from apps.agent.telephony.codecs import (
    base64_to_mulaw,
    chunk_audio,
    mulaw_to_base64,
    mulaw_to_pcm16_bytes,
    pcm_to_mulaw_bytes,
)
from apps.agent.telephony.state_machine import TelephonyCallSession
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.telephony.twilio_bridge")


class TwilioMediaStreamBridge:
    """Handles Twilio Media Streams bidirectional WebSocket protocol and audio streaming."""

    def __init__(self, session: TelephonyCallSession | None = None) -> None:
        self.session = session

    @staticmethod
    def generate_twiml(
        stream_url: str,
        welcome_greeting: str | None = None,
    ) -> str:
        """Generate TwiML XML response instructing Twilio to establish a bidirectional Media Stream WebSocket."""
        # Clean URL to wss://
        ws_url = stream_url.replace("http://", "ws://").replace("https://", "wss://")
        twiml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<Response>"]

        if welcome_greeting:
            twiml_parts.append(f"  <Say>{welcome_greeting}</Say>")

        twiml_parts.append("  <Connect>")
        twiml_parts.append(f'    <Stream url="{ws_url}"/>')
        twiml_parts.append("  </Connect>")
        twiml_parts.append("</Response>")

        return "\n".join(twiml_parts)

    def handle_inbound_message(
        self,
        raw_message: str | bytes,
    ) -> dict[str, Any]:
        """Parse incoming JSON message from Twilio WebSocket."""
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8")

        try:
            event = json.loads(raw_message)
        except Exception as e:
            logger.error("Failed to parse Twilio WebSocket message: %s", e)
            return {"event": "error", "error": str(e)}

        event_type = event.get("event")

        if event_type == "connected":
            logger.info("Twilio media stream connected: protocol=%s", event.get("protocol"))
            return {"event": "connected", "protocol": event.get("protocol")}

        elif event_type == "start":
            start_data = event.get("start", {})
            call_sid = start_data.get("callSid", "unknown_call")
            stream_sid = event.get("streamSid") or start_data.get("streamSid", "unknown_stream")
            account_sid = start_data.get("accountSid")
            custom_params = start_data.get("customParameters", {})

            caller_phone = (
                custom_params.get("From") or custom_params.get("caller_number") or "unknown"
            )

            if self.session:
                self.session.call_sid = call_sid
                self.session.phone_number = caller_phone
                self.session.set_connected(stream_sid=stream_sid, account_sid=account_sid)

            logger.info("Twilio stream started: CallSid=%s, StreamSid=%s", call_sid, stream_sid)
            return {
                "event": "start",
                "call_sid": call_sid,
                "stream_sid": stream_sid,
                "caller_phone": caller_phone,
                "account_sid": account_sid,
                "custom_parameters": custom_params,
            }

        elif event_type == "media":
            media_data = event.get("media", {})
            payload_b64 = media_data.get("payload", "")
            track = media_data.get("track", "inbound")
            chunk_num = media_data.get("chunk", 0)

            # Decode mu-law audio
            mulaw_audio = base64_to_mulaw(payload_b64)
            # Transcode to 16kHz PCM for Whisper
            pcm16_audio = mulaw_to_pcm16_bytes(mulaw_audio, target_sample_rate=16000)

            if self.session:
                self.session.record_inbound_packet()

            return {
                "event": "media",
                "track": track,
                "chunk": chunk_num,
                "mulaw_bytes": mulaw_audio,
                "pcm16_bytes": pcm16_audio,
                "stream_sid": event.get("streamSid"),
            }

        elif event_type == "mark":
            mark_data = event.get("mark", {})
            name = mark_data.get("name")
            return {"event": "mark", "name": name, "stream_sid": event.get("streamSid")}

        elif event_type == "stop":
            if self.session:
                self.session.complete()
            logger.info("Twilio stream stopped: StreamSid=%s", event.get("streamSid"))
            return {"event": "stop", "stream_sid": event.get("streamSid")}

        return {"event": event_type, "raw": event}

    @staticmethod
    def create_media_frames(
        pcm_or_mulaw_audio: bytes | Any,
        stream_sid: str,
        source_sample_rate: int = 24000,
        is_already_mulaw: bool = False,
    ) -> list[str]:
        """Convert synthesized voice audio into standard 20ms Twilio Media frame JSON messages."""
        if not is_already_mulaw:
            mulaw_bytes = pcm_to_mulaw_bytes(
                pcm_or_mulaw_audio, source_sample_rate=source_sample_rate
            )
        else:
            mulaw_bytes = pcm_or_mulaw_audio

        frames = []
        for chunk in chunk_audio(mulaw_bytes, chunk_size_bytes=160):
            payload_b64 = mulaw_to_base64(chunk)
            msg = {
                "event": "media",
                "streamSid": stream_sid,
                "media": {
                    "payload": payload_b64,
                },
            }
            frames.append(json.dumps(msg))

        return frames

    @staticmethod
    def create_clear_message(stream_sid: str) -> str:
        """Create a Twilio clear message to immediately flush and cancel ongoing audio playback on barge-in."""
        msg = {
            "event": "clear",
            "streamSid": stream_sid,
        }
        return json.dumps(msg)

    @staticmethod
    def create_mark_message(stream_sid: str, mark_name: str) -> str:
        """Create a Twilio mark event message for playback sync tracking."""
        msg = {
            "event": "mark",
            "streamSid": stream_sid,
            "mark": {
                "name": mark_name,
            },
        }
        return json.dumps(msg)
