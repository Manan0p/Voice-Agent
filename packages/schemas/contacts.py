import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ContactCreate(BaseModel):
    """Payload to create a new contact profile."""

    phone_number: str = Field(description="Phone number in standard E.164 or national format")
    name: str | None = Field(default=None, description="Contact name")
    relationship: str = Field(
        default="unknown",
        description="Relationship: family, friend, colleague, recruiter, delivery, business, spam, unknown",
    )
    trust_score: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Trust confidence level (0.0 to 1.0)"
    )
    organization: str | None = Field(default=None, description="Organization or company name")
    language_preference: str = Field(
        default="hinglish", description="Language preference (hinglish, english, hindi)"
    )
    notes: str | None = Field(default=None, description="Personal or context notes")
    is_blocked: bool = Field(default=False, description="Flag indicating if number is blocked")


class ContactUpdate(BaseModel):
    """Payload to update an existing contact."""

    name: str | None = Field(default=None, description="Updated contact name")
    relationship: str | None = Field(default=None, description="Updated relationship")
    trust_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Updated trust score"
    )
    organization: str | None = Field(default=None, description="Updated organization")
    language_preference: str | None = Field(default=None, description="Updated language preference")
    notes: str | None = Field(default=None, description="Updated notes")
    is_blocked: bool | None = Field(default=None, description="Updated block status")


class ContactResponse(BaseModel):
    """Output schema for a contact profile."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone_number: str
    name: str | None
    relationship: str
    trust_score: float
    organization: str | None
    language_preference: str
    notes: str | None
    is_blocked: bool
    created_at: datetime
    updated_at: datetime
