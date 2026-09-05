"""Pydantic schemas for Human Handoff and Live Call Intervention."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class HandoffState(StrEnum):
    """Lifecycle states of human handoff intervention."""

    AI_HANDLING = "ai_handling"
    USER_INVITED = "user_invited"
    HUMAN_HANDLING = "human_handling"
    AI_RESUMED = "ai_resumed"
    COMPLETED = "completed"


class HandoffActionType(StrEnum):
    """Supported handoff commands."""

    TAKE_CALL = "take_call"
    KEEP_AI = "keep_ai"
    END_CALL = "end_call"
    RESUME_AI = "resume_ai"


class HandoffRequest(BaseModel):
    """Request payload to execute a handoff command."""

    action: HandoffActionType
    target_endpoint: str | None = Field(
        default="PJSIP/1002",
        description="SIP or PSTN endpoint to bridge user to (e.g. 'PJSIP/1002' or '+919876543210')",
    )
    reason: str = Field(
        default="User manual takeover",
        description="Reason for the handoff action",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class HandoffResponse(BaseModel):
    """Response returned upon executing a handoff command."""

    success: bool
    call_id: str
    previous_state: HandoffState
    current_state: HandoffState
    message: str
    bridge_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HandoffStatus(BaseModel):
    """Detailed real-time diagnostic status of a call's handoff state."""

    call_id: str
    state: HandoffState
    caller_phone: str
    is_speaking_ai: bool = False
    bridge_id: str | None = None
    user_endpoint: str | None = None
    last_action_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    active_channels: list[str] = Field(default_factory=list)
