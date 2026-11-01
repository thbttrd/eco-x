"""OECD repository implementation.

This module implements the repository pattern for fetching data from
the OECD SDMX 2.1 REST API.
"""

import asyncio
import json
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog
from ecox_shared.models import SourceMetadata
from ecox_shared.utils import ResilientHttpClient
from pydantic import ValidationError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.config import settings
from ecox_platform.infrastructure.cache import get_cache
from ecox_platform.sources.base.repository import BaseRepository
from ecox_platform.sources.oecd.models import (
    OecdDataflowsResponse,
    OecdDataResponse,
    OecdDatasetInfo,
)

logger = structlog.get_logger(__name__)

# OECD SDMX API base URL
OECD_BASE_URL = "https://sdmx.oecd.org/public/rest"

# Cache constants
TOC_CACHE_KEY = "__toc__"
TOC_TTL_SECONDS = 6 * 3600  # 6 hours
STRUCTURE_CACHE_MAX_SIZE = 100  # Max entries in structure LRU cache


class LRUCache:
    """Simple LRU cache implementation using OrderedDict.

    Uses composition instead of inheritance to avoid signature conflicts.
    """

    def __init__(self, max_size: int = 100) -> None:
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.max_size = max_size

    def get(self, key: str) -> dict[str, Any] | None:
        """Get item and move to end (most recently used)."""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: str, value: dict[str, Any]) -> None:
        """Add item and evict oldest if over capacity."""
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def __len__(self) -> int:
        """Return number of items in cache."""
        return len(self._cache)


