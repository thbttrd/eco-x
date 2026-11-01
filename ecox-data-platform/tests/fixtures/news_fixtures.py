"""Fixtures for Epic 5: Economic News Aggregation tests.

These fixtures provide mock objects and test data for news-related BDD tests.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def news_config() -> dict[str, Any]:
    """Mutable configuration dict for news settings."""
    return {
        "default_fetch_interval_minutes": 60,
        "max_concurrent_fetches": 3,
        "rate_limit_per_domain": 2.0,
        "store_raw_html": False,
        "fetch_on_startup": True,
    }


@pytest.fixture
def mock_news_worker() -> MagicMock:
    """Create a mock news worker for testing."""
    worker = MagicMock()
    worker.status.return_value = {
        "is_running": False,
        "last_activity": None,
        "sources_fetched": 0,
        "sources_failed": 0,
        "articles_found": 0,
        "articles_new": 0,
        "current_source": None,
        "config": {},
    }
    worker.run_cycle = AsyncMock()
    return worker


@pytest.fixture
def mock_http_response() -> MagicMock:
    """Create a mock HTTP response for source fetching."""
    response = MagicMock()
    response.text = (
        "<html><body><article class='item'><a href='/news/1'>Article 1</a></article></body></html>"
    )
    response.status_code = 200
    return response


@pytest.fixture
def sse_events() -> list[dict]:
    """Collect SSE events during tests."""
    return []


@pytest.fixture
def mock_news_service() -> MagicMock:
    """Create a mock news service for testing."""
    service = MagicMock()
    service.get_categories_with_sources = AsyncMock(return_value=[])
    service.import_from_config = AsyncMock()
    return service


@pytest.fixture
def sample_news_categories() -> list[dict[str, Any]]:
    """Sample news categories for testing."""
    return [
        {
            "id": 1,
            "name": "Central Banks",
            "sources": [
                {
                    "id": 1,
                    "title": "ECB",
                    "url": "https://ecb.europa.eu",
                    "is_active": True,
                    "last_fetched_at": datetime.now(UTC).isoformat(),
                    "last_fetch_status": "success",
                    "last_fetch_error": None,
                    "article_count": 5,
                },
                {
                    "id": 2,
                    "title": "Fed",
                    "url": "https://federalreserve.gov",
                    "is_active": True,
                    "last_fetched_at": datetime.now(UTC).isoformat(),
                    "last_fetch_status": "success",
                    "last_fetch_error": None,
                    "article_count": 3,
                },
            ],
            "source_count": 2,
            "total_articles": 8,
        },
        {
            "id": 2,
            "name": "National Statistics",
            "sources": [
                {
                    "id": 3,
                    "title": "Eurostat",
                    "url": "https://ec.europa.eu/eurostat",
                    "is_active": True,
                    "last_fetched_at": None,
                    "last_fetch_status": None,
                    "last_fetch_error": None,
                    "article_count": 0,
                },
            ],
            "source_count": 1,
            "total_articles": 0,
        },
    ]


@pytest.fixture
def sample_news_articles() -> list[dict[str, Any]]:
    """Sample news articles for testing."""
    now = datetime.now(UTC)
    return [
        {
            "id": 1,
            "title": "ECB raises interest rates",
            "url": "https://ecb.europa.eu/news/1",
            "source_id": 1,
            "source_title": "ECB",
            "published_at": now.isoformat(),
            "discovered_at": now.isoformat(),
            "content_preview": "The ECB announced today...",
        },
        {
            "id": 2,
            "title": "Fed holds steady",
            "url": "https://federalreserve.gov/news/1",
            "source_id": 2,
            "source_title": "Fed",
            "published_at": now.isoformat(),
            "discovered_at": now.isoformat(),
            "content_preview": "The Federal Reserve...",
        },
    ]
