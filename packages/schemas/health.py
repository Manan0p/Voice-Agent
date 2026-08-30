from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for system health endpoint response."""

    status: str = Field(default="ok", description="Overall system health status")
    version: str = Field(default="0.1.0", description="Application version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of the check",
    )
    environment: str = Field(default="development", description="Current environment mode")
