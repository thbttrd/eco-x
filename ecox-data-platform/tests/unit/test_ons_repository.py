"""Unit tests for ONS repository.

Tests cover:
- TOC fetching and caching
- Dataset version resolution
- Observations fetching
- Search functionality
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ecox_platform.sources.ons.repository import OnsRepository


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client."""
    client = MagicMock()
    client.get = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def ons_repository(mock_http_client: MagicMock) -> OnsRepository:
    """Create ONS repository with mocked HTTP client."""
    repo = OnsRepository(http_client=mock_http_client)
    return repo


class TestFetchToc:
    """Tests for fetch_toc method."""

    @pytest.mark.asyncio
    async def test_fetch_toc_returns_datasets(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        sample_ons_datasets_response: dict,
    ) -> None:
        """Test fetching TOC returns list of datasets."""
        mock_http_client.get.return_value = sample_ons_datasets_response

        toc = await ons_repository.fetch_toc(force_refresh=True)

        assert len(toc) == 3  # Fixture has 3 datasets
        assert toc[0]["code"] == "trade"
        assert toc[0]["name"] == "UK Trade"
        assert toc[1]["code"] == "regional-gdp-by-year"
        assert toc[2]["code"] == "employment-by-industry"

    @pytest.mark.asyncio
    async def test_fetch_toc_transforms_to_common_format(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        sample_ons_datasets_response: dict,
    ) -> None:
        """Test TOC entries are transformed to common format."""
        mock_http_client.get.return_value = sample_ons_datasets_response

        toc = await ons_repository.fetch_toc(force_refresh=True)

        # Check common format fields
        entry = toc[0]
        assert "code" in entry
        assert "name" in entry
        assert "description" in entry
        assert "category" in entry
        assert entry["category"] == "ons"
        assert "last_update" in entry
        assert "keywords" in entry

    @pytest.mark.asyncio
    async def test_fetch_toc_handles_pagination(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        ons_paginated_datasets_page1: dict,
        ons_paginated_datasets_page2: dict,
    ) -> None:
        """Test TOC fetching handles multiple pages."""
        mock_http_client.get.side_effect = [
            ons_paginated_datasets_page1,
            ons_paginated_datasets_page2,
        ]

        toc = await ons_repository.fetch_toc(force_refresh=True)

        assert len(toc) == 150
        assert mock_http_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_toc_handles_api_error(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
    ) -> None:
        """Test TOC fetching returns empty list on API error."""
        mock_http_client.get.side_effect = Exception("API Error")

        toc = await ons_repository.fetch_toc(force_refresh=True)

        assert toc == []


class TestGetLatestVersion:
    """Tests for _get_latest_version method."""

    @pytest.mark.asyncio
    async def test_get_latest_version_caches_result(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        sample_ons_editions_response: dict,
        sample_ons_version_response: dict,
    ) -> None:
        """Test version info is cached after first call."""
        mock_http_client.get.side_effect = [
            sample_ons_editions_response,
            sample_ons_version_response,
        ]

        # First call - fetches from API
        result1 = await ons_repository._get_latest_version("trade")
        assert result1 is not None
        assert result1["edition"] == "time-series"
        assert result1["version"] == "1"

        # Second call - should use cache
        result2 = await ons_repository._get_latest_version("trade")
        assert result2 == result1
        assert mock_http_client.get.call_count == 2  # Only called during first call

    @pytest.mark.asyncio
    async def test_get_latest_version_handles_empty_editions(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        ons_empty_response: dict,
    ) -> None:
        """Test handling of dataset with no editions."""
        mock_http_client.get.return_value = ons_empty_response

        result = await ons_repository._get_latest_version("empty-dataset")

        assert result is None


class TestGetDataset:
    """Tests for get_dataset method."""

    @pytest.mark.asyncio
    async def test_get_dataset_fetches_observations(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        sample_ons_editions_response: dict,
        sample_ons_version_response: dict,
        sample_ons_observations_response: dict,
    ) -> None:
        """Test fetching dataset observations."""
        # Setup mock responses for version info + dimension options + observations
        mock_http_client.get.side_effect = [
            sample_ons_editions_response,
            sample_ons_version_response,
            {"items": [{"option": "K02000001"}]},  # geography options
            {"items": [{"option": "total"}]},  # tradetype options
            sample_ons_observations_response,
        ]

        data = await ons_repository.get_dataset("trade")

        assert "observations" in data
        assert len(data["observations"]) == 4  # Fixture has 4 observations (Q1-Q4)
        assert data["_metadata"]["dataset_code"] == "trade"
        assert data["_metadata"]["edition"] == "time-series"

    @pytest.mark.asyncio
    async def test_get_dataset_with_filters(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        sample_ons_editions_response: dict,
        sample_ons_version_response: dict,
        sample_ons_observations_response: dict,
    ) -> None:
        """Test fetching dataset with dimension filters."""
        mock_http_client.get.side_effect = [
            sample_ons_editions_response,
            sample_ons_version_response,
            sample_ons_observations_response,
        ]

        filters = {"geography": "K02000001", "tradetype": "total"}
        await ons_repository.get_dataset("trade", filters=filters)

        # Check that filters were used in the request
        call_args = mock_http_client.get.call_args_list[-1]
        params = call_args[1].get("params", {})
        assert params.get("geography") == "K02000001"
        assert params.get("tradetype") == "total"
        assert params.get("time") == "*"  # Time defaults to wildcard

    @pytest.mark.asyncio
    async def test_get_dataset_raises_on_missing_dataset(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        ons_empty_response: dict,
    ) -> None:
        """Test error handling for non-existent dataset."""
        mock_http_client.get.return_value = ons_empty_response

        with pytest.raises(ValueError, match="Could not find dataset"):
            await ons_repository.get_dataset("nonexistent")


