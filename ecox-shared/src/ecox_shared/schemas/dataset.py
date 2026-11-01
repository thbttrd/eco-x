"""Pydantic schemas for dataset API responses.

These schemas define the API contract for dataset-related endpoints.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetResponse(BaseModel):
    """API response schema for a single dataset."""

    id: int
    code: str
    name: str
    source: str
    description: str | None = None
    last_fetched: datetime | None = None
    record_count: int | None = Field(
        default=None, description="Number of data values in this dataset"
    )


class DatasetDetailResponse(BaseModel):
    """Detailed API response for a single dataset with metadata."""

    id: int
    code: str
    name: str
    source: str
    description: str | None = None
    last_fetched: datetime | None = None
    record_count: int | None = None
    extra_metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata as parsed JSON"
    )
    dimensions: list[str] | None = Field(
        default=None, description="Available dimensions for filtering"
    )
    source_url: str | None = Field(
        default=None, description="URL to the original dataset page on the source website"
    )


class DatasetListResponse(BaseModel):
    """Paginated list of datasets."""

    items: list[DatasetResponse]
    total: int = Field(description="Total number of datasets matching the query")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")


class DatasetSyncResponse(BaseModel):
    """Response for incremental dataset sync.

    Used by clients to fetch only new datasets since their last sync.
    """

    items: list[DatasetResponse] = Field(description="List of datasets")
    max_id: int | None = Field(
        default=None,
        description="Highest dataset ID in response, use as since_id for next sync",
    )


class DataValueResponse(BaseModel):
    """API response for a single data value."""

    geo: str = Field(description="Geographic area code")
    time_period: str = Field(description="Time period")
    indicator: str = Field(description="Indicator/measurement type")
    value: float = Field(description="Numeric value")
    unit: str | None = Field(default=None, description="Unit of measurement")
    flags: str | None = Field(default=None, description="Data quality flags")


class DataValueListResponse(BaseModel):
    """Paginated list of data values."""

    items: list[DataValueResponse]
    total: int = Field(description="Total number of values matching the query")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    dataset_code: str = Field(description="Dataset code these values belong to")
    source: str = Field(description="Data source")
