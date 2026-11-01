"""FRED repository implementation.

This module implements the repository pattern for fetching data from
the Federal Reserve Economic Data (FRED) API.
"""

import json
from datetime import datetime, timedelta
from typing import Any

import structlog
from ecox_shared.models import SourceMetadata
from ecox_shared.utils import ResilientHttpClient
from pydantic import ValidationError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.config import settings
from ecox_platform.infrastructure.cache import get_cache
from ecox_platform.sources.base.repository import BaseRepository
from ecox_platform.sources.fred.models import (
    FredObservationsResponse,
    FredSeriesResponse,
)

logger = structlog.get_logger(__name__)

# FRED API base URL
FRED_BASE_URL = "https://api.stlouisfed.org/fred"

# Cache key constants
TOC_CACHE_KEY = "__toc__"
TOC_TTL_SECONDS = 6 * 3600  # 6 hours


class FredRepository(BaseRepository):
    """Repository for fetching data from FRED API.

    Implements the BaseRepository interface for FRED-specific operations.
    """

    def __init__(
        self,
        http_client: ResilientHttpClient | None = None,
        api_key: str | None = None,
        rate_limit: float = 10.0,
    ) -> None:
        """Initialize the FRED repository.

        Args:
            http_client: Optional HTTP client (creates new one if not provided)
            api_key: FRED API key (uses settings if not provided)
            rate_limit: Rate limit in requests per second
        """
        self.http_client = http_client or ResilientHttpClient(
            base_url=FRED_BASE_URL,
            rate_limit=rate_limit,
        )
        self.api_key = api_key or settings.fred_api_key

        if not self.api_key:
            logger.warning("FRED API key is not set. API calls will fail.")

        logger.info("FRED repository initialized")

    async def get_dataset(
        self, dataset_code: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch a specific series observations from FRED API.

        Args:
            dataset_code: Series ID (e.g., "GDP", "UNRATE")
            filters: Optional filters (observation_start, observation_end, units, etc.)

        Returns:
            Dictionary containing observations and metadata

        Raises:
            ValueError: If dataset_code is invalid or API key is missing
        """
        if not self.api_key:
            raise ValueError("FRED API key is not configured")

        params: dict[str, Any] = {
            "series_id": dataset_code,
            "api_key": self.api_key,
            "file_type": "json",
        }

        if filters:
            params.update(filters)

        logger.info(
            "Fetching series observations from FRED",
            series_id=dataset_code,
            filters=filters,
        )

        try:
            data = await self.http_client.get("series/observations", params=params)

            # Validate response structure
            FredObservationsResponse(**data)

            return data

        except ValidationError as e:
            logger.error("Invalid FRED API response", error=str(e))
            raise ValueError(f"Invalid FRED API response: {e}") from e
        except Exception as e:
            logger.error(
                "Failed to fetch FRED series",
                series_id=dataset_code,
                error=str(e),
            )
            raise

    async def _refresh_toc_background(self, session_factory: Any) -> None:
        """Background task to refresh the TOC cache.

        Args:
            session_factory: Factory to create database sessions
        """
        logger.info("Starting background FRED TOC refresh")
        try:
            async with session_factory() as session:
                await self.fetch_toc(session=session, force_refresh=True)
        except Exception as e:
            logger.error("Background FRED TOC refresh failed", error=str(e))

    async def fetch_toc(
        self, session: AsyncSession | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch and parse the FRED Table of Contents (TOC).

        Since FRED has too many datasets to list all, we simulate a TOC by
        fetching the most popular series tagged with 'usa'.

        Args:
            session: Optional DB session for caching
            force_refresh: If True, bypass caches and fetch from API

        Returns:
            List of dataset metadata dictionaries
        """
        cache = get_cache()

        # 1. Check memory cache first (fastest) - unless forced
        if not force_refresh:
            cached_toc = cache.get("fred", TOC_CACHE_KEY)
            if cached_toc is not None:
                logger.debug("Returning cached FRED TOC (memory)", count=len(cached_toc))
                return list(cached_toc)

        # 2. Check DB cache if session provided - unless forced
        if not force_refresh and session:
            try:
                statement = select(SourceMetadata).where(SourceMetadata.source == "fred")
                result = await session.exec(statement)
                metadata = result.one_or_none()

                if metadata and metadata.cached_toc:
                    try:
                        toc_data: list[dict[str, Any]] = json.loads(metadata.cached_toc)

                        # Check age
                        age = datetime.now() - metadata.last_updated
                        is_stale = age >= timedelta(hours=24)

                        if not is_stale:
                            logger.info(
                                "Returning cached FRED TOC (DB)",
                                count=len(toc_data),
                                age_hours=age.total_seconds() / 3600,
                            )
                            cache.set("fred", TOC_CACHE_KEY, toc_data, ttl_seconds=TOC_TTL_SECONDS)
                            return toc_data
                        else:
                            # Stale: Return old data
                            logger.info(
                                "Returning STALE FRED TOC (DB)",
                                count=len(toc_data),
                                age_hours=age.total_seconds() / 3600,
                            )
                            cache.set("fred", TOC_CACHE_KEY, toc_data, ttl_seconds=TOC_TTL_SECONDS)
                            return toc_data

                    except json.JSONDecodeError:
                        logger.warning("Failed to decode cached TOC from DB")
            except Exception as e:
                logger.warning("Failed to check DB cache for TOC", error=str(e))

        # 3. Fetch from API (slowest) - or forced
        if not self.api_key:
            logger.warning("FRED API key missing, cannot fetch TOC")
            return []

        try:
            logger.info("Fetching FRED Table of Contents (popular series)")

            # Fetch popular series tagged with 'usa'
            # We use tags/series endpoint
            params = {
                "tag_names": "usa;nation",
                "order_by": "popularity",
                "sort_order": "desc",
                "limit": 1000,
                "api_key": self.api_key,
                "file_type": "json",
            }

            data = await self.http_client.get("tags/series", params=params)
            series_list = data.get("seriess", [])

            datasets = []
            for s in series_list:
                datasets.append(
                    {
                        "code": s.get("id"),
                        "name": s.get("title"),
                        "description": s.get("notes") or s.get("title"),
                        "category": "fred_popular",
                        "last_update": s.get("last_updated"),
                        "data_start": s.get("observation_start"),
                        "data_end": s.get("observation_end"),
                        "frequency": s.get("frequency"),
                        "units": s.get("units"),
                        "popularity": s.get("popularity"),
                        "metadata_url": f"https://fred.stlouisfed.org/series/{s.get('id')}",
                    }
                )

            logger.info("Parsed FRED TOC", dataset_count=len(datasets))

            # Update memory cache
            cache.set("fred", TOC_CACHE_KEY, datasets, ttl_seconds=TOC_TTL_SECONDS)

            # Update DB cache if session provided
            if session:
                try:
                    # Re-fetch to ensure we have the latest state or create new
                    statement = select(SourceMetadata).where(SourceMetadata.source == "fred")
                    result = await session.exec(statement)
                    metadata = result.one_or_none()

                    if not metadata:
                        metadata = SourceMetadata(source="fred")
                        session.add(metadata)

                    metadata.total_datasets = len(datasets)
                    metadata.cached_toc = json.dumps(datasets)
                    metadata.last_updated = datetime.now()

                    await session.commit()
                    logger.info("Updated FRED TOC in DB cache")
                except Exception as e:
                    logger.error("Failed to update DB cache for TOC", error=str(e))

            return datasets

        except Exception as e:
            logger.error("Failed to fetch/parse FRED TOC", error=str(e))
            return []

    async def list_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available datasets (series) from FRED.

        If category is provided (as category_id), lists series in that category.
        Otherwise, returns a default list of popular series.

        Args:
            category: Optional category ID (as string)

        Returns:
            List of series metadata
        """
        if not self.api_key:
            logger.warning("FRED API key missing, returning empty list")
            return []

        if category:
            # List series in category
            params = {
                "category_id": category,
                "api_key": self.api_key,
                "file_type": "json",
            }
            endpoint = "category/series"
            try:
                data = await self.http_client.get(endpoint, params=params)
                series_list = data.get("seriess", [])

                # Enrich with metadata URL and map to common structure
                results = []
                for s in series_list:
                    results.append(
                        {
                            "code": s.get("id"),
                            "name": s.get("title"),
                            "description": s.get("notes") or s.get("title"),
                            "category": category,
                            "last_update": s.get("last_updated"),
                            "data_start": s.get("observation_start"),
                            "data_end": s.get("observation_end"),
                            "frequency": s.get("frequency"),
                            "units": s.get("units"),
                            "popularity": s.get("popularity"),
                            "metadata_url": f"https://fred.stlouisfed.org/series/{s.get('id')}",
                        }
                    )

                return results
            except Exception as e:
                logger.error("Failed to list FRED datasets by category", error=str(e))
                return []
        else:
            # Return cached TOC (popular series)
            return await self.fetch_toc()

    async def list_discoverable_datasets(
        self, session: AsyncSession | None = None
    ) -> list[dict[str, Any]]:
        """List all discoverable datasets from FRED.

        Args:
            session: Optional database session for caching

        Returns:
            List of all available datasets from TOC
        """
        return await self.fetch_toc(session=session)

    async def search_datasets(self, query: str) -> list[dict[str, Any]]:
        """Search for series by keyword.

        Args:
            query: Search query string

        Returns:
            List of matching series metadata
        """
        if not self.api_key:
            raise ValueError("FRED API key is not configured")

        params = {
            "search_text": query,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": 20,  # Limit results
        }

        logger.info("Searching FRED series", query=query)

        try:
            data = await self.http_client.get("series/search", params=params)
            return list(data.get("seriess", []))
        except Exception as e:
            logger.error("Failed to search FRED series", query=query, error=str(e))
            raise

    async def get_dataset_metadata(self, dataset_code: str) -> dict[str, Any]:
        """Get metadata for a specific series.

        Args:
            dataset_code: Series ID

        Returns:
            Series metadata
        """
        if not self.api_key:
            raise ValueError("FRED API key is not configured")

        params = {
            "series_id": dataset_code,
            "api_key": self.api_key,
            "file_type": "json",
        }

        try:
            data = await self.http_client.get("series", params=params)

            # Validate
            response = FredSeriesResponse(**data)

            if not response.seriess:
                raise ValueError(f"Series not found: {dataset_code}")

            series = response.seriess[0]

            result = series.model_dump()
            result["metadata_url"] = f"https://fred.stlouisfed.org/series/{dataset_code}"

            return result

        except Exception as e:
            logger.error(
                "Failed to get FRED series metadata",
                series_id=dataset_code,
                error=str(e),
            )
            raise

    async def validate_filters(self, dataset_code: str, filters: dict[str, Any]) -> bool:
        """Validate filters for FRED requests.

        Args:
            dataset_code: Series ID
            filters: Filters to validate

        Returns:
            True if valid
        """
        valid_params = {
            "realtime_start",
            "realtime_end",
            "limit",
            "offset",
            "sort_order",
            "observation_start",
            "observation_end",
            "units",
            "frequency",
            "aggregation_method",
            "output_type",
            "vintage_dates",
        }

        for key in filters:
            if key not in valid_params:
                logger.warning(f"Unknown filter parameter for FRED: {key}")
                # We don't return False here as it might be a valid param we missed,
                # just warn.

        return True

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.close()
