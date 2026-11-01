"""ONS repository implementation.

This module implements the repository pattern for fetching data from
the UK Office for National Statistics (ONS) API.
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

from ecox_platform.infrastructure.cache import get_cache
from ecox_platform.sources.base.repository import BaseRepository
from ecox_platform.sources.ons.models import (
    OnsDatasetsResponse,
    OnsEditionsResponse,
)


class SkippedDatasetError(Exception):
    """Raised when a dataset is intentionally skipped (not a failure).

    This exception signals that a dataset was skipped due to being marked
    as problematic (consistent server errors), not because of a transient failure.
    The source worker should NOT count this as a failure for consecutive failure tracking.
    """

    pass


logger = structlog.get_logger(__name__)

# ONS API base URL
ONS_BASE_URL = "https://api.beta.ons.gov.uk/v1"

# Cache constants
TOC_CACHE_KEY = "__toc__"
TOC_TTL_SECONDS = 6 * 3600  # 6 hours

# Census 2021 dataset prefixes - these use /json endpoint instead of /observations
CENSUS_2021_PREFIXES = ("TS", "RM", "ST")


def is_census_2021_dataset(dataset_code: str) -> bool:
    """Check if dataset uses Census 2021 JSON endpoint.

    Census 2021 datasets use a different API pattern:
    - Endpoint: /datasets/{id}/editions/{edition}/versions/{version}/json
    - Returns flat observation array (cartesian product of dimensions)
    - No dimension parameter queries needed

    Standard datasets use /observations endpoint with dimension parameters.

    Args:
        dataset_code: Dataset identifier (e.g., "TS001", "trade")

    Returns:
        True if this is a Census 2021 dataset requiring /json endpoint
    """
    return dataset_code.upper().startswith(CENSUS_2021_PREFIXES)


class OnsRepository(BaseRepository):
    """Repository for fetching data from ONS API.

    Implements the BaseRepository interface for ONS-specific operations.
    """

    def __init__(
        self,
        http_client: ResilientHttpClient | None = None,
        rate_limit: float = 2.0,
    ) -> None:
        """Initialize the ONS repository.

        Args:
            http_client: Optional HTTP client (creates new one if not provided)
            rate_limit: Rate limit in requests per second
        """
        self.http_client = http_client or ResilientHttpClient(
            base_url=ONS_BASE_URL,
            rate_limit=rate_limit,
        )
        self._version_cache: dict[str, dict[str, Any]] = {}

        # Problematic dataset tracking (for 500 errors)
        self._failure_counts: dict[str, int] = {}
        self._problematic_datasets: set[str] = set()
        self._failure_threshold = 1  # Mark as problematic after first 500 error (server bugs)

        logger.info("ONS repository initialized")

    def record_dataset_failure(self, dataset_id: str) -> None:
        """Record a failure for a dataset.

        After threshold consecutive failures, dataset is marked as problematic
        and will be skipped in future fetch attempts (until service restart).

        Args:
            dataset_id: The dataset identifier
        """
        self._failure_counts[dataset_id] = self._failure_counts.get(dataset_id, 0) + 1
        if self._failure_counts[dataset_id] >= self._failure_threshold:
            self._problematic_datasets.add(dataset_id)
            logger.warning(
                "Dataset marked as problematic after consecutive failures",
                dataset_id=dataset_id,
                failures=self._failure_counts[dataset_id],
            )

    def record_dataset_success(self, dataset_id: str) -> None:
        """Record a success for a dataset, resetting failure count.

        Args:
            dataset_id: The dataset identifier
        """
        self._failure_counts.pop(dataset_id, None)
        self._problematic_datasets.discard(dataset_id)

    def should_skip_dataset(self, dataset_id: str) -> bool:
        """Check if dataset should be skipped due to consistent failures.

        Args:
            dataset_id: The dataset identifier

        Returns:
            True if dataset should be skipped
        """
        return dataset_id in self._problematic_datasets

    async def _get_latest_version(self, dataset_id: str) -> dict[str, Any] | None:
        """Get the latest version info for a dataset.

        Caches version info to avoid repeated API calls.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Version info dict with edition, version number, and metadata
        """
        if dataset_id in self._version_cache:
            return self._version_cache[dataset_id]

        try:
            # Get editions
            editions_data = await self.http_client.get(f"datasets/{dataset_id}/editions")
            editions_response = OnsEditionsResponse(**editions_data)

            if not editions_response.items:
                return None

            # Get first (usually "time-series") edition
            edition = editions_response.items[0].edition

            # Get latest version from edition links
            latest_version_link = editions_response.items[0].links
            if latest_version_link and "latest_version" in latest_version_link:
                # Extract version number from link
                version_id = latest_version_link["latest_version"].get("id", "1")
            else:
                # Fall back to version 1
                version_id = "1"

            # Get version metadata
            version_data = await self.http_client.get(
                f"datasets/{dataset_id}/editions/{edition}/versions/{version_id}"
            )

            version_info = {
                "edition": edition,
                "version": version_id,
                "metadata": version_data,
            }

            self._version_cache[dataset_id] = version_info
            return version_info

        except Exception as e:
            logger.warning(
                "Failed to get latest version for dataset",
                dataset_id=dataset_id,
                error=str(e),
            )
            return None

    async def get_dataset(
        self, dataset_code: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch observations for a specific dataset from ONS API.

        Routes to the appropriate endpoint based on dataset type:
        - Census 2021 datasets (TS/RM/ST): /json endpoint
        - Standard datasets: /observations endpoint

        Args:
            dataset_code: Dataset identifier (e.g., "trade", "TS001")
            filters: Optional filters including dimension values to query

        Returns:
            Dictionary containing observations and metadata

        Raises:
            ValueError: If dataset_code is invalid, dimensions missing, or problematic
        """
        # Skip datasets marked as problematic (consistent 500 errors)
        if self.should_skip_dataset(dataset_code):
            logger.info(
                "Skipping problematic dataset",
                dataset_code=dataset_code,
            )
            raise ValueError(
                f"Dataset {dataset_code} marked as problematic (consistent 500 errors)"
            )

        # Get latest version info
        version_info = await self._get_latest_version(dataset_code)
        if not version_info:
            raise ValueError(f"Could not find dataset: {dataset_code}")

        edition = version_info["edition"]
        version = version_info["version"]
        metadata = version_info["metadata"]

        # Route to appropriate endpoint based on dataset type
        if is_census_2021_dataset(dataset_code):
            return await self._fetch_census_json(dataset_code, edition, version, metadata, filters)
        else:
            return await self._fetch_observations(dataset_code, edition, version, metadata, filters)

    async def _fetch_observations(
        self,
        dataset_code: str,
        edition: str,
        version: str,
        metadata: dict[str, Any],
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch standard dataset observations from /observations endpoint.

        This handles non-Census datasets that require dimension parameters.

        Args:
            dataset_code: Dataset identifier
            edition: Edition name
            version: Version number
            metadata: Version metadata
            filters: Optional dimension filters

        Returns:
            Dictionary containing observations and metadata
        """
        # Build observations URL
        base_path = f"datasets/{dataset_code}/editions/{edition}/versions/{version}/observations"

        # Get dimensions from metadata
        dimensions = metadata.get("dimensions", [])
        if not dimensions:
            raise ValueError(f"No dimensions found for dataset: {dataset_code}")

        # Build query params - require all dimensions
        params: dict[str, str] = {}

        # If filters provided, use them; otherwise use wildcards for time only
        if filters:
            for dim in dimensions:
                dim_name = dim.get("name", "")
                if dim_name in filters:
                    params[dim_name] = filters[dim_name]
                elif dim_name == "time":
                    # Default to wildcard for time dimension
                    params[dim_name] = "*"
                else:
                    # Need to get first option for other dimensions
                    first_option = await self._get_first_dimension_option(
                        dataset_code, edition, version, dim_name
                    )
                    if first_option:
                        params[dim_name] = first_option
        else:
            # No filters - use wildcards for time, first option for others
            for dim in dimensions:
                dim_name = dim.get("name", "")
                if dim_name == "time":
                    params[dim_name] = "*"
                else:
                    first_option = await self._get_first_dimension_option(
                        dataset_code, edition, version, dim_name
                    )
                    if first_option:
                        params[dim_name] = first_option

        logger.info(
            "Fetching ONS observations",
            dataset_code=dataset_code,
            edition=edition,
            version=version,
            params=params,
        )

        try:
            data = await self.http_client.get(base_path, params=params)

            # Success - reset failure count
            self.record_dataset_success(dataset_code)

            # Add metadata to response
            data["_metadata"] = {
                "dataset_code": dataset_code,
                "edition": edition,
                "version": version,
                "unit_of_measure": metadata.get("unit_of_measure"),
                "last_updated": metadata.get("last_updated"),
            }

            return data

        except Exception as e:
            error_str = str(e)

            # Track all 5xx server errors - these may be transient or permanent
            # 500 = Internal Server Error
            # 502 = Bad Gateway (common with ONS Beta API)
            # 503 = Service Unavailable
            # 504 = Gateway Timeout
            if any(code in error_str for code in ["500", "502", "503", "504"]):
                self.record_dataset_failure(dataset_code)

            logger.error(
                "Failed to fetch ONS observations",
                dataset_code=dataset_code,
                error=error_str,
            )
            raise

    async def _get_first_dimension_option(
        self, dataset_id: str, edition: str, version: str, dimension: str
    ) -> str | None:
        """Get the first valid option for a dimension.

        Skips negative values (like -8) which are metadata codes ("Does not apply")
        that cause API 500 errors when used in observation queries.

        Args:
            dataset_id: Dataset identifier
            edition: Edition name
            version: Version number
            dimension: Dimension name

        Returns:
            First valid option value or None
        """
        try:
            path = f"datasets/{dataset_id}/editions/{edition}/versions/{version}/dimensions/{dimension}/options"
            # Fetch more options to find a valid one (skipping negative codes)
            data = await self.http_client.get(path, params={"limit": 20})

            items = data.get("items", [])
            for item in items:
                option: str | None = item.get("option")
                if option is None:
                    continue

                # Skip negative values - these are metadata codes like -8 ("Does not apply")
                # that cause ONS API 500 errors when used in observation queries
                try:
                    if option.lstrip("-").isdigit() and int(option) < 0:
                        logger.debug(
                            "Skipping negative dimension option",
                            dataset_id=dataset_id,
                            dimension=dimension,
                            option=option,
                        )
                        continue
                except (ValueError, AttributeError):
                    pass  # Non-numeric options are fine to use

                return option

            # If all options were negative, return None (dataset will fail gracefully)
            logger.warning(
                "No valid dimension options found (all negative)",
                dataset_id=dataset_id,
                dimension=dimension,
            )
            return None

        except Exception as e:
            logger.warning(
                "Failed to get dimension option",
                dataset_id=dataset_id,
                dimension=dimension,
                error=str(e),
            )
            return None

    async def _fetch_census_json(
        self,
        dataset_code: str,
        edition: str,
        version: str,
        metadata: dict[str, Any],
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Fetch Census 2021 data from /json endpoint.

        Census 2021 datasets (TS###, RM###, ST###) use a different API pattern:
        - Endpoint: /datasets/{id}/editions/{edition}/versions/{version}/json
        - Response contains dimensions as arrays with options
        - Observations is a flat array of numbers (cartesian product)

        Args:
            dataset_code: Dataset identifier (TS001, RM001, etc.)
            edition: Edition name (usually "2021")
            version: Version number
            metadata: Version metadata
            filters: Optional filters (not currently used for Census)

        Returns:
            Normalized response matching observations format
        """
        base_path = f"datasets/{dataset_code}/editions/{edition}/versions/{version}/json"

        logger.info(
            "Fetching Census 2021 JSON data",
            dataset_code=dataset_code,
            edition=edition,
            version=version,
        )

        try:
            data = await self.http_client.get(base_path)

            # Transform Census response to match observations format
            observations = self._transform_census_to_observations(data, dataset_code)

            # Success - reset failure count
            self.record_dataset_success(dataset_code)

            return {
                "observations": observations,
                "dimensions": data.get("dimensions", []),
                "_metadata": {
                    "dataset_code": dataset_code,
                    "edition": edition,
                    "version": version,
                    "unit_of_measure": metadata.get("unit_of_measure"),
                    "last_updated": metadata.get("last_updated"),
                    "census_2021": True,  # Flag for service layer
                },
                "total_observations": data.get("total_observations", len(observations)),
            }

        except Exception as e:
            error_str = str(e)
            if any(code in error_str for code in ["500", "502", "503", "504"]):
                self.record_dataset_failure(dataset_code)
            logger.error(
                "Failed to fetch Census JSON",
                dataset_code=dataset_code,
                error=error_str,
            )
            raise

    def _transform_census_to_observations(
        self,
        data: dict[str, Any],
        dataset_code: str,
    ) -> list[dict[str, Any]]:
        """Transform Census 2021 JSON response to observation format.

        Census JSON structure:
        {
            "dimensions": [
                {"dimension_name": "ltla", "options": [{"id": "E06000001", "label": "Hartlepool"}, ...]},
                {"dimension_name": "residence_type", "options": [{"id": "1", "label": "Household"}, ...]}
            ],
            "observations": [91471, 867, 141421, 2505, ...]  # Flat array
        }

        The flat observations array corresponds to all combinations of dimension options
        in the order they appear (cartesian product). We map flat indices back to
        dimension values using stride calculations.

        Args:
            data: Raw Census JSON response
            dataset_code: Dataset identifier for logging

        Returns:
            List of observation dicts matching standard format
        """
        dimensions = data.get("dimensions", [])
        raw_observations = data.get("observations", [])

        if not dimensions or not raw_observations:
            logger.warning(
                "Empty Census data",
                dataset_code=dataset_code,
                dimensions_count=len(dimensions),
                observations_count=len(raw_observations),
            )
            return []

        # Build list of dimension options in order
        dimension_lists: list[list[dict[str, Any]]] = []
        dimension_names: list[str] = []

        for dim in dimensions:
            dim_name = dim.get("dimension_name", "") or dim.get("name", "")
            options = dim.get("options", [])
            dimension_names.append(dim_name)
            dimension_lists.append(options)

        # Calculate strides for index mapping (like NumPy's multi-dimensional indexing)
        # For dimensions [A, B, C] with sizes [2, 3, 4], strides = [12, 4, 1]
        strides = [1]
        for dim_list in reversed(dimension_lists[1:]):
            strides.insert(0, strides[0] * len(dim_list))

        observations: list[dict[str, Any]] = []

        for idx, value in enumerate(raw_observations):
            if value is None:
                continue

            # Map flat index to dimension indices
            obs_dims: dict[str, dict[str, str]] = {}
            remaining = idx

            for i, (dim_name, dim_options) in enumerate(
                zip(dimension_names, dimension_lists, strict=False)
            ):
                if not dim_options:
                    continue
                dim_idx = remaining // strides[i]
                remaining = remaining % strides[i]

                if dim_idx < len(dim_options):
                    option = dim_options[dim_idx]
                    obs_dims[dim_name] = {
                        "id": option.get("id", ""),
                        "label": option.get("label", ""),
                    }

            observations.append(
                {
                    "observation": str(value),
                    "dimensions": obs_dims,
                }
            )

        logger.info(
            "Transformed Census observations",
            dataset_code=dataset_code,
            raw_count=len(raw_observations),
            transformed_count=len(observations),
        )

        return observations

    async def fetch_toc(
        self, session: AsyncSession | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch and parse the ONS Table of Contents (datasets list).

        Args:
            session: Optional DB session for caching
            force_refresh: If True, bypass caches and fetch from API

        Returns:
            List of dataset metadata dictionaries
        """
        cache = get_cache()

        # 1. Check memory cache first (fastest) - unless forced
        if not force_refresh:
            cached_toc = cache.get("ons", TOC_CACHE_KEY)
            if cached_toc is not None:
                logger.debug("Returning cached ONS TOC (memory)", count=len(cached_toc))
                return list(cached_toc)

        # 2. Check DB cache if session provided - unless forced
        if not force_refresh and session:
            try:
                statement = select(SourceMetadata).where(SourceMetadata.source == "ons")
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
                                "Returning cached ONS TOC (DB)",
                                count=len(toc_data),
                                age_hours=age.total_seconds() / 3600,
                            )
                            cache.set("ons", TOC_CACHE_KEY, toc_data, ttl_seconds=TOC_TTL_SECONDS)
                            return toc_data
                        else:
                            # Stale but return anyway
                            logger.info(
                                "Returning STALE ONS TOC (DB)",
                                count=len(toc_data),
                                age_hours=age.total_seconds() / 3600,
                            )
                            cache.set("ons", TOC_CACHE_KEY, toc_data, ttl_seconds=TOC_TTL_SECONDS)
                            return toc_data

                    except json.JSONDecodeError:
                        logger.warning("Failed to decode cached TOC from DB")
            except Exception as e:
                logger.warning("Failed to check DB cache for TOC", error=str(e))

        # 3. Fetch from API
        try:
            logger.info("Fetching ONS Table of Contents")

            all_datasets: list[dict[str, Any]] = []
            offset = 0
            limit = 100  # API max is typically 100

            while True:
                data = await self.http_client.get(
                    "datasets", params={"limit": limit, "offset": offset}
                )

                try:
                    response = OnsDatasetsResponse(**data)
                except ValidationError as e:
                    logger.warning("ONS datasets response validation error", error=str(e))
                    # Try to continue with raw data
                    items = data.get("items", [])
                    total_count = data.get("total_count", 0)
                else:
                    items = response.items
                    total_count = response.total_count

                for item in items:
                    if isinstance(item, dict):
                        ds = item
                    else:
                        ds = item.model_dump() if hasattr(item, "model_dump") else dict(item)

                    # Get latest version link for last_update
                    last_update = ds.get("last_updated")

                    all_datasets.append(
                        {
                            "code": ds.get("id"),
                            "name": ds.get("title"),
                            "description": ds.get("description"),
                            "category": "ons",
                            "last_update": last_update,
                            "keywords": ds.get("keywords"),
                            "unit_of_measure": ds.get("unit_of_measure"),
                            "release_frequency": ds.get("release_frequency"),
                            "metadata_url": f"https://www.ons.gov.uk/datasets/{ds.get('id')}",
                        }
                    )

                # Check if we've fetched all
                if len(items) < limit or offset + len(items) >= total_count:
                    break

                offset += limit

            logger.info("Parsed ONS TOC", dataset_count=len(all_datasets))

            # Update memory cache
            cache.set("ons", TOC_CACHE_KEY, all_datasets, ttl_seconds=TOC_TTL_SECONDS)

            # Update DB cache if session provided
            if session:
                try:
                    statement = select(SourceMetadata).where(SourceMetadata.source == "ons")
                    result = await session.exec(statement)
                    metadata = result.one_or_none()

                    if not metadata:
                        metadata = SourceMetadata(source="ons")
                        session.add(metadata)

                    metadata.total_datasets = len(all_datasets)
                    metadata.cached_toc = json.dumps(all_datasets)
                    metadata.last_updated = datetime.now()

                    await session.commit()
                    logger.info("Updated ONS TOC in DB cache")
                except Exception as e:
                    logger.error("Failed to update DB cache for TOC", error=str(e))

            return all_datasets

        except Exception as e:
            logger.error("Failed to fetch/parse ONS TOC", error=str(e))
            return []

    async def list_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available datasets from ONS.

        Args:
            category: Optional category filter (not used for ONS)

        Returns:
            List of dataset metadata
        """
        return await self.fetch_toc()

    async def list_discoverable_datasets(
        self, session: AsyncSession | None = None
    ) -> list[dict[str, Any]]:
        """List all discoverable datasets from ONS.

        Args:
            session: Optional database session for caching

        Returns:
            List of all available datasets from TOC
        """
        return await self.fetch_toc(session=session)

    async def search_datasets(self, query: str) -> list[dict[str, Any]]:
        """Search for datasets by keyword.

        Uses local filtering over cached TOC since ONS search returns
        mixed content types.

        Args:
            query: Search query string

        Returns:
            List of matching dataset metadata dictionaries
        """
        query_lower = query.lower()
        toc = await self.fetch_toc()

        results = []
        for ds in toc:
            # Search in name, description, and keywords
            name = (ds.get("name") or "").lower()
            desc = (ds.get("description") or "").lower()
            keywords = ds.get("keywords") or []

            if (
                query_lower in name
                or query_lower in desc
                or any(query_lower in kw.lower() for kw in keywords)
            ):
                results.append(ds)

        logger.info("ONS search completed", query=query, results=len(results))
        return results

    async def get_dataset_metadata(self, dataset_code: str) -> dict[str, Any]:
        """Get metadata for a specific dataset.

        Args:
            dataset_code: Dataset identifier

        Returns:
            Dataset metadata including dimensions, units, etc.

        Raises:
            ValueError: If dataset_code is invalid
        """
        try:
            # Get basic dataset info
            data = await self.http_client.get(f"datasets/{dataset_code}")

            # Get version info for dimensions
            version_info = await self._get_latest_version(dataset_code)
            if version_info:
                data["dimensions"] = version_info["metadata"].get("dimensions", [])
                data["edition"] = version_info["edition"]
                data["version"] = version_info["version"]
                data["last_updated"] = version_info["metadata"].get("last_updated")
                if not data.get("unit_of_measure"):
                    data["unit_of_measure"] = version_info["metadata"].get("unit_of_measure")

            data["metadata_url"] = f"https://www.ons.gov.uk/datasets/{dataset_code}"

            return data

        except Exception as e:
            logger.error(
                "Failed to get ONS dataset metadata",
                dataset_code=dataset_code,
                error=str(e),
            )
            raise ValueError(f"Failed to get metadata for dataset: {dataset_code}") from e

    async def validate_filters(self, dataset_code: str, filters: dict[str, Any]) -> bool:
        """Validate filters for ONS requests.

        Args:
            dataset_code: Dataset identifier
            filters: Filters to validate

        Returns:
            True if valid (ONS is flexible with dimension values)
        """
        # ONS API validates dimensions itself
        # We just check that required dimensions are provided
        return True

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.close()
