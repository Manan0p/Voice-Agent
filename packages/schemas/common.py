from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Common query parameters for paginated endpoints."""

    limit: int = Field(default=20, ge=1, le=100, description="Number of items to return")
    offset: int = Field(default=0, ge=0, description="Offset index for pagination")


class PaginatedResponse[T](BaseModel):
    """Standard generic wrapper for paginated collections."""

    total: int = Field(description="Total count of items matching criteria")
    limit: int = Field(description="Applied page limit")
    offset: int = Field(description="Applied page offset")
    items: list[T] = Field(description="List of records for the current page")


class StandardErrorResponse(BaseModel):
    """Standardized error output payload."""

    error: str = Field(description="Error message summary")
    detail: str | None = Field(
        default=None, description="Detailed technical or validation error message"
    )
