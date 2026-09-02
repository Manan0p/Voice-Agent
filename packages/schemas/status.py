from datetime import datetime

from pydantic import BaseModel, Field


class ServiceComponentStatus(BaseModel):
    """Status of an individual subsystem."""

    name: str
    status: str = Field(description="operational, degraded, disabled, error")
    details: str | None = None


class SystemStatusResponse(BaseModel):
    """Aggregate system status overview."""

    app_name: str
    version: str
    environment: str
    timestamp: datetime
    llm_provider: str
    stt_model: str
    tts_engine: str
    database_connected: bool
    total_callers: int
    total_calls: int
    unread_messages: int
    pending_reminders: int
    components: list[ServiceComponentStatus]
