"""Pydantic schemas for Telegram Bot notifications, call triage alerts, and callback queries."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TelegramCallbackAction(StrEnum):
    """Actions triggered from Telegram inline button clicks."""

    TAKE_CALL = "take_call"
    KEEP_AI = "keep_ai"
    END_CALL = "end_call"
    RESUME_AI = "resume_ai"


class TelegramAlertPayload(BaseModel):
    """Payload for an incoming call triage alert card sent to Telegram."""

    call_id: str = Field(..., description="Unique call identifier / channel ID")
    caller_phone: str = Field(..., description="Caller phone number in E.164 format")
    caller_name: str = Field(default="Unknown Caller", description="Resolved caller name")
    intent: str = Field(default="general_inquiry", description="Classified intent")
    urgency_score: int = Field(default=1, ge=1, le=5, description="Urgency rating from 1 to 5")
    risk_level: str = Field(
        default="low", description="Risk assessment level (low/medium/high/critical)"
    )
    language: str = Field(default="English", description="Detected caller language")
    summary: str | None = Field(default=None, description="Real-time call summary snippet")
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context or caller tags"
    )


class TelegramNotificationResult(BaseModel):
    """Result of sending or updating a Telegram notification card."""

    success: bool
    chat_id: str | int
    message_id: int | None = None
    action: str = "send"
    error: str | None = None
