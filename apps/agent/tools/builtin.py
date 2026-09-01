from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from apps.agent.tools.base import BaseTool, PermissionLevel, ToolResult


class GetCurrentTimeInput(BaseModel):
    """Input for get_current_time tool."""

    timezone_offset: str = Field(
        default="UTC+5:30", description="Timezone offset (default Indian Standard Time)"
    )


class GetCurrentTimeTool(BaseTool):
    """Tool to retrieve the current date and time."""

    name = "get_current_time"
    description = "Get the current time, date, and day of the week to answer caller scheduling or timing questions."
    permission_level = PermissionLevel.READ_ONLY
    args_schema = GetCurrentTimeInput

    async def execute(self, **kwargs: Any) -> ToolResult:
        now = datetime.now(UTC)
        return ToolResult(
            success=True,
            data={
                "utc_iso": now.isoformat(),
                "formatted": now.strftime("%A, %B %d, %Y %I:%M %p UTC"),
                "status": "success",
            },
        )


class SaveCallerMessageInput(BaseModel):
    """Input schema for recording a message from the caller."""

    caller_name: str = Field(description="Name of the person who is calling or leaving the message")
    message: str | None = Field(
        default=None, description="Detailed text of the message, inquiry, or notes from the caller"
    )
    message_content: str | None = Field(
        default=None, description="Alternative field for message content"
    )
    phone_number: str | None = Field(
        default=None, description="Phone number or contact info if provided"
    )
    urgency: str = Field(
        default="normal", description="Perceived urgency: low, normal, high, critical"
    )
    category: str | None = Field(
        default=None, description="Optional message category (e.g. 'work', 'recruiter', 'personal')"
    )


class SaveCallerMessageTool(BaseTool):
    """Tool to save a caller's message to the user."""

    name = "save_caller_message"
    description = (
        "Save and record a message, note, or inquiry left by a caller for the user to review later."
    )
    permission_level = PermissionLevel.LOW_RISK_WRITE
    args_schema = SaveCallerMessageInput

    def __init__(self, name: str = "save_caller_message") -> None:
        self.name = name
        self.saved_messages: list[dict[str, Any]] = []

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            validated = SaveCallerMessageInput(**kwargs)
            content = validated.message or validated.message_content
            if not content:
                return ToolResult(
                    success=False,
                    error="Message content is required to save a caller message",
                )

            record = {
                "caller_name": validated.caller_name,
                "phone_number": validated.phone_number,
                "message_content": content,
                "urgency": validated.urgency,
                "category": validated.category or "general",
                "timestamp": datetime.now(UTC).isoformat(),
            }
            self.saved_messages.append(record)
            return ToolResult(
                success=True,
                data={
                    "status": "saved",
                    "caller_name": validated.caller_name,
                    "message_id": f"msg_{len(self.saved_messages)}",
                    "content": content,
                    "urgency": validated.urgency,
                },
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to validate or save message: {str(e)}",
            )
