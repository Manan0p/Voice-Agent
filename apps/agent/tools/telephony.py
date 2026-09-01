from typing import Any

from pydantic import BaseModel, Field

from apps.agent.tools.base import BaseTool, PermissionLevel, ToolResult


class TransferCallInput(BaseModel):
    """Input parameters for transferring a call to the user."""

    target: str = Field(
        default="owner", description="Transfer destination target: 'owner' or extension number."
    )
    reason: str = Field(description="Explanation of why the call is being escalated to the owner.")
    urgency: str = Field(default="high", description="Urgency priority of the transfer.")


class TransferCallTool(BaseTool):
    """Tool to initiate call escalation and transfer to the human user."""

    name = "transfer_call"
    description = "Transfer the active phone call directly to the user (e.g. for emergencies or important interviews)."
    permission_level = PermissionLevel.HIGH_RISK_WRITE
    args_schema = TransferCallInput

    def __init__(self) -> None:
        self.transfer_events: list[dict[str, Any]] = []

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Signal call transfer to telephony layer."""
        target = kwargs.get("target", "owner")
        reason = kwargs.get("reason", "").strip()
        urgency = kwargs.get("urgency", "high")

        if not reason:
            return ToolResult(success=False, error="Transfer reason must be specified")

        record = {
            "target": target,
            "reason": reason,
            "urgency": urgency,
            "status": "transfer_initiated",
        }
        self.transfer_events.append(record)

        return ToolResult(
            success=True,
            data={
                "transfer_initiated": True,
                "target": target,
                "reason": reason,
                "urgency": urgency,
                "message": f"Call transfer initiated to {target} (Reason: {reason}).",
            },
        )


class EndCallInput(BaseModel):
    """Input parameters for gracefully ending a call."""

    reason: str = Field(
        default="normal_completion",
        description="Reason for ending the call ('normal_completion', 'scam_blocked', 'caller_declined').",
    )
    polite_closing_note: str | None = Field(
        default=None, description="Final spoken closing statement to the caller."
    )


class EndCallTool(BaseTool):
    """Tool to signal graceful completion or termination of the call."""

    name = "end_call"
    description = (
        "Conclude and hang up the current phone call after saying goodbye or blocking spam."
    )
    permission_level = PermissionLevel.LOW_RISK_WRITE
    args_schema = EndCallInput

    def __init__(self) -> None:
        self.termination_events: list[dict[str, Any]] = []

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Signal call termination."""
        reason = kwargs.get("reason", "normal_completion")
        closing_note = kwargs.get("polite_closing_note") or "Thank you for calling. Goodbye!"

        record = {
            "reason": reason,
            "closing_note": closing_note,
            "status": "call_ended",
        }
        self.termination_events.append(record)

        return ToolResult(
            success=True,
            data={
                "call_ended": True,
                "reason": reason,
                "closing_note": closing_note,
                "message": "Call successfully ended.",
            },
        )
