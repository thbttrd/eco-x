"""FRED API data models.

This module provides Pydantic models for parsing responses from the
Federal Reserve Economic Data (FRED) API.
"""

from pydantic import BaseModel


class FredObservation(BaseModel):
    """A single data observation from FRED."""

    date: str
    value: str
    realtime_start: str
    realtime_end: str


class FredObservationsResponse(BaseModel):
    """Response structure for FRED series observations."""

    realtime_start: str
    realtime_end: str
    observation_start: str
    observation_end: str
    units: str
    output_type: int
    file_type: str
    order_by: str
    sort_order: str
    count: int
    offset: int
    limit: int
    observations: list[FredObservation]


class FredSeries(BaseModel):
    """Metadata for a FRED series."""

    id: str
    realtime_start: str
    realtime_end: str
    title: str
    observation_start: str
    observation_end: str
    frequency: str
    frequency_short: str
    units: str
    units_short: str
    seasonal_adjustment: str
    seasonal_adjustment_short: str
    last_updated: str
    popularity: int
    notes: str | None = None


class FredSeriesResponse(BaseModel):
    """Response structure for FRED series metadata."""

    realtime_start: str
    realtime_end: str
    seriess: list[FredSeries]


class FredCategory(BaseModel):
    """FRED category metadata."""

    id: int
    name: str
    parent_id: int


class FredCategoryResponse(BaseModel):
    """Response structure for FRED category."""

    categories: list[FredCategory]