class TestSearchDatasets:
    """Tests for search_datasets method."""

    @pytest.mark.asyncio
    async def test_search_by_name(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        sample_ons_datasets_response: dict,
    ) -> None:
        """Test searching datasets by name."""
        mock_http_client.get.return_value = sample_ons_datasets_response

        # Force refresh TOC to ensure we use our fixture data
        await ons_repository.fetch_toc(force_refresh=True)
        results = await ons_repository.search_datasets("trade")

        assert len(results) == 1
        assert results[0]["code"] == "trade"

    @pytest.mark.asyncio
    async def test_search_by_keyword(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        sample_ons_datasets_response: dict,
    ) -> None:
        """Test searching datasets by keyword."""
        mock_http_client.get.return_value = sample_ons_datasets_response

        # Force refresh TOC to ensure we use our fixture data
        await ons_repository.fetch_toc(force_refresh=True)
        results = await ons_repository.search_datasets("gdp")

        assert len(results) == 1
        assert results[0]["code"] == "regional-gdp-by-year"

    @pytest.mark.asyncio
    async def test_search_case_insensitive(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        sample_ons_datasets_response: dict,
    ) -> None:
        """Test search is case-insensitive."""
        mock_http_client.get.return_value = sample_ons_datasets_response

        # Force refresh TOC to ensure we use our fixture data
        await ons_repository.fetch_toc(force_refresh=True)
        results = await ons_repository.search_datasets("TRADE")

        assert len(results) == 1
        assert results[0]["code"] == "trade"


class TestGetDatasetMetadata:
    """Tests for get_dataset_metadata method."""

    @pytest.mark.asyncio
    async def test_get_metadata_includes_dimensions(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        sample_ons_editions_response: dict,
        sample_ons_version_response: dict,
    ) -> None:
        """Test metadata includes dimension information."""
        mock_http_client.get.side_effect = [
            {"id": "trade", "title": "UK Trade"},  # Basic dataset info
            sample_ons_editions_response,
            sample_ons_version_response,
        ]

        metadata = await ons_repository.get_dataset_metadata("trade")

        assert "dimensions" in metadata
        assert len(metadata["dimensions"]) == 3
        assert metadata["edition"] == "time-series"
        assert metadata["version"] == "1"

    @pytest.mark.asyncio
    async def test_get_metadata_raises_on_error(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
    ) -> None:
        """Test error handling for metadata fetch failure."""
        mock_http_client.get.side_effect = Exception("API Error")

        with pytest.raises(ValueError, match="Failed to get metadata"):
            await ons_repository.get_dataset_metadata("trade")


class TestGetFirstDimensionOption:
    """Tests for _get_first_dimension_option method.

    This method must skip negative values (like -8) which are metadata codes
    that cause ONS API 500 errors when used in observation queries.
    """

    @pytest.mark.asyncio
    async def test_skips_negative_dimension_values(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        ons_dimension_options_with_negative: dict,
    ) -> None:
        """Test that negative dimension options are skipped.

        The ONS API uses negative values like -8 ("Does not apply") as metadata
        codes. These cannot be used in observation queries and cause 500 errors.
        """
        mock_http_client.get.return_value = ons_dimension_options_with_negative

        result = await ons_repository._get_first_dimension_option(
            "TS079", "2021", "5", "sexual_orientation_9a"
        )

        # Should skip -8 and -7, return first positive value "1"
        assert result == "1"

    @pytest.mark.asyncio
    async def test_returns_none_when_all_negative(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        ons_dimension_options_all_negative: dict,
    ) -> None:
        """Test returns None when all options are negative."""
        mock_http_client.get.return_value = ons_dimension_options_all_negative

        result = await ons_repository._get_first_dimension_option("TS999", "2021", "1", "some_dim")

        assert result is None

    @pytest.mark.asyncio
    async def test_accepts_non_numeric_options(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
        ons_dimension_options_non_numeric: dict,
    ) -> None:
        """Test that non-numeric options (like geography codes) are accepted."""
        mock_http_client.get.return_value = ons_dimension_options_non_numeric

        result = await ons_repository._get_first_dimension_option(
            "trade", "time-series", "1", "geography"
        )

        # Non-numeric values should be returned as-is
        assert result == "K02000001"

    @pytest.mark.asyncio
    async def test_handles_api_error(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
    ) -> None:
        """Test error handling for dimension options fetch failure."""
        mock_http_client.get.side_effect = Exception("API Error")

        result = await ons_repository._get_first_dimension_option(
            "trade", "time-series", "1", "geography"
        )

        assert result is None


