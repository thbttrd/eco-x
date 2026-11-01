"""Tests for health check endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecox_platform.api.routes.health import router


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


class TestLivenessCheck:
    """Tests for liveness endpoint."""

    def test_liveness_returns_alive(self, client: TestClient) -> None:
        """Test that liveness check returns alive status."""
        response = client.get("/live")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


class TestReadinessCheck:
    """Tests for readiness endpoint."""

    def test_readiness_when_db_healthy(self, client: TestClient) -> None:
        """Test readiness check when database is healthy."""
        mock_db_manager = MagicMock()
        mock_db_manager.health_check = AsyncMock(
            return_value={"status": "healthy", "database": "connected"}
        )

        with patch(
            "ecox_platform.api.routes.health.get_db_manager",
            return_value=mock_db_manager,
        ):
            response = client.get("/ready")

        assert response.status_code == 200
        assert response.json() == {"ready": True}

    def test_readiness_when_db_unhealthy(self, client: TestClient) -> None:
        """Test readiness check when database is unhealthy."""
        mock_db_manager = MagicMock()
        mock_db_manager.health_check = AsyncMock(
            return_value={"status": "unhealthy", "database": "disconnected"}
        )

        with patch(
            "ecox_platform.api.routes.health.get_db_manager",
            return_value=mock_db_manager,
        ):
            response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is False
        assert data["reason"] == "Database not ready"


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_when_all_healthy(self, client: TestClient) -> None:
        """Test health check when database and scheduler are healthy."""
        mock_db_manager = MagicMock()
        mock_db_manager.health_check = AsyncMock(
            return_value={"status": "healthy", "database": "connected"}
        )

        mock_fetcher = MagicMock()
        mock_fetcher.status.return_value = {"is_running": True, "workers": 5}

        with (
            patch(
                "ecox_platform.api.routes.health.get_db_manager",
                return_value=mock_db_manager,
            ),
            patch(
                "ecox_platform.api.routes.health.get_fetcher",
                return_value=mock_fetcher,
            ),
        ):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ecox-data-platform"
        assert data["database"]["status"] == "healthy"
        assert data["scheduler"]["is_running"] is True

    def test_health_when_db_unhealthy(self, client: TestClient) -> None:
        """Test health check when database is unhealthy."""
        mock_db_manager = MagicMock()
        mock_db_manager.health_check = AsyncMock(
            return_value={
                "status": "unhealthy",
                "database": "disconnected",
                "error": "Connection failed",
            }
        )

        mock_fetcher = MagicMock()
        mock_fetcher.status.return_value = {"is_running": True}

        with (
            patch(
                "ecox_platform.api.routes.health.get_db_manager",
                return_value=mock_db_manager,
            ),
            patch(
                "ecox_platform.api.routes.health.get_fetcher",
                return_value=mock_fetcher,
            ),
        ):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"

    def test_health_when_scheduler_not_initialized(self, client: TestClient) -> None:
        """Test health check when scheduler is not initialized."""
        mock_db_manager = MagicMock()
        mock_db_manager.health_check = AsyncMock(
            return_value={"status": "healthy", "database": "connected"}
        )

        with (
            patch(
                "ecox_platform.api.routes.health.get_db_manager",
                return_value=mock_db_manager,
            ),
            patch(
                "ecox_platform.api.routes.health.get_fetcher",
                side_effect=RuntimeError("Scheduler not initialized"),
            ),
        ):
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"  # DB is healthy
        assert data["scheduler"]["is_running"] is False
        assert "error" in data["scheduler"]
