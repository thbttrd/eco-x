"""FRED data source implementation."""

from ecox_platform.sources.fred.models import (
    FredCategory,
    FredCategoryResponse,
    FredObservation,
    FredObservationsResponse,
    FredSeries,
    FredSeriesResponse,
)
from ecox_platform.sources.fred.repository import FredRepository
from ecox_platform.sources.fred.service import FredService

__all__ = [
    "FredCategory",
    "FredCategoryResponse",
    "FredObservation",
    "FredObservationsResponse",
    "FredRepository",
    "FredSeries",
    "FredSeriesResponse",
    "FredService",
]
