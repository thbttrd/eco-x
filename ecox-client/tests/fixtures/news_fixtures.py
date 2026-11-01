"""Fixtures for Epic 5: Economic News Aggregation UI tests.

These fixtures provide mock data for news-related BDD tests.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest


@pytest.fixture
def sample_news_categories() -> list[dict[str, Any]]:
    """Sample news categories for testing."""
    now = datetime.now(UTC)
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
                    "last_fetched_at": now.isoformat(),
                    "last_fetch_status": "success",
                    "last_fetch_error": None,
                    "article_count": 5,
                },
                {
                    "id": 2,
                    "title": "Fed",
                    "url": "https://federalreserve.gov",
                    "is_active": True,
                    "last_fetched_at": now.isoformat(),
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
def sample_news_articles() -> dict[str, Any]:
    """Sample news articles response for testing."""
    now = datetime.now(UTC)
    return {
        "articles": [
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
                "published_at": (now - timedelta(hours=2)).isoformat(),
                "discovered_at": (now - timedelta(hours=2)).isoformat(),
                "content_preview": "The Federal Reserve...",
            },
        ],
        "total": 2,
        "limit": 10,
        "offset": 0,
    }


@pytest.fixture
def sample_news_status() -> dict[str, Any]:
    """Sample news worker status for testing."""
    return {
        "is_running": False,
        "last_activity": None,
        "sources_fetched": 0,
        "sources_failed": 0,
        "articles_found": 0,
        "articles_new": 0,
        "current_source": None,
        "config": {},
    }


@pytest.fixture
def sample_news_status_running() -> dict[str, Any]:
    """Sample news worker status when running."""
    return {
        "is_running": True,
        "last_activity": datetime.now(UTC).isoformat(),
        "sources_fetched": 3,
        "sources_failed": 0,
        "articles_found": 15,
        "articles_new": 10,
        "current_source": "ECB",
        "config": {},
    }
