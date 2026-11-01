"""OECD service layer for business logic orchestration.

This module coordinates repository, cache, and database operations for
OECD data fetching and storage.
"""

from datetime import datetime
from typing import Any

import structlog
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.infrastructure.cache import Cache, get_cache
from ecox_platform.logging_config import truncate_error
from ecox_platform.sources.base.service import BaseService
from ecox_platform.sources.oecd.models import OecdDataResponse
from ecox_platform.sources.oecd.repository import OecdRepository

logger = structlog.get_logger(__name__)


class OecdService(BaseService):
    """Service layer for OECD data operations.

    Coordinates fetching, caching, parsing, and storing OECD SDMX data.
    """

    def __init__(
        self,
        repository: OecdRepository | None = None,
        cache: Cache | None = None,
        rate_limit: float = 1.0,
    ) -> None:
        """Initialize the OECD service.

        Args:
            repository: OECD repository (creates new one if not provided)
            cache: Cache instance (uses global cache if not provided)
            rate_limit: Rate limit in requests per second
        """
        repo = repository or OecdRepository(rate_limit=rate_limit)
        cache_instance = cache or get_cache()

        super().__init__(
            repository=repo,
            cache=cache_instance,
            source_name="oecd",
        )

        logger.info("OECD service initialized")

    async def fetch_and_store(
        self,
        dataset_code: str,
        filters: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Fetch dataset from OECD and store in database.

        Uses content hashing and UPSERT to minimize database operations:
        - Skips entirely if data hasn't changed (hash match)
        - Uses UPSERT to preserve IDs for existing rows
        - Only allocates new IDs for truly new data points

        Args:
            dataset_code: Full dataflow code (agencyID,dataflowId,version)
            filters: Optional filters (dimension values, time period)
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

            # Parse the SDMX-JSON response
            value_dicts = self._transform_sdmx_data(data, dataset_code)

            logger.info(
                "Fetched OECD data",
                dataset_code=dataset_code,
                value_count=len(value_dicts),
            )

            # Return early if no session (just fetch, no store)
            if not session:
                return {
                    "dataset_code": dataset_code,
                    "source": "oecd",
                    "records_fetched": len(value_dicts),
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
                dataset_name=ds_metadata.get("name") or dataset_code,
                description=ds_metadata.get("description"),
                source_last_update=None,  # OECD doesn't provide this in TOC
                source_url=ds_metadata.get("metadata_url"),
            )

            # Use template method for change detection and storage
            result = await self.store_with_change_detection(
                session=session,
                dataset=dataset,
                value_dicts=value_dicts,
                filters=filters,
                started_at=started_at,
            )

            # Override records_fetched with original count
            result["records_fetched"] = len(value_dicts)
            return result

        except Exception as e:
            logger.error(
                "Failed to fetch and store OECD dataset",
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

    def _transform_sdmx_data(self, data: dict[str, Any], dataset_code: str) -> list[dict[str, Any]]:
        """Transform OECD SDMX-JSON data to common value format.

        SDMX-JSON has a complex structure:
        - Structure defines dimension and attribute metadata
        - DataSet contains series indexed by dimension key
        - Each series has observations indexed by time position

        Args:
            data: Raw SDMX-JSON response
            dataset_code: Dataset code for error context

        Returns:
            List of value dictionaries in common format
        """
        value_dicts: list[dict[str, Any]] = []

        try:
            # Parse with Pydantic for type safety
            response = OecdDataResponse(**data)
        except Exception as e:
            logger.warning(
                "Failed to parse OECD response with model, using raw dict",
                dataset_code=dataset_code,
                error=str(e),
            )
            return self._transform_sdmx_data_raw(data, dataset_code)

        structure = response.get_structure()
        dataset = response.get_dataset()

        if not structure or not dataset:
            logger.warning(
                "Missing structure or dataset in OECD response",
                dataset_code=dataset_code,
            )
            return value_dicts

        # Build dimension lookups
        series_dims = structure.dimensions.series if structure.dimensions else []
        obs_dims = structure.dimensions.observation if structure.dimensions else []

        # Build observation attribute lookup (for OBS_STATUS flags)
        obs_attributes = structure.attributes.observation if structure.attributes else []
        obs_status_index = None
        obs_status_values: list[str] = []
        for idx, attr in enumerate(obs_attributes):
            if attr.id == "OBS_STATUS":
                obs_status_index = idx
                obs_status_values = [v.id or "" for v in attr.values]
                break

        # Get time period values
        time_values: list[str] = []
        for obs_dim in obs_dims:
            if obs_dim.id == "TIME_PERIOD":
                time_values = [v.id for v in obs_dim.values]
                break

        # Process each series
        for series_key, series_data in dataset.series.items():
            # Parse series key to get dimension values
            try:
                dim_indices = [int(i) for i in series_key.split(":")]
            except (ValueError, TypeError):
                # Skip malformed series keys (e.g., non-integer indices)
                logger.warning(
                    "Skipping malformed series key",
                    series_key=series_key,
                    dataset_code=dataset_code,
                )
                continue

            # Extract dimension values
            geo = None
            measure = None
            unit = None
            freq = None

            for idx, dim_idx in enumerate(dim_indices):
                if idx >= len(series_dims):
                    break
                dim = series_dims[idx]
                if dim_idx < len(dim.values):
                    dim_value = dim.values[dim_idx].id

                    if dim.id == "REF_AREA":
                        geo = dim_value
                    elif dim.id == "MEASURE":
                        measure = dim_value
                    elif dim.id == "UNIT_MEASURE":
                        unit = dim_value
                    elif dim.id == "FREQ":
                        freq = dim_value

            # Default geo if not found
            if not geo:
                geo = "OECD"

            # Build indicator from measure and frequency
            indicator = measure or dataset_code
            if freq:
                indicator = f"{indicator}_{freq}"

            # Note: Unit could also come from series attributes, but decoding
            # requires attribute metadata which adds complexity. For now,
            # we only use UNIT_MEASURE dimension if available.

            # Process observations
            observations = series_data.get("observations", {})
            for obs_key, obs_values in observations.items():
                try:
                    obs_idx = int(obs_key)
                except (ValueError, TypeError):
                    continue

                # Get time period
                if obs_idx < len(time_values):
                    time_period = time_values[obs_idx]
                else:
                    continue

                # Get value (first element in observations array)
                if not obs_values or obs_values[0] is None:
                    continue

                try:
                    value = float(obs_values[0])
                except (ValueError, TypeError):
                    continue

                # Get flags from OBS_STATUS attribute
                flags = None
                if obs_status_index is not None and len(obs_values) > obs_status_index + 1:
                    flag_idx = obs_values[obs_status_index + 1]
                    if flag_idx is not None and flag_idx < len(obs_status_values):
                        flags = obs_status_values[flag_idx]

                value_dicts.append(
                    {
                        "geo": geo,
                        "time_period": time_period,
                        "indicator": indicator,
                        "value": value,
                        "unit": unit,
                        "flags": flags,
                    }
                )

        return value_dicts

    def _transform_sdmx_data_raw(
        self, data: dict[str, Any], dataset_code: str
    ) -> list[dict[str, Any]]:
        """Fallback transformation using raw dict access.

        Used when Pydantic parsing fails.

        Args:
            data: Raw SDMX-JSON response
            dataset_code: Dataset code for error context

        Returns:
            List of value dictionaries in common format
        """
        value_dicts: list[dict[str, Any]] = []

        try:
            structures = data.get("data", {}).get("structures", [])
            datasets = data.get("data", {}).get("dataSets", [])

            if not structures or not datasets:
                return value_dicts

            structure = structures[0]
            dataset = datasets[0]

            # Get dimension info
            dims = structure.get("dimensions", {})
            series_dims = dims.get("series", [])
            obs_dims = dims.get("observation", [])

            # Get time period values
            time_values: list[str] = []
            for obs_dim in obs_dims:
                if obs_dim.get("id") == "TIME_PERIOD":
                    time_values = [v.get("id", "") for v in obs_dim.get("values", [])]
                    break

            # Process series
            series_dict = dataset.get("series", {})
            for series_key, series_data in series_dict.items():
                # Parse series key
                dim_indices = [int(i) for i in series_key.split(":")]

                # Extract key dimensions
                geo = "OECD"
                measure = dataset_code
                unit = None
                freq = None

                for idx, dim_idx in enumerate(dim_indices):
                    if idx >= len(series_dims):
                        break
                    dim = series_dims[idx]
                    dim_values = dim.get("values", [])
                    if dim_idx < len(dim_values):
                        dim_value = dim_values[dim_idx].get("id", "")
                        dim_id = dim.get("id", "")

                        if dim_id == "REF_AREA":
                            geo = dim_value
                        elif dim_id == "MEASURE":
                            measure = dim_value
                        elif dim_id == "UNIT_MEASURE":
                            unit = dim_value
                        elif dim_id == "FREQ":
                            freq = dim_value

                indicator = measure
                if freq:
                    indicator = f"{indicator}_{freq}"

                # Process observations
                observations = series_data.get("observations", {})
                for obs_key, obs_values in observations.items():
                    try:
                        obs_idx = int(obs_key)
                    except (ValueError, TypeError):
                        continue

                    if obs_idx >= len(time_values):
                        continue

                    time_period = time_values[obs_idx]

                    if not obs_values or obs_values[0] is None:
                        continue

                    try:
                        value = float(obs_values[0])
                    except (ValueError, TypeError):
                        continue

                    value_dicts.append(
                        {
                            "geo": geo,
                            "time_period": time_period,
                            "indicator": indicator,
                            "value": value,
                            "unit": unit,
                            "flags": None,
                        }
                    )

        except Exception as e:
            logger.error(
                "Failed to transform OECD data (raw)",
                dataset_code=dataset_code,
                error=str(e),
            )

        return value_dicts

    async def list_available_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available OECD datasets.

        Args:
            category: Optional category filter (agency prefix)

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
