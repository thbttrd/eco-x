"""Unit tests for OECD repository.

Tests cover:
- TOC fetching and caching
- Dataset fetching
- SDMX data key building
- Search functionality
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ecox_platform.sources.oecd.repository import OecdRepository


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client."""
    client = MagicMock()
    client.get = AsyncMock()
    client.get_large = AsyncMock()  # Used for large dataset fetches
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_structure_client() -> MagicMock:
    """Create a mock structure httpx client."""
    client = MagicMock()
    client.get = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def oecd_repository(
    mock_http_client: MagicMock, mock_structure_client: MagicMock
) -> OecdRepository:
    """Create OECD repository with mocked HTTP clients."""
    repo = OecdRepository(http_client=mock_http_client)
    # Replace the structure client with mock
    repo._structure_client = mock_structure_client
    return repo


def _make_mock_response(json_data: dict) -> MagicMock:
    """Create a mock httpx Response with json() method."""
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


class TestFetchToc:
    """Tests for fetch_toc method."""

    @pytest.mark.asyncio
    async def test_fetch_toc_returns_datasets(
        self,
        oecd_repository: OecdRepository,
        mock_structure_client: MagicMock,
        sample_oecd_dataflows_response: dict,
    ) -> None:
        """Test fetching TOC returns list of datasets."""
        mock_structure_client.get.return_value = _make_mock_response(sample_oecd_dataflows_response)

        toc = await oecd_repository.fetch_toc(force_refresh=True)

        assert len(toc) == 3  # Fixture has 3 dataflows
        # Check first dataflow
        assert toc[0]["code"] == "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0"
        assert toc[0]["name"] == "Key Short-Term Economic Indicators"
        assert toc[0]["agency_id"] == "OECD.SDD.STES"
        assert toc[0]["dataflow_id"] == "DSD_KEI@DF_KEI"
        assert toc[0]["version"] == "4.0"

    @pytest.mark.asyncio
    async def test_fetch_toc_transforms_to_common_format(
        self,
        oecd_repository: OecdRepository,
        mock_structure_client: MagicMock,
        sample_oecd_dataflows_response: dict,
    ) -> None:
        """Test TOC entries are transformed to common format."""
        mock_structure_client.get.return_value = _make_mock_response(sample_oecd_dataflows_response)

        toc = await oecd_repository.fetch_toc(force_refresh=True)

        # Check common format fields
        entry = toc[0]
        assert "code" in entry
        assert "name" in entry
        assert "description" in entry
        assert "category" in entry
        assert entry["category"].startswith("oecd_")
        assert "metadata_url" in entry

    @pytest.mark.asyncio
    async def test_fetch_toc_handles_api_error(
        self,
        oecd_repository: OecdRepository,
        mock_structure_client: MagicMock,
    ) -> None:
        """Test TOC fetching returns empty list on API error."""
        mock_structure_client.get.side_effect = Exception("API Error")

        toc = await oecd_repository.fetch_toc(force_refresh=True)

        assert toc == []


