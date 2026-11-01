"""Tests for datasets API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecox_platform.api.routes.datasets import router


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_dataset() -> MagicMock:
    """Create a mock dataset."""
    dataset = MagicMock()
    dataset.id = 1
    dataset.code = "nama_10_gdp"
    dataset.name = "GDP and main components"
    dataset.source = "eurostat"
    dataset.description = "Gross domestic product data"
    dataset.last_fetched = datetime(2024, 1, 15, 10, 30)
    dataset.extra_metadata = '{"dimensions": ["geo", "time"]}'
    dataset.record_count = 100  # Pre-computed record count on Dataset table
    dataset.source_url = "https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp"
    return dataset


class TestListDatasets:
    """Tests for list datasets endpoint."""

    def test_list_datasets_empty(self, app: FastAPI) -> None:
        """Test listing datasets with empty database."""
        mock_session = AsyncMock()

        # Mock total count
        mock_count = MagicMock()
        mock_count.one.return_value = 0

        # Mock datasets query
        mock_datasets = MagicMock()
        mock_datasets.all.return_value = []

        mock_session.exec = AsyncMock(side_effect=[mock_count, mock_datasets])

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["total_pages"] == 1

    def test_list_datasets_with_data(self, app: FastAPI, mock_dataset: MagicMock) -> None:
        """Test listing datasets with data."""
        mock_session = AsyncMock()

        # Mock total count
        mock_count = MagicMock()
        mock_count.one.return_value = 1

        # Mock datasets query (record_count is now on Dataset table directly)
        mock_datasets = MagicMock()
        mock_datasets.all.return_value = [mock_dataset]

        mock_session.exec = AsyncMock(side_effect=[mock_count, mock_datasets])

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["code"] == "nama_10_gdp"
        assert data["items"][0]["source"] == "eurostat"
        assert data["items"][0]["record_count"] == 100  # From mock_dataset.record_count

    def test_list_datasets_with_source_filter(self, app: FastAPI, mock_dataset: MagicMock) -> None:
        """Test listing datasets filtered by source."""
        mock_session = AsyncMock()

        mock_count = MagicMock()
        mock_count.one.return_value = 1

        # record_count is now on Dataset table directly
        mock_datasets = MagicMock()
        mock_datasets.all.return_value = [mock_dataset]

        mock_session.exec = AsyncMock(side_effect=[mock_count, mock_datasets])

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets?source=eurostat")

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["source"] == "eurostat"

    def test_list_datasets_pagination(self, app: FastAPI) -> None:
        """Test datasets pagination parameters."""
        mock_session = AsyncMock()

        mock_count = MagicMock()
        mock_count.one.return_value = 100

        mock_datasets = MagicMock()
        mock_datasets.all.return_value = []

        mock_session.exec = AsyncMock(side_effect=[mock_count, mock_datasets])

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets?page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert data["total"] == 100
        assert data["total_pages"] == 10


class TestGetDataset:
    """Tests for get dataset endpoint."""

    def test_get_dataset_not_found(self, app: FastAPI) -> None:
        """Test getting non-existent dataset returns 404."""
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None

        mock_session.exec = AsyncMock(return_value=mock_result)

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets/eurostat/unknown_dataset")

        assert response.status_code == 404
        assert "Dataset not found" in response.json()["detail"]

    def test_get_dataset_success(self, app: FastAPI, mock_dataset: MagicMock) -> None:
        """Test getting existing dataset."""
        mock_session = AsyncMock()

        # Mock dataset query (record_count is now on Dataset table directly)
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_dataset

        mock_session.exec = AsyncMock(return_value=mock_result)

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets/eurostat/nama_10_gdp")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "nama_10_gdp"
        assert data["source"] == "eurostat"
        assert data["record_count"] == 100  # From mock_dataset.record_count
        assert data["extra_metadata"]["dimensions"] == ["geo", "time"]


class TestGetDatasetValues:
    """Tests for get dataset values endpoint."""

    def test_get_values_dataset_not_found(self, app: FastAPI) -> None:
        """Test getting values for non-existent dataset."""
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None

        mock_session.exec = AsyncMock(return_value=mock_result)

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets/eurostat/unknown/values")

        assert response.status_code == 404

    def test_get_values_success(self, app: FastAPI, mock_dataset: MagicMock) -> None:
        """Test getting values for dataset."""
        mock_session = AsyncMock()

        # Mock dataset query
        mock_dataset_result = MagicMock()
        mock_dataset_result.one_or_none.return_value = mock_dataset

        # Mock total count
        mock_count = MagicMock()
        mock_count.one.return_value = 2

        # Mock values
        mock_value1 = MagicMock()
        mock_value1.geo = "FR"
        mock_value1.time_period = "2023"
        mock_value1.indicator = "B1GQ"
        mock_value1.value = 2500000.5
        mock_value1.unit = "CP_MEUR"
        mock_value1.flags = None

        mock_value2 = MagicMock()
        mock_value2.geo = "DE"
        mock_value2.time_period = "2023"
        mock_value2.indicator = "B1GQ"
        mock_value2.value = 3800000.0
        mock_value2.unit = "CP_MEUR"
        mock_value2.flags = "e"

        mock_values_result = MagicMock()
        mock_values_result.all.return_value = [
            mock_value1,
            mock_value2,
        ]

        mock_session.exec = AsyncMock(
            side_effect=[mock_dataset_result, mock_count, mock_values_result]
        )

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets/eurostat/nama_10_gdp/values")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2
        assert data["items"][0]["geo"] == "FR"
        assert data["items"][1]["geo"] == "DE"
        assert data["dataset_code"] == "nama_10_gdp"

    def test_get_values_with_filters(self, app: FastAPI, mock_dataset: MagicMock) -> None:
        """Test getting values with geo/time filters."""
        mock_session = AsyncMock()

        mock_dataset_result = MagicMock()
        mock_dataset_result.one_or_none.return_value = mock_dataset

        mock_count = MagicMock()
        mock_count.one.return_value = 1

        mock_value = MagicMock()
        mock_value.geo = "FR"
        mock_value.time_period = "2023"
        mock_value.indicator = "B1GQ"
        mock_value.value = 2500000.5
        mock_value.unit = "CP_MEUR"
        mock_value.flags = None

        mock_values_result = MagicMock()
        mock_values_result.all.return_value = [mock_value]

        mock_session.exec = AsyncMock(
            side_effect=[mock_dataset_result, mock_count, mock_values_result]
        )

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets/eurostat/nama_10_gdp/values?geo=FR&time_period=2023")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["geo"] == "FR"


class TestGetDimensionValues:
    """Tests for get dimension values endpoint."""

    def test_invalid_dimension(self, app: FastAPI) -> None:
        """Test getting invalid dimension returns 400."""
        mock_session = AsyncMock()

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets/eurostat/test/dimensions/invalid_dim")

        assert response.status_code == 400
        assert "Invalid dimension" in response.json()["detail"]

    def test_get_dimension_dataset_not_found(self, app: FastAPI) -> None:
        """Test getting dimension for non-existent dataset."""
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None

        mock_session.exec = AsyncMock(return_value=mock_result)

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/datasets/eurostat/unknown/dimensions/geo")

        assert response.status_code == 404

    def test_get_dimension_geo_values(self, app: FastAPI, mock_dataset: MagicMock) -> None:
        """Test getting geo dimension values.

        Note: The route uses session.exec for dataset lookup and session.execute
        for dimension values query (due to distinct/order_by requirements).
        """
        mock_session = AsyncMock()

        # Mock dataset query (uses session.exec)
        mock_dataset_result = MagicMock()
        mock_dataset_result.one_or_none.return_value = mock_dataset
        mock_session.exec = AsyncMock(return_value=mock_dataset_result)

        # Mock dimension values query (uses session.execute for raw SQL features)
        mock_dim_result = MagicMock()
        mock_dim_result.all.return_value = [("DE",), ("FR",), ("IT",)]
        mock_session.execute = AsyncMock(return_value=mock_dim_result)

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/datasets/eurostat/nama_10_gdp/dimensions/geo")

        # Verify route executes successfully
        assert response.status_code == 200
        # Verify both queries were made
        assert mock_session.exec.call_count == 1
        assert mock_session.execute.call_count == 1
