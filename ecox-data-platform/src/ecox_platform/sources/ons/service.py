"""ONS service layer for business logic orchestration.

This module coordinates repository, cache, and database operations for
ONS data fetching and storage.
"""

from datetime import datetime
from typing import Any

import structlog
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.infrastructure.cache import Cache, get_cache
from ecox_platform.logging_config import truncate_error
from ecox_platform.sources.base.service import BaseService
from ecox_platform.sources.ons.repository import OnsRepository

logger = structlog.get_logger(__name__)


class OnsService(BaseService):
    """Service layer for ONS data operations.

    Coordinates fetching, caching, parsing, and storing ONS data.
    """

    def __init__(
        self,
        repository: OnsRepository | None = None,
        cache: Cache | None = None,
        rate_limit: float = 2.0,
    ) -> None:
        """Initialize the ONS service.

        Args:
            repository: ONS repository (creates new one if not provided)
            cache: Cache instance (uses global cache if not provided)
            rate_limit: Rate limit in requests per second
        """
        repo = repository or OnsRepository(rate_limit=rate_limit)
        cache_instance = cache or get_cache()

        super().__init__(
            repository=repo,
            cache=cache_instance,
            source_name="ons",
        )

        logger.info("ONS service initialized")

    async def fetch_and_store(
        self,
        dataset_code: str,
        filters: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Fetch dataset from ONS and store in database.

        Uses content hashing and UPSERT to minimize database operations:
        - Skips entirely if data hasn't changed (hash match)
        - Uses UPSERT to preserve IDs for existing rows
        - Only allocates new IDs for truly new data points

        Args:
            dataset_code: Dataset identifier (e.g., "trade", "regional-gdp-by-year")
            filters: Optional filters (dimension values)
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

            observations = data.get("observations") or []
            metadata = data.get("_metadata", {})

            logger.info(
                "Fetched ONS observations",
                dataset_code=dataset_code,
                observation_count=len(observations),
            )

            # Return early if no session (just fetch, no store)
            if not session:
                return {
                    "dataset_code": dataset_code,
                    "source": "ons",
                    "records_fetched": len(observations),
                    "status": "success",
                }

            # Get dataset metadata for name/description
            try:
                ds_metadata = await self.repository.get_dataset_metadata(dataset_code)
            except Exception:
                ds_metadata = {}

            # Store/update dataset record
            dataset = await self.store_dataset(
                session=session,
                dataset_code=dataset_code,
                dataset_name=ds_metadata.get("title", dataset_code),
                description=ds_metadata.get("description"),
                source_last_update=metadata.get("last_updated") or ds_metadata.get("last_updated"),
                source_url=ds_metadata.get("metadata_url"),
            )

            # Transform observations to common value format
            value_dicts = self._transform_observations(
                observations, filters, metadata, dataset_code, data
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
            result["records_fetched"] = len(observations)
            return result

        except Exception as e:
            logger.error(
                "Failed to fetch and store ONS dataset",
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

    # Census 2021 geography dimension names (in priority order)
    CENSUS_GEO_DIMENSIONS = ("ltla", "msoa", "lsoa", "oa", "region", "ctry", "rgn")

    def _transform_observations(
        self,
        observations: list[dict[str, Any]],
        filters: dict[str, Any] | None,
        metadata: dict[str, Any],
        dataset_code: str,
        raw_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Transform ONS observations to common value format.

        Handles both standard datasets and Census 2021 data:
        - Standard: geography dimension named "geography" or "Geography"
        - Census 2021: geography may be "ltla", "msoa", "lsoa", "oa", "region", etc.

        Args:
            observations: Raw ONS observation data
            filters: Optional filters (used to extract dimension values)
            metadata: Dataset metadata from _metadata key
            dataset_code: The dataset ID
            raw_data: Full API response (may contain dimension info)

        Returns:
            List of value dictionaries in common format
        """
        unit = metadata.get("unit_of_measure") or raw_data.get("unit_of_measure")
        is_census = metadata.get("census_2021", False)

        # Get fixed dimension values from raw_data.dimensions (non-time dimensions)
        # Standard datasets: dimensions is a dict {name: {option: {...}}}
        # Census 2021: dimensions is a list [{dimension_name: ..., options: [...]}]
        raw_dims = raw_data.get("dimensions", {})
        if isinstance(raw_dims, list):
            # Census format - we don't use fixed dims from here (they're in each observation)
            fixed_dims: dict[str, Any] = {}
        else:
            fixed_dims = raw_dims

        value_dicts = []
        for obs in observations:
            val_str = obs.get("observation")
            if val_str is None:
                continue

            try:
                val = float(val_str)
            except (ValueError, TypeError):
                continue

            # Extract dimension values from observation
            obs_dims = obs.get("dimensions", {})

            # Get time period - Census may use different time dimension names
            time_dim = obs_dims.get("Time") or obs_dims.get("time") or obs_dims.get("census_year")
            if isinstance(time_dim, dict):
                time_period = time_dim.get("id") or time_dim.get("label", "")
            else:
                time_period = str(time_dim) if time_dim else ""

            # For Census 2021, default time to "2021" if not found
            if is_census and not time_period:
                time_period = "2021"

            # Get geography - check observation dimensions first, then fixed dims
            # For Census 2021, check additional geo dimension names
            geo_dim = obs_dims.get("geography") or obs_dims.get("Geography")

            # Check Census geography dimensions if standard geography not found
            if geo_dim is None:
                for geo_key in self.CENSUS_GEO_DIMENSIONS:
                    geo_dim = obs_dims.get(geo_key)
                    if geo_dim is not None:
                        break

            if geo_dim is None:
                # Check fixed dimensions from response
                fixed_geo = fixed_dims.get("geography", {}).get("option", {})
                geo = fixed_geo.get("id", "K02000001")  # Default to UK
            elif isinstance(geo_dim, dict):
                geo = geo_dim.get("id") or geo_dim.get("label", "K02000001")
            else:
                geo = str(geo_dim) if geo_dim else "K02000001"

            # Build indicator from dataset code and other dimensions
            # Include relevant non-time, non-geo dimensions
            # Exclude Census geo dimensions as well as standard geography
            excluded_dims = {"time", "geography"} | set(self.CENSUS_GEO_DIMENSIONS)

            indicator_parts = [dataset_code]
            for dim_name, dim_val in obs_dims.items():
                if dim_name.lower() not in excluded_dims:
                    if isinstance(dim_val, dict):
                        indicator_parts.append(dim_val.get("id", ""))
                    else:
                        indicator_parts.append(str(dim_val))

            # Also add fixed dimensions
            for dim_name, dim_info in fixed_dims.items():
                if dim_name.lower() not in excluded_dims:
                    if isinstance(dim_info, dict):
                        option = dim_info.get("option", {})
                        if isinstance(option, dict):
                            dim_id = option.get("id", "")
                            if dim_id and dim_id not in indicator_parts:
                                indicator_parts.append(dim_id)

            indicator = "_".join(filter(None, indicator_parts))

            value_dicts.append(
                {
                    "geo": geo,
                    "time_period": time_period,
                    "indicator": indicator,
                    "value": val,
                    "unit": unit,
                    "flags": None,  # ONS doesn't provide flags in API
                }
            )

        return value_dicts

    async def list_available_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available ONS datasets.

        Args:
            category: Optional category filter (unused for ONS)

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
