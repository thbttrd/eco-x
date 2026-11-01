"""Abstract repository interface for data sources.

This module defines the contract that all data source repositories must implement.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    """Abstract base class for data source repositories.

    All data source implementations (Eurostat, OECD, FRED, etc.)
    must implement these methods.
    """

    @abstractmethod
    async def get_dataset(
        self, dataset_code: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch a specific dataset from the data source.

        Args:
            dataset_code: Dataset identifier (e.g., "nama_10_gdp")
            filters: Optional filters to apply (geo, time, etc.)

        Returns:
            Dataset data as dictionary

        Raises:
            ValueError: If dataset_code is invalid
            ConnectionError: If the API is unreachable
            RuntimeError: For other errors
        """
        pass

    @abstractmethod
    async def list_datasets(self, category: str | None = None) -> list[dict[str, Any]]:
        """List available datasets from the data source.

        Args:
            category: Optional category filter (e.g., "economy", "environment")

        Returns:
            List of dataset metadata dictionaries

        Raises:
            ConnectionError: If the API is unreachable
        """
        pass

    @abstractmethod
    async def search_datasets(self, query: str) -> list[dict[str, Any]]:
        """Search for datasets by keyword.

        Args:
            query: Search query string

        Returns:
            List of matching dataset metadata dictionaries

        Raises:
            ConnectionError: If the API is unreachable
        """
        pass

    @abstractmethod
    async def get_dataset_metadata(self, dataset_code: str) -> dict[str, Any]:
        """Get metadata for a specific dataset.

        Args:
            dataset_code: Dataset identifier

        Returns:
            Dataset metadata including dimensions, attributes, etc.

        Raises:
            ValueError: If dataset_code is invalid
            ConnectionError: If the API is unreachable
        """
        pass

    @abstractmethod
    async def validate_filters(self, dataset_code: str, filters: dict[str, Any]) -> bool:
        """Validate that filters are valid for a dataset.

        Args:
            dataset_code: Dataset identifier
            filters: Filters to validate

        Returns:
            True if filters are valid, False otherwise
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close any open resources (HTTP client, etc.).

        Should be called when the repository is no longer needed.
        """
        pass

    async def list_discoverable_datasets(self, session: Any | None = None) -> list[dict[str, Any]]:
        """List all discoverable datasets from the source.

        This method returns datasets that can be discovered and fetched.
        Default implementation calls list_datasets with no filter.

        Args:
            session: Optional database session for caching

        Returns:
            List of discoverable dataset metadata
        """
        return await self.list_datasets(category=None)
