"""Pytest configuration and fixtures for ecox-data-platform tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.infrastructure.cache import Cache

# Import fixtures from fixtures module (makes them available in all tests)
pytest_plugins = [
    "tests.fixtures.nbs_fixtures",
    "tests.fixtures.ons_fixtures",
    "tests.fixtures.oecd_fixtures",
    "tests.fixtures.news_fixtures",
]


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with in-memory SQLite.

    Uses StaticPool to ensure connection is reused within the test.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Yield session for test
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def test_cache() -> Cache:
    """Create a test cache instance with short TTL."""
    return Cache(ttl_seconds=60)


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client for testing."""
    client = MagicMock()
    client.get = AsyncMock()
    client.get_json = AsyncMock()
    client.post = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def sample_eurostat_jsonstat() -> dict:
    """Sample JSON-stat 2.0 response from Eurostat."""
    return {
        "version": "2.0",
        "class": "dataset",
        "label": "GDP and main components",
        "source": "Eurostat",
        "updated": "2023-12-15T11:00:00",
        "id": ["geo", "time", "na_item", "unit"],
        "size": [2, 2, 1, 1],
        "dimension": {
            "geo": {
                "label": "Geopolitical entity",
                "category": {
                    "index": {"EU27_2020": 0, "FR": 1},
                    "label": {
                        "EU27_2020": "European Union - 27 countries",
                        "FR": "France",
                    },
                },
            },
            "time": {
                "label": "Time",
                "category": {
                    "index": {"2020": 0, "2021": 1},
                    "label": {"2020": "2020", "2021": "2021"},
                },
            },
            "na_item": {
                "label": "National accounts indicator",
                "category": {
                    "index": {"B1GQ": 0},
                    "label": {"B1GQ": "Gross domestic product at market prices"},
                },
            },
            "unit": {
                "label": "Unit of measure",
                "category": {
                    "index": {"CP_MEUR": 0},
                    "label": {"CP_MEUR": "Current prices, million euro"},
                },
            },
        },
        "value": {
            "0": 13200000.5,
            "1": 13500000.2,
            "2": 2300000.1,
            "3": 2400000.3,
        },
        "status": {"1": "e"},
    }


# ==============================================================================
# BDD Context Fixtures
# ==============================================================================


@pytest.fixture
def scenario_context() -> dict:
    """Shared mutable context for BDD scenarios.

    Use this to pass data between Given/When/Then steps.
    """
    return {}


@pytest.fixture
def api_response() -> dict:
    """Store API response data for assertion steps.

    Keys:
        - status_code: HTTP status code
        - json: Parsed JSON response body
        - text: Raw text response
        - headers: Response headers
    """
    return {}


@pytest.fixture
def sample_eurostat_toc_with_duplicates() -> list[dict]:
    """Sample Eurostat TOC entries with duplicates (same dataset in multiple categories)."""
    return [
        {"code": "nama_10_gdp", "name": "GDP", "last_update": "10.12.2024", "values_count": 50000},
        {"code": "nama_10_gdp", "name": "GDP", "last_update": "10.12.2024", "values_count": 50000},
        {
            "code": "prc_hicp_midx",
            "name": "HICP",
            "last_update": "15.12.2024",
            "values_count": 100000,
        },
        {
            "code": "prc_hicp_midx",
            "name": "HICP",
            "last_update": "15.12.2024",
            "values_count": 100000,
        },
        {
            "code": "prc_hicp_midx",
            "name": "HICP",
            "last_update": "15.12.2024",
            "values_count": 100000,
        },
        {
            "code": "une_rt_m",
            "name": "Unemployment",
            "last_update": "12.12.2024",
            "values_count": 75000,
        },
    ]


@pytest.fixture
def sample_eurostat_toc_unique() -> list[dict]:
    """Sample Eurostat TOC entries without duplicates."""
    return [
        {"code": "nama_10_gdp", "name": "GDP", "last_update": "10.12.2024", "values_count": 50000},
        {
            "code": "prc_hicp_midx",
            "name": "HICP",
            "last_update": "15.12.2024",
            "values_count": 100000,
        },
        {
            "code": "une_rt_m",
            "name": "Unemployment",
            "last_update": "12.12.2024",
            "values_count": 75000,
        },
    ]


@pytest.fixture
def sample_toc_different_last_updates() -> list[dict]:
    """Sample TOC entries with same code but different last_update dates."""
    return [
        {"code": "A", "name": "Old version", "last_update": "01.12.2024"},
        {"code": "A", "name": "New version", "last_update": "15.12.2024"},
        {"code": "A", "name": "Middle version", "last_update": "10.12.2024"},
    ]


@pytest.fixture
def sample_toc_with_none_dates() -> list[dict]:
    """Sample TOC entries with None last_update."""
    return [
        {"code": "A", "name": "No date", "last_update": None},
        {"code": "A", "name": "Has date", "last_update": "01.12.2024"},
    ]


@pytest.fixture
def sample_fred_response() -> dict:
    """Sample FRED API response."""
    return {
        "realtime_start": "2023-01-01",
        "realtime_end": "2023-12-31",
        "observation_start": "2022-01-01",
        "observation_end": "2022-12-31",
        "units": "lin",
        "output_type": 1,
        "file_type": "json",
        "order_by": "observation_date",
        "sort_order": "asc",
        "count": 4,
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
                "value": "25500.0",
            },
            {
                "realtime_start": "2023-01-01",
                "realtime_end": "2023-12-31",
                "date": "2022-07-01",
                "value": "26000.0",
            },
            {
                "realtime_start": "2023-01-01",
                "realtime_end": "2023-12-31",
                "date": "2022-10-01",
                "value": "26500.0",
            },
        ],
    }
