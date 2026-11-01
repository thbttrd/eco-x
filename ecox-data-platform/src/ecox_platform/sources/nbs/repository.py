"""NBS China repository implementation.

This module implements the repository pattern for fetching data from
China's National Bureau of Statistics (NBS) API.

API Documentation (unofficial - reverse-engineered):
- Base URL: https://data.stats.gov.cn/english/easyquery.htm
- Database codes: hgnd (annual), hgyd (monthly), fsnd (regional annual)
- No authentication required
- Rate limit: undocumented, use conservative 2 req/s
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
import structlog
from ecox_shared.models import SourceMetadata
from ecox_shared.utils import ResilientHttpClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.config import settings
from ecox_platform.infrastructure.cache import get_cache
from ecox_platform.sources.base.repository import BaseRepository

logger = structlog.get_logger(__name__)

# NBS API base URL
NBS_BASE_URL = "https://data.stats.gov.cn/english"

# Cache key constants
TOC_CACHE_KEY = "__toc__"
TOC_TTL_SECONDS = 6 * 3600  # 6 hours

# Database codes for different data frequencies
DB_CODES = {
    "annual": "hgnd",
    "monthly": "hgyd",
    "quarterly": "hgjd",
    "regional_annual": "fsnd",
    "regional_monthly": "fsyd",
}


class NbsRepository(BaseRepository):
    """Repository for fetching data from NBS China API.

    Implements the BaseRepository interface for NBS-specific operations.
    The NBS API uses a hierarchical tree structure for dataset discovery
    rather than a flat list like other sources.
    """

    def __init__(
        self,
        http_client: ResilientHttpClient | None = None,
        rate_limit: float | None = None,
        dbcode: str = "hgnd",
    ) -> None:
        """Initialize the NBS repository.

        Args:
            http_client: Optional HTTP client (creates new one if not provided)
            rate_limit: Rate limit in requests per second (uses settings if not provided)
            dbcode: Database code to use (default: hgnd for annual data)
        """
        effective_rate_limit = rate_limit or settings.nbs_rate_limit
        self.http_client = http_client or ResilientHttpClient(
            base_url=NBS_BASE_URL,
            rate_limit=effective_rate_limit,
        )
        self.dbcode = dbcode
        self._cache = get_cache()
        self._rate_limit = effective_rate_limit
        self._tree_client: httpx.AsyncClient | None = None
        self._tree_client_lock = asyncio.Lock()  # Prevent race condition
        self._last_tree_request: float = 0.0

        logger.info(
            "NBS repository initialized",
            dbcode=dbcode,
            rate_limit=effective_rate_limit,
        )

    async def _get_tree_client(self) -> httpx.AsyncClient:
        """Get or create a reusable httpx client for tree requests.

        Note: Uses a separate httpx.AsyncClient (not ResilientHttpClient) because
        the NBS tree endpoint returns a list, not a dict, and ResilientHttpClient
        only accepts dict responses.

        Uses asyncio.Lock to prevent race conditions when multiple coroutines
        try to create the client simultaneously.
        """
        async with self._tree_client_lock:
            if self._tree_client is None or self._tree_client.is_closed:
                # Enable redirect following - NBS API sometimes returns 302 redirects
                # Add browser-like headers to avoid bot detection
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://data.stats.gov.cn/english/easyquery.htm",
                }
                self._tree_client = httpx.AsyncClient(
                    timeout=30.0,
                    follow_redirects=True,
                    headers=headers,
                )
        return self._tree_client

    async def _rate_limit_tree_request(self) -> None:
        """Enforce rate limiting for tree requests.

        Uses a more conservative rate (1 req/s) for tree traversal to avoid
        triggering NBS's anti-bot protection.
        """
        now = time.monotonic()
        # Force 1 req/s for tree traversal (more conservative than general rate limit)
        min_interval = 1.0  # 1 second between requests
        elapsed = now - self._last_tree_request

        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)

        self._last_tree_request = time.monotonic()

    async def _fetch_tree(self, parent_id: str = "zb") -> list[dict[str, Any]]:
        """Fetch tree nodes from the NBS API.

        Note: Uses httpx directly because the NBS tree endpoint returns a list,
        not a dict, and ResilientHttpClient.get() only accepts dict responses.

        Args:
            parent_id: Parent node ID to fetch children for (default: root)

        Returns:
            List of tree node dictionaries
        """
        params = {
            "m": "getTree",
            "dbcode": self.dbcode,
            "wdcode": "zb",
            "id": parent_id,
        }

        max_retries = 3
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                await self._rate_limit_tree_request()

                # Reuse httpx client for efficiency
                client = await self._get_tree_client()
                url = f"{NBS_BASE_URL}/easyquery.htm"
                response = await client.get(url, params=params)
                response.raise_for_status()

                # Check for empty response (rate limiting symptom)
                if not response.text or not response.text.strip():
                    logger.warning(
                        "NBS returned empty response, retrying",
                        parent_id=parent_id,
                        attempt=attempt + 1,
                    )
                    await asyncio.sleep(2.0)  # Extra backoff
                    continue

                try:
                    data = response.json()
                except Exception as json_err:
                    logger.warning(
                        "NBS returned non-JSON response, retrying",
                        parent_id=parent_id,
                        attempt=attempt + 1,
                        response_preview=response.text[:200] if response.text else "empty",
                        error=str(json_err),
                    )
                    await asyncio.sleep(2.0)  # Extra backoff
                    continue

                # Response is a list of tree nodes
                if isinstance(data, list):
                    return data
                return []

            except (TimeoutError, httpx.HTTPError) as e:
                # Retry on network/HTTP errors
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(
                        "NBS tree request failed, retrying",
                        parent_id=parent_id,
                        attempt=attempt + 1,
                        error_type=type(e).__name__,
                    )
                    await asyncio.sleep(2.0)  # Extra backoff
                    continue

        # All retries exhausted
        logger.error(
            "Failed to fetch NBS tree after retries",
            parent_id=parent_id,
            error_type=type(last_error).__name__ if last_error else "Unknown",
            error_msg=str(last_error) if last_error else "Unknown",
        )
        raise last_error or RuntimeError("Failed to fetch NBS tree")

    async def _fetch_all_leaf_nodes(self, max_depth: int = 3) -> list[dict[str, Any]]:
        """Recursively fetch all leaf nodes (actual datasets) from the tree.

        Args:
            max_depth: Maximum depth to traverse

        Returns:
            List of leaf node metadata dictionaries
        """
        all_leaves: list[dict[str, Any]] = []
        visited: set[str] = set()

        async def traverse(node_id: str, depth: int) -> None:
            if depth > max_depth or node_id in visited:
                return

            visited.add(node_id)
            children = await self._fetch_tree(node_id)

            for child in children:
                child_id = child.get("id", "")
                is_parent = child.get("isParent", False)

                if is_parent:
                    # Recurse into parent nodes
                    await traverse(child_id, depth + 1)
                else:
                    # Leaf node - this is a dataset
                    # Note: NBS doesn't have reliable browser URLs for datasets
                    # UI shows message instead - see generate_source_url() in datasets.py
                    all_leaves.append(
                        {
                            "code": child_id,
                            "name": child.get("name", child_id),
                            "category": child.get("pid", ""),
                            "dbcode": child.get("dbcode", self.dbcode),
                        }
                    )

        # Start from root
        await traverse("zb", 0)

        logger.info("Fetched all NBS leaf nodes", count=len(all_leaves))
        return all_leaves

    async def fetch_toc(
        self, session: AsyncSession | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch and parse the NBS Table of Contents (TOC).

        The TOC is built by traversing the indicator tree and collecting
        all leaf nodes (actual datasets).

        Args:
            session: Optional DB session for caching
            force_refresh: If True, bypass caches and fetch from API

        Returns:
            List of dataset metadata dictionaries
        """
        # 1. Check memory cache first (fastest) - unless forced
        if not force_refresh:
            cached_toc = self._cache.get("nbs", TOC_CACHE_KEY)
            if cached_toc is not None:
                logger.debug("Returning cached NBS TOC (memory)", count=len(cached_toc))
                return list(cached_toc)

        # 2. Check DB cache if session provided - unless forced
        if not force_refresh and session:
            try:
                statement = select(SourceMetadata).where(SourceMetadata.source == "nbs")
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
                                "Returning cached NBS TOC (DB)",
                                count=len(toc_data),
                                age_hours=age.total_seconds() / 3600,
                            )
                            self._cache.set(
                                "nbs", TOC_CACHE_KEY, toc_data, ttl_seconds=TOC_TTL_SECONDS
                            )
                            return toc_data
                        else:
                            # Stale-while-revalidate: try refresh, fallback to stale
                            logger.info(
                                "DB cache is stale, attempting refresh",
                                age_hours=age.total_seconds() / 3600,
                            )
                            stale_fallback = toc_data  # Save for fallback
                            try:
                                fresh_datasets = await self._fetch_all_leaf_nodes()
                                logger.info(
                                    "Refreshed NBS TOC successfully",
                                    count=len(fresh_datasets),
                                )
                                # Update caches
                                self._cache.set(
                                    "nbs",
                                    TOC_CACHE_KEY,
                                    fresh_datasets,
                                    ttl_seconds=TOC_TTL_SECONDS,
                                )
                                # Update DB cache
                                metadata.total_datasets = len(fresh_datasets)
                                metadata.cached_toc = json.dumps(fresh_datasets)
                                metadata.last_updated = datetime.now()
                                await session.commit()
                                return fresh_datasets
                            except Exception as refresh_error:
                                logger.warning(
                                    "Failed to refresh stale TOC, using stale data",
                                    error=str(refresh_error),
                                    stale_age_hours=age.total_seconds() / 3600,
                                )
                                self._cache.set(
                                    "nbs",
                                    TOC_CACHE_KEY,
                                    stale_fallback,
                                    ttl_seconds=TOC_TTL_SECONDS,
                                )
                                return stale_fallback

                    except json.JSONDecodeError:
                        logger.warning("Failed to decode cached TOC from DB")
            except Exception as e:
                logger.warning("Failed to check DB cache for TOC", error=str(e))

        # 3. Fetch from API (slowest)
        try:
            logger.info("Fetching NBS Table of Contents (tree traversal)")

            datasets = await self._fetch_all_leaf_nodes()

            logger.info("Parsed NBS TOC", dataset_count=len(datasets))

            # Update memory cache
            self._cache.set("nbs", TOC_CACHE_KEY, datasets, ttl_seconds=TOC_TTL_SECONDS)

            # Update DB cache if session provided
            if session:
                try:
                    statement = select(SourceMetadata).where(SourceMetadata.source == "nbs")
                    result = await session.exec(statement)
                    metadata = result.one_or_none()

                    if not metadata:
                        metadata = SourceMetadata(source="nbs")
                        session.add(metadata)

                    metadata.total_datasets = len(datasets)
                    metadata.cached_toc = json.dumps(datasets)
                    metadata.last_updated = datetime.now()

                    await session.commit()
                    logger.info("Updated NBS TOC in DB cache")
                except Exception as e:
                    logger.error("Failed to update DB cache for TOC", error=str(e))

            return datasets

        except Exception as e:
            logger.error(
                "Failed to fetch/parse NBS TOC",
                error_type=type(e).__name__,
                error_msg=str(e) or repr(e),
            )
            return []

    async def get_dataset(
        self, dataset_code: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch a specific dataset from NBS API.

        Args:
            dataset_code: Dataset/indicator code (e.g., "A0201" for GDP)
            filters: Optional filters (time range, etc.)

        Returns:
            Dictionary containing data observations and metadata

        Raises:
            ValueError: If dataset_code is invalid
        """
        # Build the dfwds (dimension filter) parameter
        dfwds = [{"wdcode": "zb", "valuecode": dataset_code}]

        params = {
            "m": "QueryData",
            "dbcode": self.dbcode,
            "rowcode": "zb",
            "colcode": "sj",
            "wds": "[]",
            "dfwds": json.dumps(dfwds),
        }

        logger.info(
            "Fetching dataset from NBS",
            dataset_code=dataset_code,
            dbcode=self.dbcode,
        )

        try:
            data = await self.http_client.get("easyquery.htm", params=params)

            # Validate response status
            returncode = data.get("returncode", 0)
            if returncode != 200:
                raise ValueError(f"NBS API error: returncode={returncode}")

            return data

        except Exception as e:
            logger.error(
                "Failed to fetch NBS dataset",
                dataset_code=dataset_code,
                error=str(e),
            )
            raise

    async def list_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available datasets from NBS.

        Args:
            category: Optional category filter (parent node ID)

        Returns:
            List of dataset metadata
        """
        if category:
            # List children of specific category
            children = await self._fetch_tree(category)
            return [
                {
                    "code": c.get("id"),
                    "name": c.get("name"),
                    "category": c.get("pid", ""),
                    "is_parent": c.get("isParent", False),
                }
                for c in children
            ]
        else:
            # Return full TOC
            return await self.fetch_toc()

    async def list_discoverable_datasets(
        self, session: AsyncSession | None = None
    ) -> list[dict[str, Any]]:
        """List all discoverable datasets from NBS.

        Args:
            session: Optional database session for caching

        Returns:
            List of all available datasets from TOC
        """
        return await self.fetch_toc(session=session)

    async def search_datasets(self, query: str) -> list[dict[str, Any]]:
        """Search for datasets by keyword.

        NBS doesn't have a search endpoint, so we search the cached TOC.
        Searches code (case-insensitive), English name (case-insensitive),
        and Chinese name (exact substring match since Chinese has no case).

        Args:
            query: Search query string

        Returns:
            List of matching dataset metadata
        """
        toc = await self.fetch_toc()
        query_lower = query.lower()

        results = []
        for dataset in toc:
            code = dataset.get("code", "").lower()
            name = dataset.get("name", "").lower()
            cname = dataset.get("cname", "")  # Chinese name (no case conversion)

            # Match code or English name (case-insensitive)
            if query_lower in code or query_lower in name:
                results.append(dataset)
            # Match Chinese name (exact substring, no case conversion)
            elif query in cname:
                results.append(dataset)

        logger.info("NBS dataset search", query=query, results=len(results))
        return results[:50]  # Limit results

    async def get_dataset_metadata(self, dataset_code: str) -> dict[str, Any]:
        """Get metadata for a specific dataset.

        Fetches data to extract indicator metadata from wdnodes.

        Args:
            dataset_code: Dataset identifier

        Returns:
            Dataset metadata including name, description, unit
        """
        # Fetch data to get wdnodes metadata
        data = await self.get_dataset(dataset_code)

        returndata = data.get("returndata", {})
        wdnodes = returndata.get("wdnodes", [])

        # Find indicator metadata
        metadata: dict[str, Any] = {
            "code": dataset_code,
            "name": dataset_code,
            "description": None,
            "unit": None,
        }

        for wdnode in wdnodes:
            if wdnode.get("wdcode") == "zb":  # Indicator dimension
                for node in wdnode.get("nodes", []):
                    if node.get("code") == dataset_code:
                        metadata["name"] = node.get("name", dataset_code)
                        metadata["description"] = node.get("exp") or None
                        metadata["unit"] = node.get("unit") or None
                        break

        return metadata

    async def validate_filters(self, dataset_code: str, filters: dict[str, Any]) -> bool:
        """Validate filters for NBS requests.

        Args:
            dataset_code: Dataset identifier
            filters: Filters to validate

        Returns:
            True if all filters are valid, False otherwise
        """
        valid_params = {
            "time_start",
            "time_end",
            "dbcode",
        }

        for key in filters:
            if key not in valid_params:
                logger.warning(f"Unknown filter parameter for NBS: {key}")
                return False

        return True

    async def close(self) -> None:
        """Close all HTTP clients."""
        await self.http_client.close()
        if self._tree_client is not None and not self._tree_client.is_closed:
            await self._tree_client.aclose()
