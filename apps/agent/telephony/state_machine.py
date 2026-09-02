import time
from dataclasses import dataclass, field
from enum import StrEnum


class CallState(StrEnum):
    """Lifecycle states of an inbound telephony session."""

    INITIATED = "initiated"
    RINGING = "ringing"
    CONNECTED = "connected"
    STREAMING = "streaming"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TelephonyCallSession:
    """State and telemetry container for an active phone call session."""

    call_sid: str
    phone_number: str = "unknown"
    stream_sid: str | None = None
    account_sid: str | None = None
    state: CallState = CallState.INITIATED
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    # Telemetry and stats
    packet_count_in: int = 0
    packet_count_out: int = 0
    interruption_count: int = 0
    total_latency_ms: float = 0.0
    last_packet_ts: float = field(default_factory=time.time)

    def set_connected(self, stream_sid: str, account_sid: str | None = None) -> None:
        """Transition call to connected state."""
        self.stream_sid = stream_sid
        self.account_sid = account_sid
        self.state = CallState.CONNECTED
        self.last_packet_ts = time.time()

    def record_inbound_packet(self) -> None:
        """Update inbound audio frame statistics."""
        self.packet_count_in += 1
        if self.state == CallState.CONNECTED:
            self.state = CallState.STREAMING
        self.last_packet_ts = time.time()

    def record_outbound_packet(self) -> None:
        """Update outbound audio frame statistics."""
        self.packet_count_out += 1
        self.last_packet_ts = time.time()

    def record_interruption(self) -> None:
        """Record a barge-in interruption event."""
        self.interruption_count += 1
        self.state = CallState.INTERRUPTED

    def complete(self) -> None:
        """Conclude call session."""
        self.end_time = time.time()
        self.state = CallState.COMPLETED

    @property
    def duration_sec(self) -> float:
        """Calculate total call duration."""
        end = self.end_time or time.time()
        return max(0.0, end - self.start_time)
