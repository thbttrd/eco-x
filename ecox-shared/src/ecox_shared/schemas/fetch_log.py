"""Pydantic schemas for fetch log API responses.

These schemas define the API contract for fetch log endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class FetchLogResponse(BaseModel):
    """API response for a single fetch log entry."""

    id: int
    dataset_code: str
    source: str
    status: str = Field(description="Status: 'success', 'error', 'partial'")
    records_fetched: int | None = None
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None


class FetchLogListResponse(BaseModel):
    """Paginated list of fetch logs."""

    items: list[FetchLogResponse]
    total: int = Field(description="Total number of logs matching the query")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
