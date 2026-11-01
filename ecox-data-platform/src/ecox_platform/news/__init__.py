"""News aggregation module for fetching and parsing economic news.

This module provides:
- Configuration loading from news.yaml
- Article parsing (RSS, CSS selectors, XPath)
- Background fetching and storage
- API endpoints for news browsing
"""

from ecox_platform.news.config import (
    NewsSettings,
    SourceConfig,
    load_news_config,
)
from ecox_platform.news.events import (
    NewsEvent,
    NewsEventManager,
    get_event_manager,
    publish_news_event,
)
from ecox_platform.news.parser import NewsParser, ParsedArticle
from ecox_platform.news.repository import NewsRepository
from ecox_platform.news.service import FetchResult, ImportResult, NewsService
from ecox_platform.news.worker import (
    NewsWorker,
    get_news_worker,
    start_news_worker,
    stop_news_worker,
)

__all__ = [
    "FetchResult",
    "ImportResult",
    "NewsEvent",
    "NewsEventManager",
    "NewsParser",
    "NewsRepository",
    "NewsService",
    "NewsSettings",
    "NewsWorker",
    "ParsedArticle",
    "SourceConfig",
    "get_event_manager",
    "get_news_worker",
    "load_news_config",
    "publish_news_event",
    "start_news_worker",
    "stop_news_worker",
]
