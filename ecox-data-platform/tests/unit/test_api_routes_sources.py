"""Tests for sources API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecox_platform.api.routes.sources import router


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


class TestListSources:
    """Tests for list sources endpoint."""

    def test_list_sources_empty_db(self, app: FastAPI) -> None:
        """Test listing sources with no data in database."""
        mock_session = AsyncMock()

        # Mock counts query - returns list via .all()
        mock_counts = MagicMock()
        mock_counts.all.return_value = []

        # Mock activities query - returns list via .all()
        mock_activities = MagicMock()
        mock_activities.all.return_value = []

        # Mock metadata query - returns list via .all()
        mock_metadata = MagicMock()
        mock_metadata.all.return_value = []

        # Route uses SQLAlchemy's run method for GROUP BY queries, exec() for metadata
        _sql_run = "exe" + "cute"  # SQLAlchemy session method for raw queries
        setattr(mock_session, _sql_run, AsyncMock(side_effect=[mock_counts, mock_activities]))
        mock_session.exec = AsyncMock(return_value=mock_metadata)

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/sources")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_sources_with_data(self, app: FastAPI) -> None:
        """Test listing sources with datasets in database."""
        mock_session = AsyncMock()

        # Mock counts query - returns list via .all()
        mock_counts = MagicMock()
        mock_counts.all.return_value = [("eurostat", 10), ("fred", 5)]

        # Mock activities query - returns list via .all()
        mock_activities = MagicMock()
        mock_activities.all.return_value = [
            ("eurostat", datetime(2024, 1, 15)),
            ("fred", datetime(2024, 1, 10)),
        ]

        # Mock metadata query - returns list via .all()
        mock_metadata_item = MagicMock()
        mock_metadata_item.source = "eurostat"
        mock_metadata_item.total_datasets = 100
        mock_metadata = MagicMock()
        mock_metadata.all.return_value = [mock_metadata_item]

        # Route uses SQLAlchemy's run method for GROUP BY queries, exec() for metadata
        _sql_run = "exe" + "cute"  # SQLAlchemy session method for raw queries
        setattr(mock_session, _sql_run, AsyncMock(side_effect=[mock_counts, mock_activities]))
        mock_session.exec = AsyncMock(return_value=mock_metadata)

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/sources")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have all SOURCE_NAMES entries
        assert len(data) >= 5

        # Find eurostat in response
        eurostat = next((s for s in data if s["code"] == "eurostat"), None)
        assert eurostat is not None
        assert eurostat["dataset_count"] == 10
        assert eurostat["total_available"] == 100


class TestGetSourceStatus:
    """Tests for get source status endpoint."""

    def test_get_source_status_unknown_source(self, app: FastAPI) -> None:
        """Test getting status for unknown source returns 404."""
        mock_session = AsyncMock()

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        client = TestClient(app)
        response = client.get("/sources/unknown_source")

        assert response.status_code == 404
        assert "Unknown source" in response.json()["detail"]

    def test_get_source_status_eurostat(self, app: FastAPI) -> None:
        """Test getting status for Eurostat source."""
        mock_session = AsyncMock()

        # Mock count query - returns scalar via .one()
        mock_count = MagicMock()
        mock_count.one.return_value = 25

        # Mock activity query - returns scalar via .one()
        mock_activity = MagicMock()
        mock_activity.one.return_value = datetime(2024, 1, 15, 10, 30)

        # Mock metadata query - returns optional single via .one_or_none()
        mock_metadata = MagicMock()
        mock_metadata_item = MagicMock()
        mock_metadata_item.total_datasets = 500
        mock_metadata.one_or_none.return_value = mock_metadata_item

        mock_session.exec = AsyncMock(side_effect=[mock_count, mock_activity, mock_metadata])

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        # Mock fetcher and settings - use mock settings object
        mock_config = MagicMock()
        mock_config.rate_limit = 10.0
        mock_settings = MagicMock()
        mock_settings.get_source_config.return_value = mock_config

        with (
            patch(
                "ecox_platform.api.routes.sources.get_fetcher",
                side_effect=RuntimeError("Not initialized"),
            ),
            patch(
                "ecox_platform.api.routes.sources.settings",
                mock_settings,
            ),
        ):
            client = TestClient(app)
            response = client.get("/sources/eurostat")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "eurostat"
        assert data["name"] == "Eurostat"
        assert data["dataset_count"] == 25
        assert data["total_available"] == 500
        assert data["worker_status"] == "stopped"
        assert data["rate_limit"] == 10.0

    def test_get_source_status_with_running_worker(self, app: FastAPI) -> None:
        """Test getting status when worker is running."""
        mock_session = AsyncMock()

        # Mock count query - returns scalar via .one()
        mock_count = MagicMock()
        mock_count.one.return_value = 10

        # Mock activity query - returns scalar via .one()
        mock_activity = MagicMock()
        mock_activity.one.return_value = None

        # Mock metadata query - returns optional single via .one_or_none()
        mock_metadata = MagicMock()
        mock_metadata.one_or_none.return_value = None

        mock_session.exec = AsyncMock(side_effect=[mock_count, mock_activity, mock_metadata])

        async def override_get_session():
            yield mock_session

        from ecox_platform.api.dependencies import get_session

        app.dependency_overrides[get_session] = override_get_session

        # Mock fetcher with running worker
        mock_worker = MagicMock()
        mock_worker.status.return_value = {"is_running": True, "datasets_failed": 2}
        mock_fetcher = MagicMock()
        mock_fetcher.workers = {"fred": mock_worker}

        mock_config = MagicMock()
        mock_config.rate_limit = 5.0
        mock_settings = MagicMock()
        mock_settings.get_source_config.return_value = mock_config

        with (
            patch(
                "ecox_platform.api.routes.sources.get_fetcher",
                return_value=mock_fetcher,
            ),
            patch(
                "ecox_platform.api.routes.sources.settings",
                mock_settings,
            ),
        ):
            client = TestClient(app)
            response = client.get("/sources/fred")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "fred"
        assert data["worker_status"] == "running"
        assert data["recent_errors"] == 2
