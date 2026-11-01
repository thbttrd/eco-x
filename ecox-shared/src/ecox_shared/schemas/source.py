"""Pydantic schemas for source API responses.

These schemas define the API contract for data source endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class SourceResponse(BaseModel):
    """API response for a single data source."""

    code: str = Field(description="Source code (e.g., 'eurostat', 'fred')")
    name: str = Field(description="Human-readable source name")
    description: str | None = None
    dataset_count: int = Field(description="Number of datasets downloaded from this source")
    total_available: int | None = Field(
        default=None, description="Total datasets available in this source"
    )
    last_activity: datetime | None = Field(
        default=None, description="Last fetch activity timestamp"
    )


class SourceStatusResponse(BaseModel):
    """Detailed status response for a data source."""

    code: str
    name: str
    description: str | None = None
    dataset_count: int
    total_available: int | None = None
    last_activity: datetime | None = None
    worker_status: str = Field(description="Worker status: 'running', 'idle', 'stopped', 'error'")
    fetch_queue_size: int = Field(default=0, description="Number of datasets waiting to be fetched")
    rate_limit: float = Field(description="Current rate limit (requests/second)")
    recent_errors: int = Field(default=0, description="Number of errors in the last hour")
