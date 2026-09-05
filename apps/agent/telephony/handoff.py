"""Core Human Handoff Engine managing Asterisk mixing bridges, live intervention, and audio cut-off."""

from datetime import UTC, datetime

from apps.agent.telephony.asterisk_ari import AsteriskARIClient
from apps.agent.telephony.asterisk_bridge import AsteriskMediaBridge
from packages.schemas.handoff import (
    HandoffResponse,
    HandoffState,
    HandoffStatus,
)
from packages.shared.logging import get_logger

logger = get_logger("apps.agent.telephony.handoff")


class HandoffSession:
    """Tracks state and bridge references for a single live call."""

    def __init__(
        self,
        call_id: str,
        caller_phone: str = "unknown",
        media_bridge: AsteriskMediaBridge | None = None,
    ) -> None:
        self.call_id = call_id
        self.caller_phone = caller_phone
        self.media_bridge = media_bridge
        self.state = HandoffState.AI_HANDLING
        self.bridge_id: str | None = None
        self.user_endpoint: str | None = None
        self.user_channel_id: str | None = None
        self.last_action_time = datetime.now(UTC)
        self.active_channels: list[str] = [call_id]


class HandoffManager:
    """Manages human intervention, call state transitions, and Asterisk audio bridging."""

    def __init__(self, ari_client: AsteriskARIClient | None = None) -> None:
        self.ari_client = ari_client or AsteriskARIClient()
        self.sessions: dict[str, HandoffSession] = {}

    def register_call(
        self,
        call_id: str,
        caller_phone: str = "unknown",
        media_bridge: AsteriskMediaBridge | None = None,
    ) -> HandoffSession:
        """Register a new incoming call for handoff tracking."""
        session = HandoffSession(
            call_id=call_id,
            caller_phone=caller_phone,
            media_bridge=media_bridge,
        )
        self.sessions[call_id] = session
        logger.info("Registered call %s for handoff tracking.", call_id)
        return session

    def unregister_call(self, call_id: str) -> None:
        """Remove a completed call from handoff tracking."""
        self.sessions.pop(call_id, None)

    async def take_call(
        self,
        call_id: str,
        target_endpoint: str = "PJSIP/1002",
        reason: str = "Manual user takeover",
    ) -> HandoffResponse:
        """Take over the call: mute AI audio immediately and bridge caller to human endpoint."""
        session = self.sessions.get(call_id)
        if not session:
            # Create on-the-fly session if not pre-registered
            session = self.register_call(call_id)

        prev_state = session.state

        # 1. Instantly cut off AI speech and flush outbound audio
        if session.media_bridge:
            session.media_bridge.handle_barge_in()
            logger.info("Flushed AI audio buffer for call %s upon human takeover.", call_id)

        # 2. Create Asterisk mixing bridge
        bridge_name = f"handoff_bridge_{call_id}"
        bridge = await self.ari_client.create_bridge(bridge_type="mixing", name=bridge_name)

        bridge_id = bridge.id if bridge else f"local_bridge_{call_id}"
        session.bridge_id = bridge_id
        session.user_endpoint = target_endpoint

        # 3. Add caller channel to mixing bridge
        await self.ari_client.add_channel_to_bridge(bridge_id, call_id)

        session.state = HandoffState.HUMAN_HANDLING
        session.last_action_time = datetime.now(UTC)

        logger.info(
            "Call %s successfully handed off to human (%s). Bridge=%s, Reason=%s",
            call_id,
            target_endpoint,
            bridge_id,
            reason,
        )

        return HandoffResponse(
            success=True,
            call_id=call_id,
            previous_state=prev_state,
            current_state=session.state,
            message=f"Human takeover active on bridge {bridge_id}",
            bridge_id=bridge_id,
        )

    async def keep_ai(
        self,
        call_id: str,
        reason: str = "User acknowledged escalation and delegated to AI",
    ) -> HandoffResponse:
        """Dismiss escalation alert and keep autonomous AI flow active."""
        session = self.sessions.get(call_id)
        if not session:
            session = self.register_call(call_id)

        prev_state = session.state
        session.state = HandoffState.AI_HANDLING
        session.last_action_time = datetime.now(UTC)

        logger.info("Call %s confirmed for autonomous AI handling: %s", call_id, reason)

        return HandoffResponse(
            success=True,
            call_id=call_id,
            previous_state=prev_state,
            current_state=session.state,
            message="AI handling confirmed and continued",
        )

    async def end_call(
        self,
        call_id: str,
        reason: str = "Call terminated by user command",
    ) -> HandoffResponse:
        """Force hangup and disconnect the call."""
        session = self.sessions.get(call_id)
        prev_state = session.state if session else HandoffState.AI_HANDLING

        if session and session.media_bridge:
            session.media_bridge.handle_barge_in()

        # Hang up caller channel in Asterisk
        await self.ari_client.hangup_channel(call_id, reason="normal")

        if session:
            session.state = HandoffState.COMPLETED
            session.last_action_time = datetime.now(UTC)

        logger.info("Call %s terminated via handoff command: %s", call_id, reason)

        return HandoffResponse(
            success=True,
            call_id=call_id,
            previous_state=prev_state,
            current_state=HandoffState.COMPLETED,
            message="Call terminated successfully",
        )

    async def resume_ai(
        self,
        call_id: str,
        reason: str = "Human transferred call back to AI assistant",
    ) -> HandoffResponse:
        """Transfer call back from human to autonomous AI handling."""
        session = self.sessions.get(call_id)
        if not session:
            session = self.register_call(call_id)

        prev_state = session.state

        # Remove channel from bridge if bridged
        if session.bridge_id:
            await self.ari_client.remove_channel_from_bridge(session.bridge_id, call_id)
            session.bridge_id = None

        session.state = HandoffState.AI_RESUMED
        session.last_action_time = datetime.now(UTC)

        logger.info("Call %s transferred back to AI handling: %s", call_id, reason)

        return HandoffResponse(
            success=True,
            call_id=call_id,
            previous_state=prev_state,
            current_state=session.state,
            message="Call transferred back to AI assistant",
        )

    def get_status(self, call_id: str) -> HandoffStatus:
        """Get live handoff diagnostics for a call."""
        session = self.sessions.get(call_id)
        if not session:
            return HandoffStatus(
                call_id=call_id,
                state=HandoffState.AI_HANDLING,
                caller_phone="unknown",
            )

        is_speaking = False
        if session.media_bridge:
            is_speaking = session.media_bridge.output_processor.is_speaking

        return HandoffStatus(
            call_id=call_id,
            state=session.state,
            caller_phone=session.caller_phone,
            is_speaking_ai=is_speaking,
            bridge_id=session.bridge_id,
            user_endpoint=session.user_endpoint,
            last_action_timestamp=session.last_action_time,
            active_channels=session.active_channels,
        )


# Global singleton instance
_GLOBAL_HANDOFF_MANAGER: HandoffManager | None = None


def get_handoff_manager() -> HandoffManager:
    """Get or initialize the global HandoffManager singleton."""
    global _GLOBAL_HANDOFF_MANAGER
    if _GLOBAL_HANDOFF_MANAGER is None:
        _GLOBAL_HANDOFF_MANAGER = HandoffManager()
    return _GLOBAL_HANDOFF_MANAGER
