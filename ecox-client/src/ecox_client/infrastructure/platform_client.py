"""HTTP client for communicating with the ecox-data-platform API.

This client handles all communication with the platform API,
providing typed responses using Pydantic models.
"""

from typing import Any

import httpx
import structlog

from ecox_client.config import settings

logger = structlog.get_logger(__name__)


class PlatformClientError(Exception):
    """Error from the platform API."""

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize the error.

        Args:
            message: Error message
            status_code: HTTP status code if available
        """
        super().__init__(message)
        self.status_code = status_code


class PlatformClient:
    """HTTP client for the ecox-data-platform API.

    Provides methods to access all platform endpoints with
    proper error handling and response typing.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        """Initialize the platform client.

        Args:
            base_url: Platform API base URL
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or settings.platform_url).rstrip("/")
        self.timeout = timeout or settings.platform_timeout

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Accept": "application/json"},
        )

        logger.info("Platform client initialized", base_url=self.base_url)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make an HTTP request to the platform.

        Args:
            method: HTTP method
            path: Request path
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            PlatformClientError: If the request fails
        """
        try:
            response = await self.client.request(method, path, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Platform API error",
                path=path,
                status_code=e.response.status_code,
                detail=e.response.text,
            )
            raise PlatformClientError(
                f"Platform API error: {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            logger.error("Platform connection error", path=path, error=str(e))
            raise PlatformClientError(f"Platform connection error: {e}") from e

    # Health endpoints

    async def health(self) -> dict[str, Any]:
        """Get platform health status.

        Returns:
            Health status dictionary
        """
        return await self._request("GET", "/health")

    # Source endpoints

    async def list_sources(self) -> list[dict[str, Any]]:
        """List all data sources.

        Returns:
            List of source dictionaries
        """
        return await self._request("GET", "/api/sources")

    async def get_source_status(self, source: str) -> dict[str, Any]:
        """Get detailed status for a source.

        Args:
            source: Source code

        Returns:
            Source status dictionary
        """
        return await self._request("GET", f"/api/sources/{source}")

    # Dataset endpoints

    async def list_datasets(
        self,
        source: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List datasets with optional filtering.

        Args:
            source: Filter by source
            search: Search term
            page: Page number
            page_size: Items per page

        Returns:
            Paginated dataset list
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if source:
            params["source"] = source
        if search:
            params["search"] = search

        return await self._request("GET", "/api/datasets", params=params)

    async def list_all_datasets(
        self,
        source: str | None = None,
        since_id: int | None = None,
    ) -> dict[str, Any]:
        """Get all datasets or incremental updates for client-side pagination.

        Args:
            source: Optional filter by source
            since_id: Only return datasets with id > since_id (for incremental sync)

        Returns:
            DatasetSyncResponse dict with items and max_id
        """
        params: dict[str, Any] = {}
        if source:
            params["source"] = source
        if since_id is not None:
            params["since_id"] = since_id

        return await self._request("GET", "/api/datasets/all", params=params)

    async def get_dataset(self, source: str, code: str) -> dict[str, Any]:
        """Get dataset details.

        Args:
            source: Source code
            code: Dataset code

        Returns:
            Dataset details
        """
        return await self._request("GET", f"/api/datasets/{source}/{code}")

    async def get_dataset_values(
        self,
        source: str,
        code: str,
        geo: str | None = None,
        time_period: str | None = None,
        indicator: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Get dataset values with optional filtering.

        Args:
            source: Source code
            code: Dataset code
            geo: Filter by geography
            time_period: Filter by time period
            indicator: Filter by indicator
            page: Page number
            page_size: Items per page

        Returns:
            Paginated data values
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if geo:
            params["geo"] = geo
        if time_period:
            params["time_period"] = time_period
        if indicator:
            params["indicator"] = indicator

        return await self._request("GET", f"/api/datasets/{source}/{code}/values", params=params)

    async def get_dimension_values(
        self,
        source: str,
        code: str,
        dimension: str,
    ) -> dict[str, Any]:
        """Get unique values for a dimension.

        Args:
            source: Source code
            code: Dataset code
            dimension: Dimension name (geo, time_period, indicator)

        Returns:
            Dictionary with dimension values
        """
        return await self._request("GET", f"/api/datasets/{source}/{code}/dimensions/{dimension}")

    # Fetch log endpoints

    async def list_fetch_logs(
        self,
        source: str | None = None,
        dataset_code: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """List fetch logs with optional filtering.

        Args:
            source: Filter by source
            dataset_code: Filter by dataset code
            status: Filter by status
            page: Page number
            page_size: Items per page

        Returns:
            Paginated fetch log list
        """
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if source:
            params["source"] = source
        if dataset_code:
            params["dataset_code"] = dataset_code
        if status:
            params["status"] = status

        return await self._request("GET", "/api/fetch-logs", params=params)

    async def get_fetch_summary(self, hours: int = 24) -> dict[str, Any]:
        """Get fetch operation summary.

        Args:
            hours: Hours to look back

        Returns:
            Fetch summary statistics
        """
        return await self._request("GET", "/api/fetch-logs/summary", params={"hours": hours})

    # News endpoints (hierarchical: Category → Source → Section → Entry)

    async def list_news_categories(self) -> list[dict[str, Any]]:
        """List news categories with sources, sections, and entry counts.

        Returns hierarchical structure:
        - Category contains sources
        - Source contains sections
        - Section has entry counts and fetch status

        Returns:
            List of category dictionaries with nested sources and sections
        """
        return await self._request("GET", "/api/news/categories")

    async def list_news_entries(
        self,
        section_id: int | None = None,
        source_id: int | None = None,
        category_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List news entries with optional filtering.

        Args:
            section_id: Filter by section ID
            source_id: Filter by source ID
            category_id: Filter by category ID
            limit: Max entries to return
            offset: Pagination offset

        Returns:
            Dictionary with entries list and pagination info
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if section_id is not None:
            params["section_id"] = section_id
        if source_id is not None:
            params["source_id"] = source_id
        if category_id is not None:
            params["category_id"] = category_id

        return await self._request("GET", "/api/news/entries", params=params)

    async def list_section_entries(
        self,
        section_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List entries for a specific section (for htmx lazy-loading).

        Args:
            section_id: Section ID
            limit: Max entries to return
            offset: Pagination offset

        Returns:
            Dictionary with entries list and pagination info
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        return await self._request("GET", f"/api/news/sections/{section_id}/entries", params=params)

    async def get_entry(self, entry_id: int) -> dict[str, Any]:
        """Get full entry details including content (US-5.12).

        Args:
            entry_id: Entry ID

        Returns:
            Entry dictionary with content_full
        """
        return await self._request("GET", f"/api/news/entries/{entry_id}")

    async def refresh_section(self, section_id: int) -> dict[str, Any]:
        """Manually refresh a section (US-5.13).

        Args:
            section_id: Section ID to refresh

        Returns:
            Fetch result dictionary
        """
        return await self._request("POST", f"/api/news/sections/{section_id}/refresh")

    async def get_news_status(self) -> dict[str, Any]:
        """Get news worker status.

        Returns:
            News worker status dictionary
        """
        return await self._request("GET", "/api/news/status")

    async def get_news_feed(
        self,
        category_id: int | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get chronological news feed (US-5.14).

        Args:
            category_id: Optional category filter
            search: Optional search term
            limit: Max entries to return
            offset: Pagination offset

        Returns:
            Feed response with entries and has_more indicator
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if category_id is not None:
            params["category_id"] = category_id
        if search:
            params["search"] = search

        return await self._request("GET", "/api/news/entries/feed", params=params)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("Platform client closed")


# Global client instance
_client: PlatformClient | None = None


def get_platform_client() -> PlatformClient:
    """Get the global platform client instance.

    Returns:
        PlatformClient instance
    """
    global _client
    if _client is None:
        _client = PlatformClient()
    return _client


async def close_platform_client() -> None:
    """Close the global platform client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