class TestGetDataset:
    """Tests for get_dataset method."""

    @pytest.mark.asyncio
    async def test_get_dataset_fetches_data(
        self,
        oecd_repository: OecdRepository,
        mock_http_client: MagicMock,
        sample_oecd_data_response: dict,
    ) -> None:
        """Test fetching dataset data."""
        mock_http_client.get_large.return_value = sample_oecd_data_response

        data = await oecd_repository.get_dataset("OECD.SDD.STES,DSD_KEI@DF_KEI,4.0")

        assert "data" in data
        assert "dataSets" in data["data"]
        assert "_metadata" in data
        assert data["_metadata"]["dataset_code"] == "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0"
        assert data["_metadata"]["agency_id"] == "OECD.SDD.STES"
        assert data["_metadata"]["dataflow_id"] == "DSD_KEI@DF_KEI"
        assert data["_metadata"]["version"] == "4.0"

    @pytest.mark.asyncio
    async def test_get_dataset_with_filters(
        self,
        oecd_repository: OecdRepository,
        mock_http_client: MagicMock,
        sample_oecd_data_response: dict,
    ) -> None:
        """Test fetching dataset with filters."""
        mock_http_client.get_large.return_value = sample_oecd_data_response

        filters = {
            "REF_AREA": "USA",
            "FREQ": "A",
            "startPeriod": "2020",
            "endPeriod": "2023",
        }
        await oecd_repository.get_dataset("OECD.SDD.STES,DSD_KEI@DF_KEI,4.0", filters=filters)

        # Check that call was made with correct path and params
        call_args = mock_http_client.get_large.call_args
        path = call_args[0][0]
        params = call_args[1].get("params", {})

        # Path should include agency,dataflow,version and key
        assert "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0" in path
        assert "USA.A" in path  # Key built from filters

        # Time params should be in query params
        assert params["startPeriod"] == "2020"
        assert params["endPeriod"] == "2023"

    @pytest.mark.asyncio
    async def test_get_dataset_raises_on_invalid_code(
        self,
        oecd_repository: OecdRepository,
        mock_http_client: MagicMock,
    ) -> None:
        """Test error handling for invalid dataset code format."""
        with pytest.raises(ValueError, match="Invalid dataset code format"):
            await oecd_repository.get_dataset("invalid_code")


class TestBuildDataKey:
    """Tests for _build_data_key method."""

    def test_build_key_empty_filters(self, oecd_repository: OecdRepository) -> None:
        """Test key building with no filters."""
        key = oecd_repository._build_data_key(None)
        assert key == ""

    def test_build_key_single_dimension(self, oecd_repository: OecdRepository) -> None:
        """Test key building with single dimension."""
        key = oecd_repository._build_data_key({"REF_AREA": "USA"})
        assert key == "USA"

    def test_build_key_multiple_dimensions(self, oecd_repository: OecdRepository) -> None:
        """Test key building with multiple dimensions."""
        key = oecd_repository._build_data_key(
            {
                "REF_AREA": "USA",
                "FREQ": "A",
                "MEASURE": "GDP",
            }
        )
        assert key == "USA.A.GDP"

    def test_build_key_multiple_values_per_dimension(self, oecd_repository: OecdRepository) -> None:
        """Test key building with multiple values for a dimension."""
        key = oecd_repository._build_data_key(
            {
                "REF_AREA": ["USA", "FRA", "DEU"],
                "FREQ": "A",
            }
        )
        assert key == "USA+FRA+DEU.A"

    def test_build_key_strips_trailing_dots(self, oecd_repository: OecdRepository) -> None:
        """Test that trailing dots are removed from key."""
        key = oecd_repository._build_data_key({"REF_AREA": "USA"})
        assert not key.endswith(".")


class TestSearchDatasets:
    """Tests for search_datasets method."""

    @pytest.mark.asyncio
    async def test_search_by_name(
        self,
        oecd_repository: OecdRepository,
        mock_structure_client: MagicMock,
        sample_oecd_dataflows_response: dict,
    ) -> None:
        """Test searching datasets by name."""
        mock_structure_client.get.return_value = _make_mock_response(sample_oecd_dataflows_response)

        # Force refresh TOC first
        await oecd_repository.fetch_toc(force_refresh=True)
        results = await oecd_repository.search_datasets("economic indicators")

        assert len(results) == 1
        assert "Key Short-Term Economic Indicators" in results[0]["name"]

    @pytest.mark.asyncio
    async def test_search_by_dataflow_id(
        self,
        oecd_repository: OecdRepository,
        mock_structure_client: MagicMock,
        sample_oecd_dataflows_response: dict,
    ) -> None:
        """Test searching datasets by dataflow ID."""
        mock_structure_client.get.return_value = _make_mock_response(sample_oecd_dataflows_response)

        await oecd_repository.fetch_toc(force_refresh=True)
        results = await oecd_repository.search_datasets("DF_GDP")

        assert len(results) == 1
        assert results[0]["dataflow_id"] == "DSD_REG_ECO@DF_GDP"

    @pytest.mark.asyncio
    async def test_search_case_insensitive(
        self,
        oecd_repository: OecdRepository,
        mock_structure_client: MagicMock,
        sample_oecd_dataflows_response: dict,
    ) -> None:
        """Test search is case-insensitive."""
        mock_structure_client.get.return_value = _make_mock_response(sample_oecd_dataflows_response)

        await oecd_repository.fetch_toc(force_refresh=True)
        results = await oecd_repository.search_datasets("REGIONAL GDP")

        assert len(results) == 1
        assert results[0]["name"] == "Regional GDP"


