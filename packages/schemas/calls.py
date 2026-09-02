import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CallCreate(BaseModel):
    """Payload to initiate/record a call session."""

    phone_number: str = Field(description="Caller phone number")
    status: str = Field(
        default="active", description="Call state: active, completed, missed, failed"
    )
    intent: str | None = Field(default=None, description="Classified caller intent")
    urgency: str | None = Field(default=None, description="Assessed urgency level")


class CallUpdate(BaseModel):
    """Payload to update an ongoing or completed call."""

    status: str | None = Field(default=None, description="Updated call status")
    duration_sec: float | None = Field(default=None, description="Final call duration in seconds")
    intent: str | None = Field(default=None, description="Updated intent")
    urgency: str | None = Field(default=None, description="Updated urgency")
    summary: str | None = Field(default=None, description="Call summary notes")
    transcript: list[dict[str, Any]] | None = Field(
        default=None, description="Call transcript turns"
    )


class CallResponse(BaseModel):
    """Overview schema for a call session."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    caller_id: uuid.UUID | None
    phone_number: str
    status: str
    start_time: datetime
    end_time: datetime | None
    duration_sec: float
    intent: str | None
    urgency: str | None
    summary: str | None


class CallDetailResponse(CallResponse):
    """Detailed schema including transcripts and metadata."""

    transcript: list[dict[str, Any]] | None
    recording_url: str | None
    created_at: datetime
    updated_at: datetime