class TestProblematicDatasetTracking:
    """Tests for problematic dataset tracking (500 error handling).

    When datasets consistently return 500 errors, they should be marked
    as problematic and skipped in future fetch attempts.
    """

    def test_record_failure_increments_count(
        self,
        ons_repository: OnsRepository,
    ) -> None:
        """Test that record_dataset_failure increments failure count."""
        ons_repository.record_dataset_failure("test-dataset")
        assert ons_repository._failure_counts["test-dataset"] == 1

        ons_repository.record_dataset_failure("test-dataset")
        assert ons_repository._failure_counts["test-dataset"] == 2

    def test_dataset_marked_problematic_after_threshold(
        self,
        ons_repository: OnsRepository,
    ) -> None:
        """Test dataset is marked problematic after N consecutive failures."""
        dataset_id = "problem-dataset"

        # Record failures to reach threshold (threshold is 1)
        ons_repository.record_dataset_failure(dataset_id)

        assert ons_repository.should_skip_dataset(dataset_id) is True
        assert dataset_id in ons_repository._problematic_datasets

    def test_dataset_not_marked_before_threshold(
        self,
        ons_repository: OnsRepository,
    ) -> None:
        """Test dataset is not marked problematic before reaching threshold."""
        dataset_id = "failing-dataset"

        # Don't record any failures - threshold is 1, so we need 0 to test "before"
        # This test verifies a dataset starts in a non-problematic state
        assert ons_repository.should_skip_dataset(dataset_id) is False
        assert dataset_id not in ons_repository._problematic_datasets

    def test_should_skip_returns_false_for_normal_dataset(
        self,
        ons_repository: OnsRepository,
    ) -> None:
        """Test should_skip_dataset returns False for normal datasets."""
        assert ons_repository.should_skip_dataset("normal-dataset") is False

    def test_record_success_resets_failure_count(
        self,
        ons_repository: OnsRepository,
    ) -> None:
        """Test that success resets the failure count."""
        dataset_id = "intermittent-dataset"

        # Record some failures
        ons_repository.record_dataset_failure(dataset_id)
        ons_repository.record_dataset_failure(dataset_id)
        assert ons_repository._failure_counts[dataset_id] == 2

        # Record success
        ons_repository.record_dataset_success(dataset_id)

        # Failure count should be reset
        assert dataset_id not in ons_repository._failure_counts

    def test_success_removes_from_problematic(
        self,
        ons_repository: OnsRepository,
    ) -> None:
        """Test that success removes dataset from problematic set.

        When a previously problematic dataset succeeds, it should be removed
        from the problematic set to allow future fetch attempts.
        """
        dataset_id = "persistent-problem"

        # Mark as problematic (threshold is 1)
        ons_repository.record_dataset_failure(dataset_id)
        assert ons_repository.should_skip_dataset(dataset_id) is True

        # Record success
        ons_repository.record_dataset_success(dataset_id)

        # Should no longer be marked as problematic
        assert ons_repository.should_skip_dataset(dataset_id) is False

    def test_multiple_datasets_tracked_independently(
        self,
        ons_repository: OnsRepository,
    ) -> None:
        """Test that failure tracking is independent per dataset."""
        dataset_a = "dataset-a"
        dataset_b = "dataset-b"

        # Fail dataset_a once to mark as problematic (threshold is 1)
        ons_repository.record_dataset_failure(dataset_a)

        # Don't fail dataset_b - keep it normal
        # (no action needed)

        assert ons_repository.should_skip_dataset(dataset_a) is True
        assert ons_repository.should_skip_dataset(dataset_b) is False

    @pytest.mark.asyncio
    async def test_get_dataset_skips_problematic(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
    ) -> None:
        """Test that get_dataset raises error for problematic datasets."""
        dataset_id = "known-problem"

        # Mark as problematic (threshold is 1)
        ons_repository.record_dataset_failure(dataset_id)

        with pytest.raises(ValueError, match="marked as problematic"):
            await ons_repository.get_dataset(dataset_id)

        # HTTP client should not be called
        mock_http_client.get.assert_not_called()


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_closes_http_client(
        self,
        ons_repository: OnsRepository,
        mock_http_client: MagicMock,
    ) -> None:
        """Test close method closes HTTP client."""
        await ons_repository.close()

        mock_http_client.close.assert_called_once()