class TestGetDatasetMetadata:
    """Tests for get_dataset_metadata method."""

    @pytest.mark.asyncio
    async def test_get_metadata_includes_dimensions(
        self,
        oecd_repository: OecdRepository,
        mock_structure_client: MagicMock,
        sample_oecd_structure_response: dict,
    ) -> None:
        """Test metadata includes dimension information."""
        mock_structure_client.get.return_value = _make_mock_response(sample_oecd_structure_response)

        metadata = await oecd_repository.get_dataset_metadata("OECD.SDD.STES,DSD_KEI@DF_KEI,4.0")

        assert "dimensions" in metadata
        assert len(metadata["dimensions"]) == 7
        assert metadata["dimensions"][0]["id"] == "REF_AREA"
        assert "attributes" in metadata
        assert len(metadata["attributes"]) == 3

    @pytest.mark.asyncio
    async def test_get_metadata_includes_dataflow_info(
        self,
        oecd_repository: OecdRepository,
        mock_structure_client: MagicMock,
        sample_oecd_structure_response: dict,
    ) -> None:
        """Test metadata includes dataflow information."""
        mock_structure_client.get.return_value = _make_mock_response(sample_oecd_structure_response)

        metadata = await oecd_repository.get_dataset_metadata("OECD.SDD.STES,DSD_KEI@DF_KEI,4.0")

        assert metadata["name"] == "Key Short-Term Economic Indicators"
        assert metadata["agency_id"] == "OECD.SDD.STES"
        assert metadata["version"] == "4.0"

    @pytest.mark.asyncio
    async def test_get_metadata_raises_on_error(
        self,
        oecd_repository: OecdRepository,
        mock_structure_client: MagicMock,
    ) -> None:
        """Test error handling for metadata fetch failure."""
        mock_structure_client.get.side_effect = Exception("API Error")

        with pytest.raises(ValueError, match="Failed to get metadata"):
            await oecd_repository.get_dataset_metadata("OECD.SDD.STES,DSD_KEI@DF_KEI,4.0")


class TestValidateFilters:
    """Tests for validate_filters method."""

    @pytest.mark.asyncio
    async def test_validate_filters_accepts_strings(self, oecd_repository: OecdRepository) -> None:
        """Test that string filter values are valid."""
        result = await oecd_repository.validate_filters(
            "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0",
            {"REF_AREA": "USA", "FREQ": "A"},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_filters_accepts_lists(self, oecd_repository: OecdRepository) -> None:
        """Test that list filter values are valid."""
        result = await oecd_repository.validate_filters(
            "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0",
            {"REF_AREA": ["USA", "FRA", "DEU"]},
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_filters_rejects_invalid_types(
        self, oecd_repository: OecdRepository
    ) -> None:
        """Test that non-string, non-list filter values are invalid."""
        result = await oecd_repository.validate_filters(
            "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0",
            {"REF_AREA": 123},  # Invalid: integer
        )
        assert result is False


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close_closes_http_clients(
        self,
        oecd_repository: OecdRepository,
        mock_http_client: MagicMock,
        mock_structure_client: MagicMock,
    ) -> None:
        """Test close method closes both HTTP clients."""
        await oecd_repository.close()

        mock_http_client.close.assert_called_once()
        mock_structure_client.aclose.assert_called_once()
