"""Unit tests for ONS service.

Tests cover:
- Observation transformation to common format
- Dimension handling (geography, time, extra dimensions)
- Invalid value filtering
- Service delegation to repository
- Caching behavior
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ecox_platform.infrastructure.cache import Cache
from ecox_platform.sources.ons.service import OnsService


@pytest.fixture
def mock_ons_repository() -> MagicMock:
    """Create a mock ONS repository."""
    repo = MagicMock()
    repo.get_dataset = AsyncMock()
    repo.get_dataset_metadata = AsyncMock()
    repo.list_datasets = AsyncMock()
    repo.search_datasets = AsyncMock()
    repo.close = AsyncMock()
    return repo


@pytest.fixture
def test_cache() -> Cache:
    """Create a test cache instance."""
    return Cache(ttl_seconds=60)


@pytest.fixture
def ons_service(mock_ons_repository: MagicMock, test_cache: Cache) -> OnsService:
    """Create ONS service with mocked repository."""
    service = OnsService(repository=mock_ons_repository, cache=test_cache)
    return service


class TestTransformObservations:
    """Tests for _transform_observations method."""

    def test_transform_basic_observations(
        self,
        ons_service: OnsService,
        ons_observations_basic: list[dict],
        ons_metadata_with_unit: dict,
        ons_raw_data_empty_dimensions: dict,
    ) -> None:
        """Test transforming basic ONS observations to common format."""
        result = ons_service._transform_observations(
            observations=ons_observations_basic,
            filters=None,
            metadata=ons_metadata_with_unit,
            dataset_code="trade",
            raw_data=ons_raw_data_empty_dimensions,
        )

        assert len(result) == 2
        assert result[0]["geo"] == "K02000001"
        assert result[0]["time_period"] == "2023-Q1"
        assert result[0]["value"] == 12345.6
        assert result[0]["unit"] == "GBP millions"

    def test_transform_with_additional_dimensions(
        self,
        ons_service: OnsService,
        ons_observations_with_extra_dimensions: list[dict],
        ons_metadata_empty: dict,
        ons_raw_data_empty_dimensions: dict,
    ) -> None:
        """Test transforming observations with non-time/geo dimensions."""
        result = ons_service._transform_observations(
            observations=ons_observations_with_extra_dimensions,
            filters=None,
            metadata=ons_metadata_empty,
            dataset_code="industry-stats",
            raw_data=ons_raw_data_empty_dimensions,
        )

        # Indicator should include the additional dimension
        assert len(result) == 2
        assert "A" in result[0]["indicator"]
        assert "industry-stats" in result[0]["indicator"]
        assert "B" in result[1]["indicator"]

    def test_transform_with_fixed_dimensions(
        self,
        ons_service: OnsService,
        ons_metadata_empty: dict,
        ons_raw_data_with_fixed_dimensions: dict,
    ) -> None:
        """Test transforming observations with fixed dimensions from response."""
        observations = [
            {
                "observation": "50.0",
                "dimensions": {
                    "time": {"id": "2023", "label": "2023"},
                },
            },
        ]

        result = ons_service._transform_observations(
            observations=observations,
            filters=None,
            metadata=ons_metadata_empty,
            dataset_code="sector-data",
            raw_data=ons_raw_data_with_fixed_dimensions,
        )

        assert len(result) == 1
        # Geography should come from fixed dimensions
        assert result[0]["geo"] == "K02000001"
        # Indicator should include fixed dimension value
        assert "total" in result[0]["indicator"]

    def test_transform_skips_invalid_values(
        self,
        ons_service: OnsService,
        ons_observations_with_invalid_values: list[dict],
        ons_metadata_empty: dict,
        ons_raw_data_empty_dimensions: dict,
    ) -> None:
        """Test that invalid observation values are skipped."""
        result = ons_service._transform_observations(
            observations=ons_observations_with_invalid_values,
            filters=None,
            metadata=ons_metadata_empty,
            dataset_code="test",
            raw_data=ons_raw_data_empty_dimensions,
        )

        # Only 2 valid values (12345.6 and 98765.4)
        assert len(result) == 2
        assert result[0]["value"] == 12345.6
        assert result[1]["value"] == 98765.4

    def test_transform_with_capital_time_key(
        self,
        ons_service: OnsService,
        ons_observations_capital_time_key: list[dict],
        ons_metadata_empty: dict,
        ons_raw_data_empty_dimensions: dict,
    ) -> None:
        """Test handling of 'Time' vs 'time' dimension key."""
        result = ons_service._transform_observations(
            observations=ons_observations_capital_time_key,
            filters=None,
            metadata=ons_metadata_empty,
            dataset_code="test",
            raw_data=ons_raw_data_empty_dimensions,
        )

        assert len(result) == 1
        assert result[0]["time_period"] == "2023"

    def test_transform_uses_label_as_fallback_for_time(
        self,
        ons_service: OnsService,
        ons_observations_label_only_time: list[dict],
        ons_metadata_empty: dict,
        ons_raw_data_empty_dimensions: dict,
    ) -> None:
        """Test using label when id is not available for time."""
        result = ons_service._transform_observations(
            observations=ons_observations_label_only_time,
            filters=None,
            metadata=ons_metadata_empty,
            dataset_code="test",
            raw_data=ons_raw_data_empty_dimensions,
        )

        assert len(result) == 1
        assert result[0]["time_period"] == "2023 Q1"

    def test_transform_default_geography(
        self,
        ons_service: OnsService,
        ons_observations_no_geography: list[dict],
        ons_metadata_empty: dict,
        ons_raw_data_empty_dimensions: dict,
    ) -> None:
        """Test default UK geography when not specified."""
        result = ons_service._transform_observations(
            observations=ons_observations_no_geography,
            filters=None,
            metadata=ons_metadata_empty,
            dataset_code="test",
            raw_data=ons_raw_data_empty_dimensions,
        )

        assert len(result) == 1
        assert result[0]["geo"] == "K02000001"  # Default UK code

    def test_transform_preserves_flags_as_none(
        self,
        ons_service: OnsService,
        ons_observations_basic: list[dict],
        ons_metadata_empty: dict,
        ons_raw_data_empty_dimensions: dict,
    ) -> None:
        """Test that flags are set to None (ONS API doesn't provide them)."""
        result = ons_service._transform_observations(
            observations=ons_observations_basic,
            filters=None,
            metadata=ons_metadata_empty,
            dataset_code="test",
            raw_data=ons_raw_data_empty_dimensions,
        )

        assert len(result) == 2
        assert result[0]["flags"] is None
        assert result[1]["flags"] is None


class TestListAvailableDatasets:
    """Tests for list_available_datasets method."""

    @pytest.mark.asyncio
    async def test_delegates_to_repository(
        self,
        ons_service: OnsService,
        mock_ons_repository: MagicMock,
    ) -> None:
        """Test that list_available_datasets delegates to repository."""
        expected = [{"code": "trade", "name": "UK Trade"}]
        mock_ons_repository.list_datasets.return_value = expected

        result = await ons_service.list_available_datasets()

        assert result == expected
        mock_ons_repository.list_datasets.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_passes_category_filter(
        self,
        ons_service: OnsService,
        mock_ons_repository: MagicMock,
    ) -> None:
        """Test that category filter is passed to repository."""
        mock_ons_repository.list_datasets.return_value = []

        await ons_service.list_available_datasets(category="economy")

        mock_ons_repository.list_datasets.assert_called_once_with("economy")


class TestSearchDatasets:
    """Tests for search_datasets method."""

    @pytest.mark.asyncio
    async def test_delegates_to_repository(
        self,
        ons_service: OnsService,
        mock_ons_repository: MagicMock,
    ) -> None:
        """Test that search_datasets delegates to repository."""
        expected = [{"code": "trade", "name": "UK Trade"}]
        mock_ons_repository.search_datasets.return_value = expected

        result = await ons_service.search_datasets("trade")

        assert result == expected
        mock_ons_repository.search_datasets.assert_called_once_with("trade")


class TestFetchAndCache:
    """Tests for fetch_and_cache method (inherited from BaseService)."""

    @pytest.mark.asyncio
    async def test_caches_fetched_data(
        self,
        ons_service: OnsService,
        mock_ons_repository: MagicMock,
        test_cache: Cache,
    ) -> None:
        """Test that fetched data is cached."""
        mock_ons_repository.get_dataset.return_value = {
            "observations": [{"observation": "100.0"}],
            "_metadata": {"dataset_code": "trade"},
        }

        # First call - fetches from repository
        await ons_service.fetch_and_cache("trade")

        # Second call - should use cache
        await ons_service.fetch_and_cache("trade")

        # Repository should only be called once
        assert mock_ons_repository.get_dataset.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_from_repository(
        self,
        ons_service: OnsService,
        mock_ons_repository: MagicMock,
    ) -> None:
        """Test that cache miss triggers repository fetch."""
        mock_ons_repository.get_dataset.return_value = {
            "observations": [],
            "_metadata": {},
        }

        await ons_service.fetch_and_cache("new-dataset")

        mock_ons_repository.get_dataset.assert_called_once()

    @pytest.mark.asyncio
    async def test_different_filters_cause_cache_miss(
        self,
        ons_service: OnsService,
        mock_ons_repository: MagicMock,
    ) -> None:
        """Test that different filters are cached separately."""
        mock_ons_repository.get_dataset.return_value = {
            "observations": [],
            "_metadata": {},
        }

        # First call with filter A
        await ons_service.fetch_and_cache("trade", filters={"geo": "UK"})

        # Second call with filter B - should trigger new fetch
        await ons_service.fetch_and_cache("trade", filters={"geo": "FR"})

        # Repository should be called twice (different cache keys)
        assert mock_ons_repository.get_dataset.call_count == 2
