"""FRED service layer for business logic orchestration.

This module coordinates repository, cache, and database operations for
FRED data fetching and storage.
"""

from datetime import datetime
from typing import Any

import structlog
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.infrastructure.cache import Cache, get_cache
from ecox_platform.logging_config import truncate_error
from ecox_platform.sources.base.service import BaseService
from ecox_platform.sources.fred.repository import FredRepository

logger = structlog.get_logger(__name__)


class FredService(BaseService):
    """Service layer for FRED data operations.

    Coordinates fetching, caching, parsing, and storing FRED data.
    """

    def __init__(
        self,
        repository: FredRepository | None = None,
        cache: Cache | None = None,
        api_key: str | None = None,
        rate_limit: float = 10.0,
    ) -> None:
        """Initialize the FRED service.

        Args:
            repository: FRED repository (creates new one if not provided)
            cache: Cache instance (uses global cache if not provided)
            api_key: FRED API key (uses settings if not provided)
            rate_limit: Rate limit in requests per second
        """
        repo = repository or FredRepository(api_key=api_key, rate_limit=rate_limit)
        cache_instance = cache or get_cache()

        super().__init__(
            repository=repo,
            cache=cache_instance,
            source_name="fred",
        )

        logger.info("FRED service initialized")

    async def fetch_and_store(
        self,
        dataset_code: str,
        filters: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Fetch series from FRED and store in database.

        Uses content hashing and UPSERT to minimize sequence ID consumption:
        - Skips entirely if data hasn't changed (hash match)
        - Uses UPSERT to preserve IDs for existing rows
        - Only allocates new IDs for truly new data points

        Args:
            dataset_code: Series ID (e.g., "GDP")
            filters: Optional filters
            session: Optional database session

        Returns:
            Dictionary with fetch results including record count and status

        Raises:
            Exception: If fetch or store fails
        """
        started_at = datetime.now()

        try:
            # Fetch data (with caching)
            data = await self.fetch_and_cache(dataset_code, filters)

            observations = data.get("observations", [])

            logger.info(
                "Fetched FRED observations",
                dataset_code=dataset_code,
                observation_count=len(observations),
            )

            # Return early if no session (just fetch, no store)
            if not session:
                return {
                    "dataset_code": dataset_code,
                    "source": "fred",
                    "records_fetched": len(observations),
                    "status": "success",
                }

            # Get series metadata for details
            metadata = await self.repository.get_dataset_metadata(dataset_code)

            # Store/update dataset record with source's last_update from API
            dataset = await self.store_dataset(
                session=session,
                dataset_code=dataset_code,
                dataset_name=metadata.get("title", dataset_code),
                description=metadata.get("notes"),
                source_last_update=metadata.get("last_updated"),
                source_url=metadata.get("metadata_url"),
            )

            # Transform observations to common value format
            value_dicts = self._transform_observations(
                observations, filters, metadata, dataset_code
            )

            # Use template method for change detection and storage
            result = await self.store_with_change_detection(
                session=session,
                dataset=dataset,
                value_dicts=value_dicts,
                filters=filters,
                started_at=started_at,
            )

            # Override records_fetched with original observation count
            # (before filtering missing values)
            result["records_fetched"] = len(observations)
            return result

        except Exception as e:
            logger.error(
                "Failed to fetch and store FRED series",
                series_id=dataset_code,
                error=truncate_error(e),
            )

            # Log failed fetch if session provided
            if session:
                await self.log_fetch(
                    session=session,
                    dataset_code=dataset_code,
                    status="error",
                    error_message=truncate_error(e),
                    filters=filters,
                    started_at=started_at,
                )

            raise

    def _transform_observations(
        self,
        observations: list[dict[str, Any]],
        filters: dict[str, Any] | None,
        metadata: dict[str, Any],
        dataset_code: str,
    ) -> list[dict[str, Any]]:
        """Transform FRED observations to common value format.

        Args:
            observations: Raw FRED observation data
            filters: Optional filters (used to extract geo)
            metadata: Series metadata (used to extract unit)
            dataset_code: The series ID

        Returns:
            List of value dictionaries in common format
        """
        geo = filters.get("geo", "US") if filters else "US"
        unit = metadata.get("units_short", metadata.get("units"))

        value_dicts = []
        for obs in observations:
            val_str = obs.get("value")
            if val_str == ".":  # FRED uses "." for missing values
                continue

            try:
                val = float(val_str)  # type: ignore[arg-type]
            except (ValueError, TypeError):
                continue

            value_dicts.append(
                {
                    "geo": geo,
                    "time_period": obs.get("date"),
                    "indicator": dataset_code,
                    "value": val,
                    "unit": unit,
                    "flags": None,
                }
            )

        return value_dicts

    async def list_available_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available FRED datasets.

        Args:
            category: Optional category filter

        Returns:
            List of dataset metadata
        """
        return await self.repository.list_datasets(category)

    async def search_datasets(self, query: str) -> list[dict[str, Any]]:
        """Search for datasets by keyword.

        Args:
            query: Search query

        Returns:
            List of matching datasets
        """
        return await self.repository.search_datasets(query)

    async def get_gdp_data(self) -> dict[str, Any]:
        """Get US GDP data (Quarterly)."""
        return await self.fetch_and_cache("GDP")

    async def get_cpi_data(self) -> dict[str, Any]:
        """Get US CPI data (Monthly)."""
        return await self.fetch_and_cache("CPIAUCSL")

    async def get_unemployment_data(self) -> dict[str, Any]:
        """Get US Unemployment Rate (Monthly)."""
        return await self.fetch_and_cache("UNRATE")
