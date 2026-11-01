"""News configuration loader.

Loads news sources from config/news.yaml with support for:
- Global settings (fetch interval, concurrency, rate limiting)
- Category-level overrides
- Source-level overrides
- Section-level configuration (US-5.9)
- Parse selectors and comments

Supports both new hierarchical format (with sections) and legacy flat format.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import structlog
import yaml

logger = structlog.get_logger()

# Defaults
DEFAULT_FETCH_INTERVAL_MINUTES = 60
MIN_FETCH_INTERVAL_MINUTES = 15
MAX_FETCH_INTERVAL_MINUTES = 1440  # 24 hours
DEFAULT_MAX_CONCURRENT = 3
DEFAULT_RATE_LIMIT = 2.0
DEFAULT_STARTUP_DELAY = 30
DEFAULT_RETENTION_MONTHS = 12


def _validate_url(url: str, context: str) -> None:
    """Validate that a URL is well-formed.

    Args:
        url: URL to validate
        context: Context for error message (e.g., "section 'ECB Decisions'")

    Raises:
        ValueError: If URL is invalid
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL in {context}: {url}")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL must use http or https in {context}: {url}")


@dataclass
class SectionConfig:
    """Configuration for a section within a news source (US-5.9).

    Sections represent specific pages/feeds within a source
    (e.g., "Press Releases", "Monetary Policy Decisions").
    """

    title: str
    url: str
    enabled: bool = True
    parse_selector: str | None = None
    parse_comment: str | None = None
    fetch_interval_minutes: int | None = None


@dataclass
class SourceConfig:
    """Configuration for a news source container.

    Sources are conceptual groupings (e.g., "ECB Monetary Policy") that contain
    one or more sections. Each section has its own URL and fetch configuration.

    For backward compatibility, sources with a direct URL (no sections) are
    converted to a single section with the source's title.
    """

    title: str
    description: str | None = None
    enabled: bool = True
    parse_selector: str | None = None  # Default for sections without parse_selector
    fetch_interval_minutes: int | None = None
    sections: list[SectionConfig] = field(default_factory=list)

    # DEPRECATED: Direct URL on source (legacy format)
    # When present, a single section is auto-created
    url: str | None = None


@dataclass
class CategoryConfig:
    """Configuration for a news category."""

    name: str
    enabled: bool = True
    fetch_interval_minutes: int | None = None
    sources: list[SourceConfig] = field(default_factory=list)


@dataclass
class NewsSettings:
    """Global news fetching settings."""

    default_fetch_interval_minutes: int = DEFAULT_FETCH_INTERVAL_MINUTES
    max_concurrent_fetches: int = DEFAULT_MAX_CONCURRENT
    rate_limit_per_domain: float = DEFAULT_RATE_LIMIT
    fetch_on_startup: bool = True
    startup_delay_seconds: int = DEFAULT_STARTUP_DELAY
    store_raw_html: bool = False
    store_full_content: bool = True  # US-5.10: Store full article text
    article_retention_months: int = DEFAULT_RETENTION_MONTHS
    content_fetch_timeout: int = 15  # Timeout in seconds for fetching full content
    content_fetch_concurrency: int = 5  # Max concurrent content fetches per section

    def get_effective_interval(
        self,
        section_interval: int | None,
        source_interval: int | None,
        category_interval: int | None,
    ) -> int:
        """Get effective fetch interval with override hierarchy.

        Priority: section > source > category > global default
        Clamps result to [MIN_FETCH_INTERVAL, MAX_FETCH_INTERVAL].
        """
        interval = (
            section_interval
            or source_interval
            or category_interval
            or self.default_fetch_interval_minutes
        )
        return max(
            MIN_FETCH_INTERVAL_MINUTES,
            min(interval, MAX_FETCH_INTERVAL_MINUTES),
        )


def _get_config_path() -> Path:
    """Get path to news.yaml config file."""
    # Check for ECOX_NEWS_CONFIG env var first
    if config_path := os.environ.get("ECOX_NEWS_CONFIG"):
        return Path(config_path)

    # Default to config/news.yaml relative to project root
    # Try multiple locations for flexibility
    candidates = [
        Path("config/news.yaml"),  # Relative to CWD
        Path(__file__).parent.parent.parent.parent.parent
        / "config"
        / "news.yaml",  # Relative to source
    ]

    for path in candidates:
        if path.exists():
            return path

    # Return default even if doesn't exist (caller handles missing file)
    return candidates[0]


