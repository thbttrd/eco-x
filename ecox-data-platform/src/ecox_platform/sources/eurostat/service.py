"""Eurostat service layer for business logic orchestration.

This module coordinates repository, cache, and database operations for
Eurostat data fetching and storage.
"""

import asyncio
from datetime import datetime
from typing import Any

import structlog
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.infrastructure.cache import Cache, get_cache
from ecox_platform.logging_config import truncate_error
from ecox_platform.sources.base.service import BaseService
from ecox_platform.sources.eurostat.models import parse_jsonstat
from ecox_platform.sources.eurostat.repository import EurostatRepository

logger = structlog.get_logger(__name__)


class EurostatService(BaseService):
    """Service layer for Eurostat data operations.

    Coordinates fetching, caching, parsing, and storing Eurostat data.
    """

    def __init__(
        self,
        repository: EurostatRepository | None = None,
        cache: Cache | None = None,
        rate_limit: float = 2.0,
    ) -> None:
        """Initialize the Eurostat service.

        Args:
            repository: Eurostat repository (creates new one if not provided)
            cache: Cache instance (uses global cache if not provided)
            rate_limit: Rate limit in requests per second
        """
        repo = repository or EurostatRepository(rate_limit=rate_limit)
        cache_instance = cache or get_cache()

        super().__init__(
            repository=repo,
            cache=cache_instance,
            source_name="eurostat",
        )

        logger.info("Eurostat service initialized")

    async def fetch_and_store(
        self,
        dataset_code: str,
        filters: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Fetch dataset from Eurostat and store in database.

        Uses content hashing and UPSERT to minimize sequence ID consumption:
        - Skips entirely if data hasn't changed (hash match)
        - Uses UPSERT to preserve IDs for existing rows
        - Only allocates new IDs for truly new data points

        Args:
            dataset_code: Dataset identifier
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

            # Parse JSON-stat data (offload to thread pool to avoid blocking event loop)
            parsed_values = await asyncio.to_thread(parse_jsonstat, data)

            logger.info(
                "Parsed dataset values",
                dataset_code=dataset_code,
                value_count=len(parsed_values),
            )

            # Transform parsed values to common dict format
            value_dicts = self._transform_parsed_values(parsed_values)

            # Return early if no session (just fetch, no store)
            if not session:
                return {
                    "dataset_code": dataset_code,
                    "source": "eurostat",
                    "records_fetched": len(parsed_values),
                    "status": "success",
                }

            # Get dataset metadata
            metadata = await self.repository.get_dataset_metadata(dataset_code)

            # Store/update dataset record with source's last_update from TOC
            dataset = await self.store_dataset(
                session=session,
                dataset_code=dataset_code,
                dataset_name=metadata["name"],
                description=metadata.get("description"),
                source_last_update=metadata.get("last_update"),
                source_url=metadata.get("metadata_url"),
            )

            # Use template method for change detection and storage
            result = await self.store_with_change_detection(
                session=session,
                dataset=dataset,
                value_dicts=value_dicts,
                filters=filters,
                started_at=started_at,
            )

            # Override records_fetched with original parsed count
            result["records_fetched"] = len(parsed_values)
            return result

        except Exception as e:
            logger.error(
                "Failed to fetch and store dataset",
                dataset_code=dataset_code,
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

    def _transform_parsed_values(self, parsed_values: list[Any]) -> list[dict[str, Any]]:
        """Transform parsed JSON-stat values to common dict format.

        Args:
            parsed_values: List of parsed EurostatValue objects

        Returns:
            List of value dictionaries in common format
        """
        return [
            {
                "geo": v.geo,
                "time_period": v.time_period,
                "indicator": v.indicator,
                "value": v.value,
                "unit": v.unit,
                "flags": v.flags,
            }
            for v in parsed_values
        ]

    async def list_available_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available Eurostat datasets.

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
