"""Unit tests for news API routes.

Tests cover:
- Category listing endpoint
- Entry listing endpoints
- Section endpoints
- Fetch logs endpoint
- Dependency injection override pattern
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecox_platform.api.routes.news import (
    get_news_repository,
    get_news_service,
    router,
)
from ecox_platform.news import NewsRepository, NewsService


class TestNewsRoutes:
    """Tests for news API routes."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create mock repository."""
        repo = MagicMock(spec=NewsRepository)
        repo.get_entries = AsyncMock(return_value=([], 0))
        repo.get_section_by_id = AsyncMock(return_value=None)
        repo.get_fetch_logs = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        """Create mock service."""
        service = MagicMock(spec=NewsService)
        service.get_categories_with_sources_and_sections = AsyncMock(return_value=[])
        return service

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        session = AsyncMock()
        session.exec = AsyncMock()
        return session

    @pytest.fixture
    def app(
        self,
        mock_repository: MagicMock,
        mock_service: MagicMock,
        mock_session: AsyncMock,
    ) -> FastAPI:
        """Create test FastAPI app with dependency overrides."""
        app = FastAPI()
        app.include_router(router)

        # Override dependencies for testing
        app.dependency_overrides[get_news_repository] = lambda: mock_repository
        app.dependency_overrides[get_news_service] = lambda: mock_service

        # Mock the database session dependency
        from ecox_platform.api.dependencies import get_session

        async def mock_get_session():
            yield mock_session

        app.dependency_overrides[get_session] = mock_get_session

        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create test client."""
        return TestClient(app)


class TestListCategories(TestNewsRoutes):
    """Tests for GET /categories endpoint."""

    def test_list_categories_empty(self, client: TestClient, mock_service: MagicMock) -> None:
        """Test listing categories when none exist."""
        mock_service.get_categories_with_sources_and_sections.return_value = []

        response = client.get("/news/categories")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_categories_with_data(self, client: TestClient, mock_service: MagicMock) -> None:
        """Test listing categories with sources and sections."""
        # Use AsyncMock to ensure proper async behavior
        mock_service.get_categories_with_sources_and_sections = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "name": "Central Banks",
                    "fetch_interval_minutes": 60,
                    "sources": [
                        {
                            "id": 1,
                            "title": "ECB",
                            "description": "European Central Bank",
                            "is_active": True,
                            "sections": [
                                {
                                    "id": 1,
                                    "title": "Press Releases",
                                    "url": "https://ecb.europa.eu/press",
                                    "is_active": True,
                                    "last_fetched_at": None,
                                    "last_fetch_status": None,
                                    "last_fetch_error": None,
                                    "entry_count": 5,
                                }
                            ],
                            "section_count": 1,
                            "entry_count": 5,
                        }
                    ],
                    "source_count": 1,
                    "section_count": 1,
                    "total_entries": 5,
                }
            ]
        )

        response = client.get("/news/categories")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Central Banks"
        assert len(data[0]["sources"]) == 1
        assert data[0]["sources"][0]["title"] == "ECB"


class TestListEntries(TestNewsRoutes):
    """Tests for GET /entries endpoint."""

    def test_list_entries_empty(self, client: TestClient, mock_repository: MagicMock) -> None:
        """Test listing entries when none exist."""
        mock_repository.get_entries.return_value = ([], 0)

        response = client.get("/news/entries")

        assert response.status_code == 200
        data = response.json()
        assert data["entries"] == []
        assert data["total"] == 0

    def test_list_entries_with_pagination(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test entry listing respects pagination params."""
        response = client.get("/news/entries?limit=5&offset=10")

        assert response.status_code == 200
        mock_repository.get_entries.assert_called_once()
        call_kwargs = mock_repository.get_entries.call_args.kwargs
        assert call_kwargs["limit"] == 5
        assert call_kwargs["offset"] == 10

    def test_list_entries_with_filters(
        self, client: TestClient, mock_repository: MagicMock
    ) -> None:
        """Test entry listing respects filter params."""
        response = client.get("/news/entries?section_id=1&search=test")

        assert response.status_code == 200
        call_kwargs = mock_repository.get_entries.call_args.kwargs
        assert call_kwargs["section_id"] == 1
        assert call_kwargs["search"] == "test"


class TestListSectionEntries(TestNewsRoutes):
    """Tests for GET /sections/{section_id}/entries endpoint."""

    def test_section_not_found(self, client: TestClient, mock_repository: MagicMock) -> None:
        """Test 404 when section doesn't exist."""
        mock_repository.get_section_by_id.return_value = None

        response = client.get("/news/sections/999/entries")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_section_entries_found(self, client: TestClient, mock_repository: MagicMock) -> None:
        """Test listing entries for existing section."""
        from ecox_shared.models import NewsSection

        mock_section = NewsSection(
            id=1,
            url="https://example.com/feed",
            title="Example Feed",
            source_id=1,
        )
        mock_repository.get_section_by_id.return_value = mock_section
        mock_repository.get_entries.return_value = ([], 0)

        response = client.get("/news/sections/1/entries")

        assert response.status_code == 200


class TestGetFetchLogs(TestNewsRoutes):
    """Tests for GET /logs endpoint."""

    def test_get_logs_empty(self, client: TestClient, mock_repository: MagicMock) -> None:
        """Test getting logs when none exist."""
        mock_repository.get_fetch_logs.return_value = []

        response = client.get("/news/logs")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_logs_with_filter(self, client: TestClient, mock_repository: MagicMock) -> None:
        """Test getting logs filtered by section."""
        response = client.get("/news/logs?section_id=1")

        assert response.status_code == 200
        call_kwargs = mock_repository.get_fetch_logs.call_args.kwargs
        assert call_kwargs["section_id"] == 1

    def test_get_logs_respects_limit(self, client: TestClient, mock_repository: MagicMock) -> None:
        """Test getting logs respects limit param."""
        response = client.get("/news/logs?limit=100")

        assert response.status_code == 200
        call_kwargs = mock_repository.get_fetch_logs.call_args.kwargs
        assert call_kwargs["limit"] == 100


class TestDependencyInjection(TestNewsRoutes):
    """Tests verifying dependency injection works correctly."""

    def test_repository_injectable(self, client: TestClient, mock_repository: MagicMock) -> None:
        """Verify repository is properly injected."""
        response = client.get("/news/entries")
        assert response.status_code == 200
        mock_repository.get_entries.assert_called_once()

    def test_service_injectable(self, client: TestClient, mock_service: MagicMock) -> None:
        """Verify service is properly injected."""
        response = client.get("/news/categories")
        assert response.status_code == 200
        mock_service.get_categories_with_sources_and_sections.assert_called_once()