class OecdRepository(BaseRepository):
    """Repository for fetching data from OECD SDMX API.

    Implements the BaseRepository interface for OECD-specific operations.
    """

    def __init__(
        self,
        http_client: ResilientHttpClient | None = None,
        rate_limit: float | None = None,
    ) -> None:
        """Initialize the OECD repository.

        Args:
            http_client: Optional HTTP client (creates new one if not provided)
            rate_limit: Rate limit in requests per second (uses config default if not provided)
        """
        effective_rate_limit = rate_limit or settings.oecd_rate_limit

        self.http_client = http_client or ResilientHttpClient(
            base_url=OECD_BASE_URL,
            rate_limit=effective_rate_limit,
            timeout=60,  # SDMX responses can be large
        )

        # LRU cache for structure metadata (bounded to prevent memory growth)
        self._structure_cache: LRUCache = LRUCache(max_size=STRUCTURE_CACHE_MAX_SIZE)

        # Rate limiter for structure requests (same rate as data requests)
        self._structure_rate_limit = effective_rate_limit
        self._structure_semaphore = asyncio.Semaphore(1)
        self._last_structure_request: float = 0.0

        # Lazy-initialized httpx client for structure requests
        self._structure_client: httpx.AsyncClient | None = None

        logger.info("OECD repository initialized", rate_limit=effective_rate_limit)

    async def _get_structure_client(self) -> httpx.AsyncClient:
        """Get or create the structure HTTP client (lazy initialization).

        Returns:
            The httpx AsyncClient for structure requests
        """
        if self._structure_client is None:
            self._structure_client = httpx.AsyncClient(
                base_url=OECD_BASE_URL,
                timeout=60.0,
                follow_redirects=True,
                headers={"Accept": "application/vnd.sdmx.structure+json"},
            )
        return self._structure_client

    async def _get_structure_json(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make a GET request for structure/metadata with SDMX JSON Accept header.

        Includes rate limiting to avoid API throttling.

        Args:
            path: API path
            params: Query parameters

        Returns:
            JSON response as dict
        """
        # Apply rate limiting
        async with self._structure_semaphore:
            now = asyncio.get_event_loop().time()
            min_interval = 1.0 / self._structure_rate_limit
            elapsed = now - self._last_structure_request

            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)

            client = await self._get_structure_client()
            response = await client.get(f"/{path}", params=params)
            response.raise_for_status()

            self._last_structure_request = asyncio.get_event_loop().time()
            result: dict[str, Any] = response.json()
            return result

    async def _get_dataflow_structure(self, dataflow_code: str) -> dict[str, Any] | None:
        """Get structure metadata for a dataflow.

        Uses LRU cache to bound memory usage (max 100 entries).

        Args:
            dataflow_code: Full dataflow code (agencyID,dataflowId,version)

        Returns:
            Structure metadata dict or None if not found
        """
        # Check LRU cache first
        cached = self._structure_cache.get(dataflow_code)
        if cached is not None:
            return cached

        try:
            # Parse the dataflow code
            parts = dataflow_code.split(",")
            if len(parts) != 3:
                logger.warning(
                    "Invalid dataflow code format",
                    dataflow_code=dataflow_code,
                    expected="agencyID,dataflowId,version",
                )
                return None

            agency_id, dataflow_id, version = parts

            # Fetch dataflow with references to get structure
            path = f"dataflow/{agency_id}/{dataflow_id}/{version}"
            params = {"references": "all"}

            data = await self._get_structure_json(path, params=params)

            # Store in LRU cache (auto-evicts oldest if over capacity)
            self._structure_cache.put(dataflow_code, data)
            return data

        except Exception as e:
            logger.warning(
                "Failed to get dataflow structure",
                dataflow_code=dataflow_code,
                error=str(e),
            )
            return None

    async def get_dataset(
        self, dataset_code: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch observations for a specific dataset from OECD API.

        Args:
            dataset_code: Full dataflow code (agencyID,dataflowId,version)
            filters: Optional filters including dimension values

        Returns:
            Dictionary containing observations and metadata

        Raises:
            ValueError: If dataset_code is invalid
        """
        # Parse the dataflow code
        parts = dataset_code.split(",")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid dataset code format: {dataset_code}. "
                f"Expected: agencyID,dataflowId,version"
            )

        agency_id, dataflow_id, version = parts

        # Build data URL path
        # Format: data/{agencyID},{dataflowId},{version}/{key}
        data_path = f"data/{agency_id},{dataflow_id},{version}"

        # Build the key from filters or use wildcard
        key = self._build_data_key(filters)
        if key:
            data_path = f"{data_path}/{key}"

        # Build query parameters
        params: dict[str, Any] = {"format": "jsondata"}

        # Add time period filters if provided
        if filters:
            if "startPeriod" in filters:
                params["startPeriod"] = filters["startPeriod"]
            if "endPeriod" in filters:
                params["endPeriod"] = filters["endPeriod"]

        logger.info(
            "Fetching OECD data",
            dataset_code=dataset_code,
            key=key,
            params=params,
        )

        try:
            # Use streaming for potentially large OECD data responses (can be 100MB+)
            data = await self.http_client.get_large(data_path, params=params)

            # Validate response structure (logs warning if invalid but continues)
            try:
                OecdDataResponse(**data)
            except ValidationError as e:
                logger.warning(
                    "OECD data response validation warning",
                    dataset_code=dataset_code,
                    error=str(e),
                )

            # Add metadata to response
            data["_metadata"] = {
                "dataset_code": dataset_code,
                "agency_id": agency_id,
                "dataflow_id": dataflow_id,
                "version": version,
            }

            return data

        except Exception as e:
            logger.error(
                "Failed to fetch OECD data",
                dataset_code=dataset_code,
                error=str(e),
            )
            raise

    def _build_data_key(self, filters: dict[str, Any] | None) -> str:
        """Build the SDMX data key from filters.

        OECD data keys are dimension values separated by dots.
        Missing values use wildcards (empty string between dots).

        Args:
            filters: Filter dictionary with dimension values

        Returns:
            Data key string (e.g., "USA+FRA.A......")
        """
        if not filters:
            return ""

        # Get dimension values from filters
        # Common OECD dimensions in typical order
        dimension_order = [
            "REF_AREA",
            "FREQ",
            "MEASURE",
            "UNIT_MEASURE",
            "ACTIVITY",
            "ADJUSTMENT",
            "TRANSFORMATION",
        ]

        key_parts = []
        for dim in dimension_order:
            if dim in filters:
                value = filters[dim]
                if isinstance(value, list):
                    # Multiple values: join with +
                    key_parts.append("+".join(value))
                else:
                    key_parts.append(str(value))
            else:
                # Wildcard (all values)
                key_parts.append("")

        # Join with dots and strip trailing empty parts
        key = ".".join(key_parts)

        # Remove trailing dots
        while key.endswith("."):
            key = key[:-1]

        return key

    async def fetch_toc(
        self, session: AsyncSession | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch and parse the OECD Table of Contents (dataflows list).

        Args:
            session: Optional DB session for caching
            force_refresh: If True, bypass caches and fetch from API

        Returns:
            List of dataset metadata dictionaries
        """
        cache = get_cache()

        # 1. Check memory cache first (fastest) - unless forced
        if not force_refresh:
            cached_toc = cache.get("oecd", TOC_CACHE_KEY)
            if cached_toc is not None:
                logger.debug("Returning cached OECD TOC (memory)", count=len(cached_toc))
                return list(cached_toc)

        # 2. Check DB cache if session provided - unless forced
        stale_toc_data: list[dict[str, Any]] | None = None
        if not force_refresh and session:
            try:
                statement = select(SourceMetadata).where(SourceMetadata.source == "oecd")
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
                                "Returning cached OECD TOC (DB)",
                                count=len(toc_data),
                                age_hours=age.total_seconds() / 3600,
                            )
                            cache.set("oecd", TOC_CACHE_KEY, toc_data, ttl_seconds=TOC_TTL_SECONDS)
                            return toc_data
                        else:
                            # Stale - save for fallback, but try to refresh first
                            logger.info(
                                "OECD TOC is stale, will attempt refresh",
                                count=len(toc_data),
                                age_hours=age.total_seconds() / 3600,
                            )
                            stale_toc_data = toc_data

                    except json.JSONDecodeError:
                        logger.warning("Failed to decode cached TOC from DB")
            except Exception as e:
                logger.warning("Failed to check DB cache for TOC", error=str(e))

        # 3. Fetch from API
        try:
            logger.info("Fetching OECD Table of Contents")

            # Fetch all dataflows
            data = await self._get_structure_json("dataflow")

            try:
                response = OecdDataflowsResponse(**data)
                dataflows = response.data.dataflows
            except ValidationError as e:
                logger.warning("OECD dataflows response validation error", error=str(e))
                # Try to continue with raw data
                dataflows = data.get("data", {}).get("dataflows", [])

            datasets = []
            for df in dataflows:
                if isinstance(df, dict):
                    # Raw dict from fallback
                    info = OecdDatasetInfo(
                        code=f"{df.get('agencyID')},{df.get('id')},{df.get('version')}",
                        agency_id=df.get("agencyID", ""),
                        dataflow_id=df.get("id", ""),
                        version=df.get("version", ""),
                        name=df.get("name"),
                        description=df.get("description"),
                    )
                else:
                    # Pydantic model
                    info = OecdDatasetInfo.from_dataflow(df)

                datasets.append(
                    {
                        "code": info.code,
                        "name": info.name or info.dataflow_id,
                        "description": info.description,
                        "category": f"oecd_{info.agency_id.split('.')[-1].lower()}"
                        if "." in info.agency_id
                        else "oecd",
                        "agency_id": info.agency_id,
                        "dataflow_id": info.dataflow_id,
                        "version": info.version,
                        "metadata_url": f"https://data-explorer.oecd.org/vis?tm=OECD&pg=0&df[ds]=dsDisseminateFinalDMZ&df[id]={info.dataflow_id}",
                    }
                )

            logger.info("Parsed OECD TOC", dataset_count=len(datasets))

            # Update memory cache
            cache.set("oecd", TOC_CACHE_KEY, datasets, ttl_seconds=TOC_TTL_SECONDS)

            # Update DB cache if session provided
            if session:
                try:
                    statement = select(SourceMetadata).where(SourceMetadata.source == "oecd")
                    result = await session.exec(statement)
                    metadata = result.one_or_none()

                    if not metadata:
                        metadata = SourceMetadata(source="oecd")
                        session.add(metadata)

                    metadata.total_datasets = len(datasets)
                    metadata.cached_toc = json.dumps(datasets)
                    metadata.last_updated = datetime.now()

                    await session.commit()
                    logger.info("Updated OECD TOC in DB cache")
                except Exception as e:
                    logger.error("Failed to update DB cache for TOC", error=str(e))

            return datasets

        except Exception as e:
            logger.error("Failed to fetch/parse OECD TOC", error=str(e))
            # Fall back to stale data if available (stale-while-revalidate)
            if stale_toc_data is not None:
                logger.warning(
                    "Returning stale OECD TOC as fallback after API failure",
                    count=len(stale_toc_data),
                )
                cache.set("oecd", TOC_CACHE_KEY, stale_toc_data, ttl_seconds=TOC_TTL_SECONDS)
                return stale_toc_data
            return []

    async def list_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available datasets from OECD.

        Args:
            category: Optional category filter (agency prefix)

        Returns:
            List of dataset metadata
        """
        datasets = await self.fetch_toc()

        if category:
            category_lower = category.lower()
            datasets = [ds for ds in datasets if category_lower in ds.get("category", "").lower()]

        return datasets

    async def list_discoverable_datasets(
        self, session: AsyncSession | None = None
    ) -> list[dict[str, Any]]:
        """List all discoverable datasets from OECD.

        Args:
            session: Optional database session for caching

        Returns:
            List of all available datasets from TOC
        """
        return await self.fetch_toc(session=session)

    async def search_datasets(self, query: str) -> list[dict[str, Any]]:
        """Search for datasets by keyword.

        Uses local filtering over cached TOC.

        Args:
            query: Search query string

        Returns:
            List of matching dataset metadata dictionaries
        """
        query_lower = query.lower()
        toc = await self.fetch_toc()

        results = []
        for ds in toc:
            # Search in name, description, and dataflow ID
            name = (ds.get("name") or "").lower()
            desc = (ds.get("description") or "").lower()
            dataflow_id = (ds.get("dataflow_id") or "").lower()

            if query_lower in name or query_lower in desc or query_lower in dataflow_id:
                results.append(ds)

        logger.info("OECD search completed", query=query, results=len(results))
        return results

    async def get_dataset_metadata(self, dataset_code: str) -> dict[str, Any]:
        """Get metadata for a specific dataset.

        Args:
            dataset_code: Full dataflow code (agencyID,dataflowId,version)

        Returns:
            Dataset metadata including dimensions, attributes, etc.

        Raises:
            ValueError: If dataset_code is invalid
        """
        structure = await self._get_dataflow_structure(dataset_code)
        if not structure:
            raise ValueError(f"Failed to get metadata for dataset: {dataset_code}")

        # Extract relevant metadata
        metadata: dict[str, Any] = {
            "code": dataset_code,
            "metadata_url": None,  # URL generated dynamically by API (SDMX dataflow endpoint)
        }

        # Extract dataflow info
        dataflows = structure.get("data", {}).get("dataflows", [])
        if dataflows:
            df = dataflows[0]
            metadata["name"] = df.get("name")
            metadata["description"] = df.get("description")
            metadata["agency_id"] = df.get("agencyID")
            metadata["version"] = df.get("version")

        # Extract data structure definition
        data_structures = structure.get("data", {}).get("dataStructures", [])
        if data_structures:
            dsd = data_structures[0]
            components = dsd.get("dataStructureComponents", {})

            # Get dimensions
            dims = components.get("dimensionList", {}).get("dimensions", [])
            metadata["dimensions"] = [
                {"id": d.get("id"), "name": d.get("name"), "position": d.get("position")}
                for d in dims
            ]

            # Get attributes
            attrs = components.get("attributeList", {}).get("attributes", [])
            metadata["attributes"] = [{"id": a.get("id"), "name": a.get("name")} for a in attrs]

        return metadata

    async def validate_filters(self, dataset_code: str, filters: dict[str, Any]) -> bool:
        """Validate filters for OECD requests.

        Args:
            dataset_code: Full dataflow code
            filters: Filters to validate

        Returns:
            True if valid (OECD is flexible with dimension values)
        """
        # OECD API validates dimensions itself
        # We just check that values are provided in a reasonable format
        for key, value in filters.items():
            if value is None:
                continue
            if isinstance(value, list):
                if not all(isinstance(v, str) for v in value):
                    logger.warning(f"Invalid filter value for {key}: list items must be strings")
                    return False
            elif not isinstance(value, str):
                logger.warning(f"Invalid filter value for {key}: must be string or list of strings")
                return False

        return True

    async def close(self) -> None:
        """Close the HTTP clients."""
        await self.http_client.close()
        # Only close structure client if it was initialized
        if self._structure_client is not None:
            await self._structure_client.aclose()
            self._structure_client = None
