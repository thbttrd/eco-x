"""NBS China service layer for business logic orchestration.

This module coordinates repository, cache, and database operations for
NBS China data fetching and storage.
"""

from datetime import datetime
from typing import Any

import structlog
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.config import settings
from ecox_platform.infrastructure.cache import Cache, get_cache
from ecox_platform.logging_config import truncate_error
from ecox_platform.sources.base.service import BaseService
from ecox_platform.sources.nbs.models import NbsQueryDataResponse
from ecox_platform.sources.nbs.repository import NbsRepository

logger = structlog.get_logger(__name__)


class NbsService(BaseService):
    """Service layer for NBS China data operations.

    Coordinates fetching, caching, parsing, and storing NBS data.
    The NBS API provides hierarchical indicator data with metadata
    embedded in the response.
    """

    def __init__(
        self,
        repository: NbsRepository | None = None,
        cache: Cache | None = None,
        rate_limit: float | None = None,
    ) -> None:
        """Initialize the NBS service.

        Args:
            repository: NBS repository (creates new one if not provided)
            cache: Cache instance (uses global cache if not provided)
            rate_limit: Rate limit in requests per second
        """
        effective_rate_limit = rate_limit or settings.nbs_rate_limit
        repo = repository or NbsRepository(rate_limit=effective_rate_limit)
        cache_instance = cache or get_cache()

        super().__init__(
            repository=repo,
            cache=cache_instance,
            source_name="nbs",
        )

        logger.info("NBS service initialized")

    async def fetch_and_store(
        self,
        dataset_code: str,
        filters: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Fetch dataset from NBS China and store in database.

        Uses content hashing and UPSERT to minimize sequence ID consumption:
        - Skips entirely if data hasn't changed (hash match)
        - Uses UPSERT to preserve IDs for existing rows
        - Only allocates new IDs for truly new data points

        Args:
            dataset_code: Indicator code (e.g., "A0201" for GDP group)
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

            returndata = data.get("returndata", {})
            datanodes = returndata.get("datanodes", [])
            wdnodes = returndata.get("wdnodes", [])

            logger.info(
                "Fetched NBS data",
                dataset_code=dataset_code,
                datanode_count=len(datanodes),
            )

            # Return early if no session (just fetch, no store)
            if not session:
                return {
                    "dataset_code": dataset_code,
                    "source": "nbs",
                    "records_fetched": len(datanodes),
                    "status": "success",
                }

            # Extract metadata using Pydantic model (removes duplicate logic)
            try:
                response = NbsQueryDataResponse(**data)
                model_meta = response.get_indicator_metadata()
                # Convert to dict format for compatibility with _transform_datanodes
                indicator_meta = {
                    code: {"name": m.name, "cname": m.cname, "unit": m.unit, "exp": m.exp}
                    for code, m in model_meta.items()
                }
            except Exception:
                # Fallback to raw extraction if model parsing fails
                indicator_meta = self._extract_indicator_metadata(wdnodes)

            # Get dataset name from metadata or use code
            dataset_name = dataset_code
            dataset_description = None
            if dataset_code in indicator_meta:
                meta = indicator_meta[dataset_code]
                dataset_name = meta.get("name", dataset_code)
                dataset_description = meta.get("exp") or None

            # Store/update dataset record
            # NBS doesn't provide last_update or URLs in TOC
            dataset = await self.store_dataset(
                session=session,
                dataset_code=dataset_code,
                dataset_name=dataset_name,
                description=dataset_description,
                source_last_update=None,
                source_url=None,  # URL generated dynamically by API
            )

            # Transform NBS data to common value format
            value_dicts = self._transform_datanodes(
                datanodes=datanodes,
                indicator_meta=indicator_meta,
            )

            # Use template method for change detection and storage
            result = await self.store_with_change_detection(
                session=session,
                dataset=dataset,
                value_dicts=value_dicts,
                filters=filters,
                started_at=started_at,
            )

            # Override records_fetched with original datanode count
            result["records_fetched"] = len(datanodes)
            return result

        except Exception as e:
            logger.error(
                "Failed to fetch and store NBS dataset",
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

    def _extract_indicator_metadata(
        self, wdnodes: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Extract indicator metadata from wdnodes.

        Args:
            wdnodes: List of dimension node dictionaries

        Returns:
            Dictionary mapping indicator codes to their metadata
        """
        result: dict[str, dict[str, Any]] = {}

        for wdnode in wdnodes:
            if wdnode.get("wdcode") == "zb":  # Indicator dimension
                for node in wdnode.get("nodes", []):
                    code = node.get("code", "")
                    if code:
                        result[code] = {
                            "name": node.get("name", code),
                            "cname": node.get("cname", ""),
                            "unit": node.get("unit", ""),
                            "exp": node.get("exp", ""),
                        }

        return result

    def _transform_datanodes(
        self,
        datanodes: list[dict[str, Any]],
        indicator_meta: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform NBS datanodes to common value format.

        The NBS format has:
        - datanodes[].data.data: the numeric value
        - datanodes[].wds[]: array of dimension values
          - wdcode="zb", valuecode="A020102" -> indicator
          - wdcode="sj", valuecode="2024" -> time_period

        Args:
            datanodes: Raw NBS datanode list
            indicator_meta: Indicator metadata dictionary

        Returns:
            List of value dictionaries in common format
        """
        value_dicts: list[dict[str, Any]] = []

        for node in datanodes:
            # Extract data value
            data_obj = node.get("data", {})
            if not data_obj.get("hasdata", False):
                continue

            value = data_obj.get("data")
            if value is None:
                continue

            # Extract dimensions from wds array
            indicator_code = ""
            time_period = ""

            for dim in node.get("wds", []):
                wdcode = dim.get("wdcode", "")
                valuecode = dim.get("valuecode", "")

                if wdcode == "zb":  # Indicator
                    indicator_code = valuecode
                elif wdcode == "sj":  # Time period
                    time_period = valuecode

            if not indicator_code or not time_period:
                continue

            # Get unit from indicator metadata
            unit = None
            if indicator_code in indicator_meta:
                unit = indicator_meta[indicator_code].get("unit") or None

            value_dicts.append(
                {
                    "geo": "CN",  # China national data
                    "time_period": time_period,
                    "indicator": indicator_code,
                    "value": float(value),
                    "unit": unit,
                    "flags": None,
                }
            )

        return value_dicts

    async def list_available_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available NBS datasets.

        Args:
            category: Optional category filter (parent node ID)

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
        """Get China GDP data (Annual)."""
        return await self.fetch_and_cache("A0201")

    async def get_cpi_data(self) -> dict[str, Any]:
        """Get China CPI data (Monthly - requires hgyd database)."""
        return await self.fetch_and_cache("A01")

    async def get_population_data(self) -> dict[str, Any]:
        """Get China Population data (Annual)."""
        return await self.fetch_and_cache("A0301")
