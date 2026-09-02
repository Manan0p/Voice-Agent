import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReminderCreate(BaseModel):
    """Payload to schedule a new callback/task reminder."""

    title: str = Field(description="Headline of the reminder")
    description: str | None = Field(default=None, description="Detailed instructions or context")
    due_at: datetime | None = Field(default=None, description="Scheduled due timestamp")
    caller_id: uuid.UUID | None = Field(default=None, description="Optional associated caller ID")


class ReminderResponse(BaseModel):
    """Output schema for a reminder."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    caller_id: uuid.UUID | None
    title: str
    description: str | None
    due_at: datetime | None
    is_completed: bool
    created_at: datetime