def _parse_settings(data: dict[str, Any]) -> NewsSettings:
    """Parse settings section from config."""
    settings_data = data.get("settings", {})

    # Check for environment variable override
    env_interval = os.environ.get("ECOX_NEWS_FETCH_INTERVAL_MINUTES")
    if env_interval:
        try:
            settings_data["default_fetch_interval_minutes"] = int(env_interval)
        except ValueError:
            logger.warning(
                "Invalid ECOX_NEWS_FETCH_INTERVAL_MINUTES",
                value=env_interval,
            )

    return NewsSettings(
        default_fetch_interval_minutes=settings_data.get(
            "default_fetch_interval_minutes", DEFAULT_FETCH_INTERVAL_MINUTES
        ),
        max_concurrent_fetches=settings_data.get("max_concurrent_fetches", DEFAULT_MAX_CONCURRENT),
        rate_limit_per_domain=settings_data.get("rate_limit_per_domain", DEFAULT_RATE_LIMIT),
        fetch_on_startup=settings_data.get("fetch_on_startup", True),
        startup_delay_seconds=settings_data.get("startup_delay_seconds", DEFAULT_STARTUP_DELAY),
        store_raw_html=settings_data.get("store_raw_html", False),
        store_full_content=settings_data.get("store_full_content", True),
        article_retention_months=settings_data.get(
            "article_retention_months", DEFAULT_RETENTION_MONTHS
        ),
    )


def _parse_section(
    section_data: dict[str, Any],
    default_parse_selector: str | None = None,
) -> SectionConfig:
    """Parse a single section from config.

    Args:
        section_data: Section configuration dict
        default_parse_selector: Default selector inherited from source

    Raises:
        ValueError: If section URL is invalid
    """
    url = section_data["url"]
    title = section_data["title"]

    # Validate URL format
    _validate_url(url, f"section '{title}'")

    return SectionConfig(
        title=title,
        url=url,
        enabled=section_data.get("enabled", True),
        parse_selector=section_data.get("parse_selector") or default_parse_selector,
        parse_comment=section_data.get("parse_comment"),
        fetch_interval_minutes=section_data.get("fetch_interval_minutes"),
    )


def _parse_source(source_data: dict[str, Any]) -> SourceConfig:
    """Parse a source with sections or legacy URL format.

    Supports both:
    - New format: source with `sections` array
    - Legacy format: source with direct `url` (auto-creates single section)
    """
    # Get source-level parse_selector as default for sections
    default_selector = source_data.get("parse_selector")

    sections: list[SectionConfig] = []

    if "sections" in source_data:
        # New hierarchical format with explicit sections
        sections = [
            _parse_section(sec_data, default_parse_selector=default_selector)
            for sec_data in source_data.get("sections", [])
        ]
    elif "url" in source_data:
        # Legacy format: single URL becomes a single section
        # Use source title as section title for backward compatibility
        url = source_data["url"]
        title = source_data["title"]

        # Validate URL format
        _validate_url(url, f"source '{title}' (legacy format)")

        sections = [
            SectionConfig(
                title=title,
                url=url,
                enabled=source_data.get("enabled", True),
                parse_selector=default_selector,
                parse_comment=source_data.get("parse_comment"),
                fetch_interval_minutes=source_data.get("fetch_interval_minutes"),
            )
        ]

    return SourceConfig(
        title=source_data["title"],
        description=source_data.get("description"),
        enabled=source_data.get("enabled", True),
        parse_selector=default_selector,
        fetch_interval_minutes=source_data.get("fetch_interval_minutes"),
        sections=sections,
        url=source_data.get("url"),  # Keep for reference (deprecated)
    )


def _parse_category(category_data: dict[str, Any]) -> CategoryConfig:
    """Parse a category with its sources from config."""
    sources = [_parse_source(s) for s in category_data.get("sources", [])]
    return CategoryConfig(
        name=category_data["category"],
        enabled=category_data.get("enabled", True),
        fetch_interval_minutes=category_data.get("fetch_interval_minutes"),
        sources=sources,
    )


def load_news_config(
    config_path: Path | None = None,
) -> tuple[NewsSettings, list[CategoryConfig]]:
    """Load news configuration from YAML file.

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        Tuple of (settings, categories) where:
        - settings: Global NewsSettings
        - categories: List of CategoryConfig with their sources and sections

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
    """
    path = config_path or _get_config_path()

    if not path.exists():
        logger.warning("News config file not found", path=str(path))
        return NewsSettings(), []

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    settings = _parse_settings(data)

    categories = [_parse_category(cat_data) for cat_data in data.get("news", [])]

    # Count sections (not sources) since sources now contain sections
    total_sources = sum(len(cat.sources) for cat in categories)
    total_sections = sum(len(src.sections) for cat in categories for src in cat.sources)

    logger.info(
        "Loaded news configuration",
        categories=len(categories),
        sources=total_sources,
        sections=total_sections,
        path=str(path),
    )

    return settings, categories
