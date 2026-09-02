import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    """Payload to record a new caller voicemail/message."""

    caller_name: str = Field(description="Name of the person leaving the message")
    message: str = Field(description="Content of the message/notes")
    phone_number: str | None = Field(default=None, description="Callback phone number")
    urgency: str = Field(
        default="normal", description="Urgency priority: low, normal, high, critical"
    )
    category: str = Field(
        default="general", description="Message category (e.g., recruiter, work, delivery, family)"
    )
    call_id: uuid.UUID | None = Field(
        default=None, description="Optional associated call session ID"
    )


class MessageUpdate(BaseModel):
    """Payload to update message status."""

    is_read: bool | None = Field(default=None, description="Mark message as read or unread")
    urgency: str | None = Field(default=None, description="Update urgency level")
    category: str | None = Field(default=None, description="Update category")


class MessageResponse(BaseModel):
    """Output schema for a voicemail/message record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    caller_id: uuid.UUID | None
    call_id: uuid.UUID | None
    caller_name: str
    phone_number: str | None
    message_content: str
    urgency: str
    category: str
    is_read: bool
    created_at: datetime
