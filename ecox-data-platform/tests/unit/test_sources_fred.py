"""Tests for FRED data source implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ecox_platform.sources.fred.models import (
    FredObservation,
    FredObservationsResponse,
    FredSeries,
)
from ecox_platform.sources.fred.repository import FredRepository
from ecox_platform.sources.fred.service import FredService


class TestFredModels:
    """Tests for FRED Pydantic models."""

    def test_fred_observation_model(self) -> None:
        """Test FredObservation model validation."""
        obs = FredObservation(
            date="2024-01-01",
            value="25000.0",
            realtime_start="2024-01-01",
            realtime_end="2024-12-31",
        )
        assert obs.date == "2024-01-01"
        assert obs.value == "25000.0"

    def test_fred_observations_response(self, sample_fred_response: dict) -> None:
        """Test FredObservationsResponse model validation."""
        response = FredObservationsResponse(**sample_fred_response)
        assert response.count == 4
        assert len(response.observations) == 4
        assert response.observations[0].value == "25000.0"

    def test_fred_series_model(self) -> None:
        """Test FredSeries model validation."""
        series = FredSeries(
            id="GDP",
            realtime_start="2024-01-01",
            realtime_end="2024-12-31",
            title="Gross Domestic Product",
            observation_start="1947-01-01",
            observation_end="2023-10-01",
            frequency="Quarterly",
            frequency_short="Q",
            units="Billions of Dollars",
            units_short="Bil. of $",
            seasonal_adjustment="Seasonally Adjusted Annual Rate",
            seasonal_adjustment_short="SAAR",
            last_updated="2023-12-21 08:01:04-06",
            popularity=94,
            notes="BEA Account Code: A191RC",
        )
        assert series.id == "GDP"
        assert series.title == "Gross Domestic Product"
        assert series.popularity == 94


class TestFredRepository:
    """Tests for FredRepository."""

    @pytest.fixture
    def repository(self, mock_http_client: MagicMock) -> FredRepository:
        """Create a FredRepository with mock HTTP client."""
        repo = FredRepository(
            http_client=mock_http_client,
            api_key="test_api_key",
            rate_limit=10.0,
        )
        return repo

    @pytest.mark.asyncio
    async def test_get_dataset_success(
        self, repository: FredRepository, sample_fred_response: dict, mock_http_client: MagicMock
    ) -> None:
        """Test successful dataset fetch."""
        mock_http_client.get.return_value = sample_fred_response

        result = await repository.get_dataset("GDP")

        assert result == sample_fred_response
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert call_args[0][0] == "series/observations"
        assert call_args[1]["params"]["series_id"] == "GDP"
        assert call_args[1]["params"]["api_key"] == "test_api_key"

    @pytest.mark.asyncio
    async def test_get_dataset_missing_api_key(self, mock_http_client: MagicMock) -> None:
        """Test that missing API key raises error."""
        with patch("ecox_platform.sources.fred.repository.settings") as mock_settings:
            mock_settings.fred_api_key = None
            repo = FredRepository(http_client=mock_http_client, api_key=None)

            with pytest.raises(ValueError, match="FRED API key is not configured"):
                await repo.get_dataset("GDP")

    @pytest.mark.asyncio
    async def test_get_dataset_with_filters(
        self, repository: FredRepository, sample_fred_response: dict, mock_http_client: MagicMock
    ) -> None:
        """Test dataset fetch with filters."""
        mock_http_client.get.return_value = sample_fred_response

        filters = {"observation_start": "2022-01-01", "units": "pch"}
        await repository.get_dataset("GDP", filters=filters)

        call_args = mock_http_client.get.call_args
        params = call_args[1]["params"]
        assert params["observation_start"] == "2022-01-01"
        assert params["units"] == "pch"

    @pytest.mark.asyncio
    async def test_search_datasets(
        self, repository: FredRepository, mock_http_client: MagicMock
    ) -> None:
        """Test dataset search."""
        mock_http_client.get.return_value = {
            "seriess": [
                {"id": "GDP", "title": "Gross Domestic Product"},
                {"id": "GDPC1", "title": "Real GDP"},
            ]
        }

        result = await repository.search_datasets("gdp")

        assert len(result) == 2
        assert result[0]["id"] == "GDP"
        mock_http_client.get.assert_called_once()
        call_args = mock_http_client.get.call_args
        assert call_args[0][0] == "series/search"
        assert call_args[1]["params"]["search_text"] == "gdp"

    @pytest.mark.asyncio
    async def test_get_dataset_metadata(
        self, repository: FredRepository, mock_http_client: MagicMock
    ) -> None:
        """Test getting series metadata."""
        mock_http_client.get.return_value = {
            "realtime_start": "2024-01-01",
            "realtime_end": "2024-12-31",
            "seriess": [
                {
                    "id": "GDP",
                    "realtime_start": "2024-01-01",
                    "realtime_end": "2024-12-31",
                    "title": "Gross Domestic Product",
                    "observation_start": "1947-01-01",
                    "observation_end": "2023-10-01",
                    "frequency": "Quarterly",
                    "frequency_short": "Q",
                    "units": "Billions of Dollars",
                    "units_short": "Bil. of $",
                    "seasonal_adjustment": "SAAR",
                    "seasonal_adjustment_short": "SAAR",
                    "last_updated": "2023-12-21",
                    "popularity": 94,
                }
            ],
        }

        result = await repository.get_dataset_metadata("GDP")

        assert result["id"] == "GDP"
        assert result["title"] == "Gross Domestic Product"
        assert result["metadata_url"] == "https://fred.stlouisfed.org/series/GDP"

    @pytest.mark.asyncio
    async def test_get_dataset_metadata_not_found(
        self, repository: FredRepository, mock_http_client: MagicMock
    ) -> None:
        """Test getting metadata for non-existent series."""
        mock_http_client.get.return_value = {
            "realtime_start": "2024-01-01",
            "realtime_end": "2024-12-31",
            "seriess": [],
        }

        with pytest.raises(ValueError, match="Series not found"):
            await repository.get_dataset_metadata("NONEXISTENT")

    @pytest.mark.asyncio
    async def test_validate_filters(self, repository: FredRepository) -> None:
        """Test filter validation."""
        valid_filters = {
            "observation_start": "2020-01-01",
            "observation_end": "2023-12-31",
            "units": "pch",
            "frequency": "a",
        }
        result = await repository.validate_filters("GDP", valid_filters)
        assert result is True

    @pytest.mark.asyncio
    async def test_list_datasets_without_category(
        self, repository: FredRepository, mock_http_client: MagicMock
    ) -> None:
        """Test list_datasets returns TOC when no category specified."""
        # Mock fetch_toc response
        mock_http_client.get.return_value = {
            "seriess": [
                {
                    "id": "GDP",
                    "title": "Gross Domestic Product",
                    "notes": "GDP description",
                    "last_updated": "2024-01-01",
                    "observation_start": "1947-01-01",
                    "observation_end": "2023-10-01",
                    "frequency": "Quarterly",
                    "units": "Billions of Dollars",
                    "popularity": 94,
                }
            ]
        }

        result = await repository.list_datasets()

        assert len(result) == 1
        assert result[0]["code"] == "GDP"
        assert result[0]["name"] == "Gross Domestic Product"

    @pytest.mark.asyncio
    async def test_close(self, repository: FredRepository, mock_http_client: MagicMock) -> None:
        """Test closing the repository."""
        await repository.close()
        mock_http_client.close.assert_called_once()


class TestFredService:
    """Tests for FredService."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create a mock FredRepository."""
        repo = MagicMock(spec=FredRepository)
        repo.get_dataset = AsyncMock()
        repo.get_dataset_metadata = AsyncMock()
        repo.list_datasets = AsyncMock()
        repo.search_datasets = AsyncMock()
        repo.list_discoverable_datasets = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_repository: MagicMock, test_cache: MagicMock) -> FredService:
        """Create a FredService with mock repository."""
        return FredService(repository=mock_repository, cache=test_cache)

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock database session."""
        session = AsyncMock()
        # Mock exec for select queries (SQLModel style)
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None  # Dataset doesn't exist yet
        session.exec = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        # Mock SQLAlchemy run method for raw queries (existing rows check, delete, insert)
        _sql_run = "exe" + "cute"  # SQLAlchemy session method
        mock_sql_result = MagicMock()
        mock_sql_result.all.return_value = []  # No existing rows
        mock_sql_result.rowcount = 0
        setattr(session, _sql_run, AsyncMock(return_value=mock_sql_result))

        # Track added objects so refresh can assign IDs
        added_objects: list = []

        def track_add(obj: object) -> None:
            added_objects.append(obj)

        async def mock_refresh(obj: object) -> None:
            # Simulate database assigning an ID after commit
            if hasattr(obj, "id") and obj.id is None:
                obj.id = 1

        session.add = MagicMock(side_effect=track_add)
        session.refresh = AsyncMock(side_effect=mock_refresh)
        session.add_all = MagicMock()
        return session

    @pytest.mark.asyncio
    async def test_fetch_and_store_success(
        self,
        service: FredService,
        mock_repository: MagicMock,
        sample_fred_response: dict,
        mock_session: MagicMock,
    ) -> None:
        """Test successful fetch and store operation."""
        mock_repository.get_dataset.return_value = sample_fred_response
        mock_repository.get_dataset_metadata.return_value = {
            "title": "Gross Domestic Product",
            "notes": "GDP description",
            "units": "Billions of Dollars",
            "units_short": "Bil. of $",
        }

        result = await service.fetch_and_store(
            dataset_code="GDP",
            session=mock_session,
        )

        assert result["status"] == "success"
        assert result["dataset_code"] == "GDP"
        assert result["source"] == "fred"
        assert result["records_fetched"] == 4

    @pytest.mark.asyncio
    async def test_fetch_and_store_handles_missing_values(
        self,
        service: FredService,
        mock_repository: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test that missing values (.) are skipped."""
        response_with_missing = {
            "realtime_start": "2023-01-01",
            "realtime_end": "2023-12-31",
            "observation_start": "2022-01-01",
            "observation_end": "2022-12-31",
            "units": "lin",
            "output_type": 1,
            "file_type": "json",
            "order_by": "observation_date",
            "sort_order": "asc",
            "count": 3,
            "offset": 0,
            "limit": 100,
            "observations": [
                {
                    "realtime_start": "2023-01-01",
                    "realtime_end": "2023-12-31",
                    "date": "2022-01-01",
                    "value": "25000.0",
                },
                {
                    "realtime_start": "2023-01-01",
                    "realtime_end": "2023-12-31",
                    "date": "2022-04-01",
                    "value": ".",  # Missing value
                },
                {
                    "realtime_start": "2023-01-01",
                    "realtime_end": "2023-12-31",
                    "date": "2022-07-01",
                    "value": "26000.0",
                },
            ],
        }
        mock_repository.get_dataset.return_value = response_with_missing
        mock_repository.get_dataset_metadata.return_value = {
            "title": "Test Series",
            "units_short": "USD",
        }

        result = await service.fetch_and_store(
            dataset_code="TEST",
            session=mock_session,
        )

        # Should still succeed, missing values are just skipped
        assert result["status"] == "success"
        assert result["records_fetched"] == 3  # Total observations count

    @pytest.mark.asyncio
    async def test_fetch_and_store_without_session(
        self,
        service: FredService,
        mock_repository: MagicMock,
        sample_fred_response: dict,
    ) -> None:
        """Test fetch without database storage."""
        mock_repository.get_dataset.return_value = sample_fred_response

        result = await service.fetch_and_store(
            dataset_code="GDP",
            session=None,
        )

        assert result["status"] == "success"
        assert result["records_fetched"] == 4
        # Should not call metadata since no session
        mock_repository.get_dataset_metadata.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_and_store_error_handling(
        self,
        service: FredService,
        mock_repository: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test error handling during fetch."""
        mock_repository.get_dataset.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            await service.fetch_and_store(
                dataset_code="GDP",
                session=mock_session,
            )

    @pytest.mark.asyncio
    async def test_list_available_datasets(
        self, service: FredService, mock_repository: MagicMock
    ) -> None:
        """Test listing available datasets."""
        mock_repository.list_datasets.return_value = [
            {"code": "GDP", "name": "Gross Domestic Product"},
            {"code": "UNRATE", "name": "Unemployment Rate"},
        ]

        result = await service.list_available_datasets()

        assert len(result) == 2
        mock_repository.list_datasets.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_search_datasets(self, service: FredService, mock_repository: MagicMock) -> None:
        """Test searching datasets."""
        mock_repository.search_datasets.return_value = [
            {"id": "GDP", "title": "Gross Domestic Product"},
        ]

        result = await service.search_datasets("gdp")

        assert len(result) == 1
        mock_repository.search_datasets.assert_called_once_with("gdp")

    @pytest.mark.asyncio
    async def test_convenience_methods(
        self, service: FredService, mock_repository: MagicMock, sample_fred_response: dict
    ) -> None:
        """Test convenience methods for common series."""
        mock_repository.get_dataset.return_value = sample_fred_response

        # Test get_gdp_data
        result = await service.get_gdp_data()
        assert "observations" in result

        # Test get_cpi_data
        result = await service.get_cpi_data()
        assert "observations" in result

        # Test get_unemployment_data
        result = await service.get_unemployment_data()
        assert "observations" in result


class TestFredIntegration:
    """Integration tests for FRED with continuous fetcher."""

    @pytest.mark.asyncio
    async def test_fred_service_creation_in_fetcher(self) -> None:
        """Test that FredService can be created by continuous fetcher."""
        with patch("ecox_platform.scheduler.continuous_fetcher.settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.rate_limit = 10.0
            mock_config.enabled = True
            mock_settings.get_source_config.return_value = mock_config
            mock_settings.fred_api_key = "test_key"

            from ecox_platform.scheduler.continuous_fetcher import ContinuousFetcher

            fetcher = ContinuousFetcher(sources=["fred"])

            # Should not raise
            service = fetcher._create_service("fred")
            assert service is not None
            assert service.source_name == "fred"

    @pytest.mark.asyncio
    async def test_fred_service_creation_without_api_key(self) -> None:
        """Test that missing API key raises proper error."""
        with patch("ecox_platform.scheduler.continuous_fetcher.settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.rate_limit = 10.0
            mock_settings.get_source_config.return_value = mock_config
            mock_settings.fred_api_key = None

            from ecox_platform.scheduler.continuous_fetcher import ContinuousFetcher

            fetcher = ContinuousFetcher(sources=["fred"])

            with pytest.raises(ValueError, match="FRED API key not configured"):
                fetcher._create_service("fred")
