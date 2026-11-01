"""Pytest configuration and fixtures for ecox-client tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Import models to ensure they are registered with SQLModel metadata
import ecox_client.models  # noqa: F401

# Import fixtures from fixtures module (makes them available in all tests)
pytest_plugins = ["tests.fixtures.news_fixtures"]


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Shared engine for BDD tests to avoid table creation issues
_test_engine: AsyncEngine | None = None


async def _get_test_engine() -> AsyncEngine:
    """Get or create a shared test engine."""
    global _test_engine
    if _test_engine is None:
        _test_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with _test_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    return _test_engine


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with in-memory SQLite.

    Uses StaticPool to ensure connection is reused within the test.
    Each test gets a clean slate by truncating tables before the test.
    """
    engine = await _get_test_engine()

    # Truncate all tables before each test for isolation
    async with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(table.delete())

    # Yield session for test
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Clean up test engine at session end."""
    global _test_engine
    if _test_engine is not None:
        # Use asyncio.run() which handles creating/cleaning up the event loop
        asyncio.run(_test_engine.dispose())
        _test_engine = None


@pytest.fixture
def mock_platform_response() -> dict:
    """Sample platform API response for sources."""
    return {
        "items": [
            {
                "code": "eurostat",
                "name": "Eurostat",
                "dataset_count": 10,
                "total_available": 100,
            },
            {
                "code": "fred",
                "name": "FRED",
                "dataset_count": 5,
                "total_available": 50,
            },
        ],
        "total": 2,
        "page": 1,
        "page_size": 20,
    }


@pytest.fixture
def mock_dataset_response() -> dict:
    """Sample platform API response for dataset details."""
    return {
        "id": 1,
        "code": "nama_10_gdp",
        "name": "GDP and main components",
        "source": "eurostat",
        "description": "Gross domestic product data",
        "last_fetched": "2024-01-15T10:30:00",
        "record_count": 250,
        "extra_metadata": {"dimensions": ["geo", "time"]},
    }


# ==============================================================================
# BDD Test Fixtures
# ==============================================================================


@pytest.fixture
def scenario_context() -> dict[str, Any]:
    """Mutable context dict shared between BDD steps."""
    return {}


@pytest.fixture
def mock_platform_client() -> AsyncMock:
    """Create a mock platform client for BDD tests."""
    mock = AsyncMock()
    # Set up default return values
    mock.list_sources.return_value = []
    mock.list_datasets.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "total_pages": 0,
    }
    mock.get_dataset.return_value = {}
    mock.list_fetch_logs.return_value = {"items": []}
    mock.health.return_value = {"status": "healthy"}
    # News-related mock methods (use actual method names from platform_client.py)
    mock.list_news_categories.return_value = []
    mock.list_news_entries.return_value = {
        "entries": [],
        "total": 0,
        "limit": 10,
        "offset": 0,
    }
    mock.list_section_entries.return_value = {
        "entries": [],
        "total": 0,
        "limit": 100,
        "offset": 0,
    }
    mock.get_entry.return_value = {}
    mock.get_news_status.return_value = {
        "is_running": False,
        "sections_fetched": 0,
        "sections_failed": 0,
        "entries_found": 0,
        "entries_new": 0,
        "current_section": None,
    }
    mock.trigger_news_refresh.return_value = {"status": "started"}
    mock.refresh_section.return_value = {"status": "started"}
    return mock


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Create a mock database manager that uses the shared test engine."""
    mock = MagicMock()

    @asynccontextmanager
    async def mock_get_session():
        engine = await _get_test_engine()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    mock.get_session = mock_get_session
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    mock.create_all_tables = AsyncMock()
    return mock


@pytest.fixture
def api_client(
    mock_platform_client: AsyncMock,
    mock_db_manager: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies."""
    with (
        patch(
            "ecox_client.api.routes.ui.get_platform_client",
            return_value=mock_platform_client,
        ),
        patch(
            "ecox_client.api.routes.ui.get_db_manager",
            return_value=mock_db_manager,
        ),
        patch(
            "ecox_client.main.get_platform_client",
            return_value=mock_platform_client,
        ),
        patch(
            "ecox_client.main.init_db_manager",
            return_value=mock_db_manager,
        ),
        patch(
            "ecox_client.main.close_platform_client",
            new_callable=AsyncMock,
        ),
        patch(
            "ecox_client.main.close_db_manager",
            new_callable=AsyncMock,
        ),
    ):
        from ecox_client.main import app

        with TestClient(app) as client:
            yield client
