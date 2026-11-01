"""Eurostat repository implementation.

This module implements the repository pattern for fetching data from
the Eurostat REST API.
"""

import json
from datetime import datetime, timedelta
from typing import Any

import structlog
from ecox_shared.models import SourceMetadata
from ecox_shared.utils import ResilientHttpClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.infrastructure.cache import get_cache
from ecox_platform.sources.base.repository import BaseRepository

logger = structlog.get_logger(__name__)

# Eurostat API base URL
EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
EUROSTAT_TOC_URL = "https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/xml"

# Cache key constants
TOC_CACHE_KEY = "__toc__"
TOC_TTL_SECONDS = 6 * 3600  # 6 hours


class EurostatRepository(BaseRepository):
    """Repository for fetching data from Eurostat REST API.

    Implements the BaseRepository interface for Eurostat-specific operations.
    """

    def __init__(
        self,
        http_client: ResilientHttpClient | None = None,
        rate_limit: float = 2.0,
    ) -> None:
        """Initialize the Eurostat repository.

        Args:
            http_client: Optional HTTP client (creates new one if not provided)
            rate_limit: Rate limit in requests per second
        """
        self.http_client = http_client or ResilientHttpClient(
            base_url=EUROSTAT_BASE_URL,
            rate_limit=rate_limit,
        )
        logger.info("Eurostat repository initialized")

    async def get_dataset(
        self, dataset_code: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch a specific dataset from Eurostat API.

        Args:
            dataset_code: Dataset identifier (e.g., "nama_10_gdp")
            filters: Optional filters to apply

        Returns:
            Dataset data in JSON-stat 2.0 format

        Raises:
            ValueError: If dataset_code is invalid
            httpx.HTTPStatusError: If the API request fails
        """
        params: dict[str, Any] = {
            "lang": "EN",
            "format": "JSON",
        }

        if filters:
            if "geo" in filters and "geoLevel" in filters:
                raise ValueError("Cannot use both 'geo' and 'geoLevel' filters")
            params.update(filters)

        logger.info(
            "Fetching dataset from Eurostat",
            dataset_code=dataset_code,
            filters=filters,
        )

        try:
            data = await self.http_client.get(dataset_code, params=params)

            logger.info(
                "Dataset fetched successfully",
                dataset_code=dataset_code,
                version=data.get("version"),
            )

            return data

        except Exception as e:
            logger.error(
                "Failed to fetch dataset",
                dataset_code=dataset_code,
                error=str(e),
            )
            raise

    async def fetch_toc(
        self, session: AsyncSession | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch and parse the Eurostat Table of Contents (TOC).

        Args:
            session: Optional DB session for caching
            force_refresh: If True, bypass caches and fetch from API

        Returns:
            List of dataset metadata dictionaries parsed from XML TOC
        """
        cache = get_cache()

        # 1. Check memory cache first
        if not force_refresh:
            cached_toc = cache.get("eurostat", TOC_CACHE_KEY)
            if cached_toc is not None:
                logger.debug("Returning cached Eurostat TOC (memory)", count=len(cached_toc))
                return list(cached_toc)

        # 2. Check DB cache if session provided
        if not force_refresh and session:
            try:
                statement = select(SourceMetadata).where(SourceMetadata.source == "eurostat")
                result = await session.exec(statement)
                metadata = result.one_or_none()

                if metadata and metadata.cached_toc:
                    try:
                        toc_data: list[dict[str, Any]] = json.loads(metadata.cached_toc)
                        age = datetime.now() - metadata.last_updated

                        if age < timedelta(hours=24):
                            logger.info(
                                "Returning cached Eurostat TOC (DB)",
                                count=len(toc_data),
                                age_hours=age.total_seconds() / 3600,
                            )
                            cache.set(
                                "eurostat", TOC_CACHE_KEY, toc_data, ttl_seconds=TOC_TTL_SECONDS
                            )
                            return toc_data
                    except json.JSONDecodeError:
                        logger.warning("Failed to decode cached TOC from DB")
            except Exception as e:
                logger.warning("Failed to check DB cache for TOC", error=str(e))

        # 3. Fetch from API
        try:
            import defusedxml.ElementTree as ET

            logger.info("Fetching Eurostat Table of Contents", url=EUROSTAT_TOC_URL)
            response = await self.http_client.client.get(EUROSTAT_TOC_URL)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            datasets = []
            ns = {"nt": "urn:eu.europa.ec.eurostat.navtree"}

            for leaf in root.findall(".//nt:leaf", ns):
                if leaf.get("type") in ["dataset", "table"]:
                    code = leaf.findtext("nt:code", namespaces=ns)
                    title = leaf.findtext("nt:title[@language='en']", namespaces=ns)
                    last_update = leaf.findtext("nt:lastUpdate", namespaces=ns)
                    data_start = leaf.findtext("nt:dataStart", namespaces=ns)
                    data_end = leaf.findtext("nt:dataEnd", namespaces=ns)
                    values_str = leaf.findtext("nt:values", namespaces=ns)
                    values_count = int(values_str) if values_str and values_str.isdigit() else 0

                    if code and title:
                        code_stripped = code.strip()
                        datasets.append(
                            {
                                "code": code_stripped,
                                "name": title.strip(),
                                "description": title.strip(),
                                "category": "eurostat_toc",
                                "last_update": last_update,
                                "data_start": data_start,
                                "data_end": data_end,
                                "values_count": values_count,
                                "type": leaf.get("type"),
                                "metadata_url": f"https://ec.europa.eu/eurostat/databrowser/view/{code_stripped}/default/table",
                            }
                        )

            # Deduplicate by code - same dataset appears in multiple TOC categories
            # Keep entry with most recent last_update for accurate smart refresh
            original_count = len(datasets)
            seen_codes: dict[str, dict[str, Any]] = {}
            for ds in datasets:
                ds_code = str(ds["code"])
                if ds_code not in seen_codes:
                    seen_codes[ds_code] = ds
                else:
                    # Keep the one with more recent last_update
                    existing_update = str(seen_codes[ds_code].get("last_update") or "")
                    new_update = str(ds.get("last_update") or "")
                    if new_update > existing_update:
                        seen_codes[ds_code] = ds

            datasets = list(seen_codes.values())
            duplicates_removed = original_count - len(datasets)

            logger.info(
                "Parsed Eurostat TOC",
                original_count=original_count,
                unique_count=len(datasets),
                duplicates_removed=duplicates_removed,
            )

            cache.set("eurostat", TOC_CACHE_KEY, datasets, ttl_seconds=TOC_TTL_SECONDS)

            # Update DB cache if session provided
            if session:
                try:
                    statement = select(SourceMetadata).where(SourceMetadata.source == "eurostat")
                    result = await session.exec(statement)
                    metadata = result.one_or_none()

                    if not metadata:
                        metadata = SourceMetadata(source="eurostat")
                        session.add(metadata)

                    metadata.total_datasets = len(datasets)
                    metadata.cached_toc = json.dumps(datasets)
                    metadata.last_updated = datetime.now()

                    await session.commit()
                    logger.info("Updated Eurostat TOC in DB cache")
                except Exception as e:
                    logger.error("Failed to update DB cache for TOC", error=str(e))

            return datasets

        except Exception as e:
            logger.error("Failed to fetch/parse Eurostat TOC", error=str(e))
            return []

    async def list_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available datasets from Eurostat.

        Args:
            category: Optional category filter

        Returns:
            List of dataset metadata dictionaries
        """
        try:
            datasets = await self.fetch_toc()
        except Exception:
            datasets = []

        if category:
            datasets = [
                d
                for d in datasets
                if d.get("category") == category or category in d.get("category", "")
            ]

        logger.info("Listed datasets", category=category, count=len(datasets))
        return datasets

    async def list_discoverable_datasets(self, session: Any | None = None) -> list[dict[str, Any]]:
        """List all discoverable datasets from Eurostat.

        Args:
            session: Optional database session for caching

        Returns:
            List of all available datasets from TOC
        """
        return await self.fetch_toc(session=session)

    async def search_datasets(self, query: str) -> list[dict[str, Any]]:
        """Search for datasets by keyword.

        Args:
            query: Search query string

        Returns:
            List of matching dataset metadata dictionaries
        """
        all_datasets = await self.list_datasets()

        query_lower = query.lower()
        matching_datasets = [
            dataset
            for dataset in all_datasets
            if query_lower in dataset.get("name", "").lower()
            or query_lower in dataset.get("description", "").lower()
            or query_lower in dataset.get("code", "").lower()
        ]

        logger.info("Searched datasets", query=query, matches=len(matching_datasets))
        return matching_datasets

    async def get_dataset_metadata(self, dataset_code: str) -> dict[str, Any]:
        """Get metadata for a specific dataset.

        Args:
            dataset_code: Dataset identifier

        Returns:
            Dataset metadata

        Raises:
            ValueError: If dataset_code is invalid
        """
        toc = await self.fetch_toc()

        for dataset in toc:
            if dataset["code"] == dataset_code:
                return dataset

        raise ValueError(f"Unknown dataset: {dataset_code}")

    async def validate_filters(self, dataset_code: str, filters: dict[str, Any]) -> bool:
        """Validate that filters are valid for a dataset.

        Args:
            dataset_code: Dataset identifier
            filters: Filters to validate

        Returns:
            True if filters are valid, False otherwise
        """
        if "geo" in filters and "geoLevel" in filters:
            logger.warning(
                "Invalid filters: both 'geo' and 'geoLevel' specified",
                dataset_code=dataset_code,
            )
            return False
        return True

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.close()
