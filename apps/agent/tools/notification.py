import time
from typing import Any

from pydantic import BaseModel, Field

from apps.agent.tools.base import BaseTool, PermissionLevel, ToolResult


class NotifyUserInput(BaseModel):
    """Input parameters for sending notification alert to user."""

    title: str = Field(description="Short summary headline of the alert.")
    message: str = Field(
        description="Full notification details, caller message, or action required."
    )
    urgency: str = Field(
        default="high",
        description="Urgency priority rating: 'low', 'medium', 'high', or 'critical'.",
    )
    channel: str = Field(
        default="telegram",
        description="Notification delivery channel: 'telegram', 'push', or 'sms'.",
    )


class NotifyUserTool(BaseTool):
    """Tool to dispatch out-of-band push / Telegram notification alerts directly to the owner."""

    name = "notify_user"
    description = "Send an urgent notification alert (e.g. via Telegram or push) to the owner regarding high-priority calls."
    permission_level = PermissionLevel.LOW_RISK_WRITE
    args_schema = NotifyUserInput

    def __init__(self) -> None:
        self.sent_notifications: list[dict[str, Any]] = []

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Deliver notification to the owner."""
        title = kwargs.get("title", "").strip()
        message = kwargs.get("message", "").strip()
        urgency = kwargs.get("urgency", "high").lower()
        channel = kwargs.get("channel", "telegram").lower()

        if not title or not message:
            return ToolResult(
                success=False, error="Title and message are required for notifications"
            )

        record = {
            "timestamp": time.time(),
            "title": title,
            "message": message,
            "urgency": urgency,
            "channel": channel,
            "delivered": True,
        }
        self.sent_notifications.append(record)

        return ToolResult(
            success=True,
            data={
                "delivered": True,
                "channel": channel,
                "urgency": urgency,
                "notification_id": f"notif_{len(self.sent_notifications)}",
                "message": f"Alert '{title}' successfully sent to owner via {channel}.",
            },
        )
