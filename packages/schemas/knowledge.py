import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocCreate(BaseModel):
    """Payload to ingest a new knowledge document."""

    title: str = Field(description="Document title")
    category: str = Field(
        default="general", description="Category: calendar, preferences, project, personal, faq"
    )
    content: str = Field(description="Full text content of the document")
    source_file: str | None = Field(default=None, description="Optional source filename or URL")


class KnowledgeChunkResponse(BaseModel):
    """Schema for an individual indexed document chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doc_id: uuid.UUID
    chunk_index: int
    chunk_text: str
    metadata_json: dict[str, Any] | None


class KnowledgeDocResponse(BaseModel):
    """Output schema for a knowledge document."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    category: str
    content: str
    source_file: str | None
    created_at: datetime


class KnowledgeSearchRequest(BaseModel):
    """Payload to query knowledge via semantic or keyword search."""

    query: str = Field(description="Search text query")
    category: str | None = Field(default=None, description="Optional category filter")
    top_k: int = Field(default=5, ge=1, le=20, description="Max number of results")


class KnowledgeSearchResult(BaseModel):
    """Individual match result from knowledge search."""

    chunk_id: uuid.UUID
    doc_id: uuid.UUID
    doc_title: str
    category: str
    chunk_text: str
    similarity_score: float | None = None
