import json
import time

import numpy as np

from apps.agent.telephony.codecs import chunk_audio, mulaw_to_base64, pcm_to_mulaw_bytes


class TelephonyCallSimulator:
    """Simulates an incoming telephone call and client-side Twilio media streaming for testing."""

    def __init__(
        self,
        call_sid: str = "CA_simulated_call_123",
        stream_sid: str = "MZ_simulated_stream_123",
        caller_number: str = "+91-9876543210",
    ) -> None:
        self.call_sid = call_sid
        self.stream_sid = stream_sid
        self.caller_number = caller_number

    def create_connect_event(self) -> str:
        """Simulate initial Twilio 'connected' event."""
        return json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"})

    def create_start_event(self) -> str:
        """Simulate Twilio 'start' event with metadata."""
        return json.dumps(
            {
                "event": "start",
                "streamSid": self.stream_sid,
                "start": {
                    "accountSid": "AC_simulated_account",
                    "streamSid": self.stream_sid,
                    "callSid": self.call_sid,
                    "tracks": ["inbound"],
                    "mediaFormat": {
                        "encoding": "audio/x-mulaw",
                        "sampleRate": 8000,
                        "channels": 1,
                    },
                    "customParameters": {
                        "From": self.caller_number,
                        "To": "+91-9876543210",
                    },
                },
            }
        )

    def create_audio_frames_from_sine(
        self,
        duration_sec: float = 0.5,
        freq_hz: float = 440.0,
    ) -> list[str]:
        """Generate simulated caller speech audio frames (sine wave encoded to mu-law)."""
        num_samples = int(8000 * duration_sec)
        t = np.linspace(0, duration_sec, num_samples, endpoint=False)
        audio = 0.5 * np.sin(2 * np.pi * freq_hz * t)
        mulaw = pcm_to_mulaw_bytes(audio, source_sample_rate=8000)

        frames = []
        for idx, chunk in enumerate(chunk_audio(mulaw, chunk_size_bytes=160)):
            msg = {
                "event": "media",
                "sequenceNumber": str(idx + 1),
                "streamSid": self.stream_sid,
                "media": {
                    "track": "inbound",
                    "chunk": str(idx + 1),
                    "timestamp": str(int(time.time() * 1000)),
                    "payload": mulaw_to_base64(chunk),
                },
            }
            frames.append(json.dumps(msg))
        return frames

    def create_stop_event(self) -> str:
        """Simulate call hangup stop event."""
        return json.dumps(
            {
                "event": "stop",
                "streamSid": self.stream_sid,
                "stop": {
                    "accountSid": "AC_simulated_account",
                    "callSid": self.call_sid,
                },
            }
        )
