"""News service for fetching and managing news entries.

Orchestrates configuration loading, fetching, parsing, and storage.

Hierarchy: NewsCategory → NewsSource → NewsSection → NewsEntry
- Categories group related sources
- Sources are conceptual containers (e.g., "ECB Monetary Policy")
- Sections are fetchable pages with URLs (e.g., "Monetary policy decisions")
- Entries are individual articles discovered from sections
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from bs4 import BeautifulSoup
from ecox_shared.models import NewsSection
from ecox_shared.utils import ResilientHttpClient
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.news.config import NewsSettings, load_news_config
from ecox_platform.news.events import NewsEvent, publish_news_event
from ecox_platform.news.parser import NewsParser
from ecox_platform.news.repository import NewsRepository

logger = structlog.get_logger()


def _utc_now() -> datetime:
    """Return current UTC time as naive datetime for database compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class FetchResult:
    """Result of fetching a single news section."""

    section_id: int
    section_title: str
    source_title: str
    status: str  # "success" or "error"
    entries_found: int = 0
    entries_new: int = 0
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class ImportResult:
    """Result of importing sources from config."""

    categories_created: int = 0
    categories_updated: int = 0
    sources_created: int = 0
    sources_updated: int = 0
    sections_created: int = 0
    sections_updated: int = 0


class NewsService:
    """Service for news fetching and management."""

    def __init__(
        self,
        repository: NewsRepository | None = None,
        parser: NewsParser | None = None,
        settings: NewsSettings | None = None,
    ) -> None:
        """Initialize the news service.

        Args:
            repository: News repository instance (created if not provided)
            parser: News parser instance (created if not provided)
            settings: News settings (loaded from config if not provided)
        """
        self.repository = repository or NewsRepository()
        self.parser = parser or NewsParser()
        self._settings = settings
        self._http_client: ResilientHttpClient | None = None

    @property
    def settings(self) -> NewsSettings:
        """Get news settings (lazy loaded)."""
        if self._settings is None:
            self._settings, _ = load_news_config()
        return self._settings

    async def _get_http_client(self) -> ResilientHttpClient:
        """Get or create HTTP client for fetching pages."""
        if self._http_client is None:
            self._http_client = ResilientHttpClient(
                base_url="",  # No base URL, we use full URLs
                rate_limit=self.settings.rate_limit_per_domain,
                timeout=30,
            )
        return self._http_client

    async def close(self) -> None:
        """Close resources."""
        if self._http_client:
            await self._http_client.close()
            self._http_client = None

    async def import_from_config(
        self,
        session: AsyncSession,
    ) -> ImportResult:
        """Import news sources and sections from config/news.yaml to database.

        Creates or updates categories, sources, and sections based on configuration.
        Supports both new hierarchical format (with sections) and legacy flat format.
        """
        settings, categories = load_news_config()
        self._settings = settings

        result = ImportResult()

        for cat_config in categories:
            # Get or create category
            existing_cat = await self.repository.get_or_create_category(
                session=session,
                name=cat_config.name,
                fetch_interval_minutes=cat_config.fetch_interval_minutes,
            )

            if existing_cat.id is None:
                result.categories_created += 1
            else:
                result.categories_updated += 1

            # Ensure category has an ID after flush
            await session.flush()

            # Import sources for this category
            for src_config in cat_config.sources:
                # Check if source exists by title within category
                existing_src = await self.repository.get_source_by_title(
                    session,
                    src_config.title,
                    existing_cat.id,  # type: ignore[arg-type]
                )

                # Compute effective enabled: source AND category must both be enabled
                is_active = src_config.enabled and cat_config.enabled

                source = await self.repository.upsert_source(
                    session=session,
                    title=src_config.title,
                    category_id=existing_cat.id,  # type: ignore[arg-type]
                    description=src_config.description,
                    is_active=is_active,
                    fetch_interval_minutes=src_config.fetch_interval_minutes,
                )

                if existing_src is None:
                    result.sources_created += 1
                else:
                    result.sources_updated += 1

                await session.flush()

                # Import sections for this source
                for sec_config in src_config.sections:
                    existing_sec = await self.repository.get_section_by_url(session, sec_config.url)

                    # Sections inherit enabled from source
                    section_active = sec_config.enabled and is_active

                    await self.repository.upsert_section(
                        session=session,
                        source_id=source.id,  # type: ignore[arg-type]
                        title=sec_config.title,
                        url=sec_config.url,
                        is_active=section_active,
                        parse_selector=sec_config.parse_selector,
                        parse_comment=sec_config.parse_comment,
                        fetch_interval_minutes=sec_config.fetch_interval_minutes,
                    )

                    if existing_sec is None:
                        result.sections_created += 1
                    else:
                        result.sections_updated += 1

        await session.commit()

        logger.info(
            "Imported news sources from config",
            categories_created=result.categories_created,
            categories_updated=result.categories_updated,
            sources_created=result.sources_created,
            sources_updated=result.sources_updated,
            sections_created=result.sections_created,
            sections_updated=result.sections_updated,
        )

        return result

    async def fetch_section(
        self,
        session: AsyncSession,
        section: NewsSection,
        source_title: str | None = None,
    ) -> FetchResult:
        """Fetch and parse entries from a single news section.

        Args:
            session: Database session
            section: The news section to fetch
            source_title: Optional source title for logging (looked up if not provided)

        Returns:
            FetchResult with status and entry counts
        """
        started_at = _utc_now()

        # Look up source title if not provided
        if source_title is None:
            source = await self.repository.get_source_by_id(session, section.source_id)
            source_title = source.title if source else "Unknown"

        try:
            # Fetch the page HTML
            http_client = await self._get_http_client()
            response = await http_client.client.get(section.url)
            response.raise_for_status()
            html = response.text

            # Parse entries from the index page
            parsed_entries = await self.parser.parse(
                html=html,
                source_url=section.url,
                parse_selector=section.parse_selector,
            )

            # Batch check for existing URLs (fixes N+1 query issue)
            parsed_urls = [entry.url for entry in parsed_entries]
            existing_urls = await self.repository.get_existing_urls(session, parsed_urls)

            # Filter to only new entries
            new_entries = [e for e in parsed_entries if e.url not in existing_urls]

            # Fetch full content for new entries in parallel (US-5.10)
            entries_to_store: list[dict[str, Any]] = []
            if new_entries and self.settings.store_full_content:
                # Use semaphore to limit concurrent content fetches
                semaphore = asyncio.Semaphore(self.settings.content_fetch_concurrency)

                async def fetch_with_semaphore(entry_url: str) -> str | None:
                    async with semaphore:
                        return await self._fetch_full_content(entry_url)

                # Fetch all content in parallel
                content_results = await asyncio.gather(
                    *[fetch_with_semaphore(e.url) for e in new_entries],
                    return_exceptions=True,
                )

                for entry, content_result in zip(new_entries, content_results, strict=True):
                    content_full = content_result if isinstance(content_result, str) else None

                    # Generate preview from full content, or fetch separately
                    content_preview = None
                    if content_full:
                        content_preview = (
                            content_full[:500] if len(content_full) > 500 else content_full
                        )
                    else:
                        # Fallback: fetch preview only if full content failed
                        content_preview = await self._fetch_content_preview(entry.url)

                    entries_to_store.append(
                        {
                            "title": entry.title,
                            "url": entry.url,
                            "published_at": entry.published_at,
                            "content_full": content_full,
                            "content_preview": content_preview,
                        }
                    )
            else:
                # No content fetching needed - just store entries
                for entry in new_entries:
                    entries_to_store.append(
                        {
                            "title": entry.title,
                            "url": entry.url,
                            "published_at": entry.published_at,
                            "content_full": None,
                            "content_preview": None,
                        }
                    )

            # Store new entries
            new_count = await self.repository.upsert_entries(
                session=session,
                section_id=section.id,  # type: ignore[arg-type]
                entries=entries_to_store,
            )

            # Update section status
            await self.repository.update_section_status(
                session=session,
                section_id=section.id,  # type: ignore[arg-type]
                status="success",
            )

            completed_at = _utc_now()
            duration = (completed_at - started_at).total_seconds()

            # Log the fetch
            await self.repository.log_fetch(
                session=session,
                section_id=section.id,  # type: ignore[arg-type]
                status="success",
                entries_found=len(parsed_entries),
                entries_new=new_count,
                started_at=started_at,
                completed_at=completed_at,
            )

            await session.commit()

            logger.info(
                "Fetched news section",
                section=section.title,
                source=source_title,
                url=section.url,
                entries_found=len(parsed_entries),
                entries_new=new_count,
                duration=duration,
            )

            # Publish SSE event if new entries found
            if new_count > 0:
                await publish_news_event(
                    NewsEvent(
                        event_type="new_entries",
                        section_id=section.id,
                        section_title=section.title,
                        source_id=section.source_id,
                        source_title=source_title,
                        entry_count=len(parsed_entries),
                        entries_new=new_count,
                    )
                )

            return FetchResult(
                section_id=section.id,  # type: ignore[arg-type]
                section_title=section.title,
                source_title=source_title,
                status="success",
                entries_found=len(parsed_entries),
                entries_new=new_count,
                duration_seconds=duration,
            )

        except Exception as e:
            # Log full error before truncating for storage
            logger.error(
                "Exception during section fetch",
                section=section.title,
                source=source_title,
                url=section.url,
                error=str(e),
                exc_info=True,
            )
            error_msg = str(e)[:500]  # Truncate for storage

            # Update section status
            await self.repository.update_section_status(
                session=session,
                section_id=section.id,  # type: ignore[arg-type]
                status="error",
                error=error_msg,
            )

            completed_at = _utc_now()
            duration = (completed_at - started_at).total_seconds()

            # Log the failed fetch
            await self.repository.log_fetch(
                session=session,
                section_id=section.id,  # type: ignore[arg-type]
                status="error",
                error_message=error_msg,
                started_at=started_at,
                completed_at=completed_at,
            )

            await session.commit()

            logger.warning(
                "Failed to fetch news section",
                section=section.title,
                source=source_title,
                url=section.url,
                error=error_msg,
            )

            return FetchResult(
                section_id=section.id,  # type: ignore[arg-type]
                section_title=section.title,
                source_title=source_title,
                status="error",
                error=error_msg,
                duration_seconds=duration,
            )

    async def _fetch_full_content(
        self,
        url: str,
    ) -> str | None:
        """Fetch full article content (US-5.10).

        Extracts the main article text, removing navigation, scripts, and other
        non-content elements.

        Args:
            url: Article URL to fetch

        Returns:
            Full article text, or None on error
        """
        try:
            http_client = await self._get_http_client()
            response = await http_client.client.get(
                url, timeout=self.settings.content_fetch_timeout
            )
            response.raise_for_status()
            html = response.text

            soup = BeautifulSoup(html, "lxml")

            # Remove non-content elements
            for element in soup(
                ["script", "style", "nav", "header", "footer", "aside", "noscript"]
            ):
                element.decompose()

            # Try to find main content area in priority order
            main_content = (
                soup.find("article")
                or soup.find("main")
                or soup.find(class_="article-body")
                or soup.find(class_="article-content")
                or soup.find(class_="content")
                or soup.find(class_="post-content")
                or soup.find(id="content")
                or soup.find(id="article")
                or soup.body
            )

            if main_content:
                # Extract text with paragraph separation
                paragraphs = main_content.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"])
                if paragraphs:
                    text_parts = []
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if text:
                            text_parts.append(text)
                    if text_parts:
                        return "\n\n".join(text_parts)

                # Fallback: get all text
                text = main_content.get_text(separator=" ", strip=True)
                # Clean up whitespace
                text = " ".join(text.split())
                return text if text else None

        except Exception as e:
            logger.debug("Failed to fetch full content", url=url, error=str(e))

        return None

    async def _fetch_content_preview(
        self,
        url: str,
        max_length: int = 500,
    ) -> str | None:
        """Fetch article and extract content preview.

        Fallback method when full content fetch fails or is disabled.

        Args:
            url: Article URL to fetch
            max_length: Maximum characters for preview

        Returns:
            First max_length chars of article text, or None on error
        """
        full_content = await self._fetch_full_content(url)
        if full_content:
            return full_content[:max_length] if len(full_content) > max_length else full_content
        return None

    async def get_categories_with_sources_and_sections(
        self,
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Get all categories with their sources, sections, and entry counts.

        Returns hierarchical structure for UI tree view (US-5.11).
        """
        categories = await self.repository.get_categories(session)
        entry_counts = await self.repository.get_entry_count_by_section(session)

        result = []
        for category in categories:
            sources = await self.repository.get_sources(session, category_id=category.id)

            source_list = []
            for source in sources:
                sections = await self.repository.get_sections(session, source_id=source.id)

                section_list = []
                for section in sections:
                    section_entry_count = entry_counts.get(section.id, 0)  # type: ignore[arg-type]
                    section_list.append(
                        {
                            "id": section.id,
                            "title": section.title,
                            "url": section.url,
                            "is_active": section.is_active,
                            "last_fetched_at": section.last_fetched_at,
                            "last_fetch_status": section.last_fetch_status,
                            "last_fetch_error": section.last_fetch_error,
                            "entry_count": section_entry_count,
                        }
                    )

                source_entry_count = sum(s["entry_count"] for s in section_list)
                source_list.append(
                    {
                        "id": source.id,
                        "title": source.title,
                        "description": source.description,
                        "is_active": source.is_active,
                        "sections": section_list,
                        "section_count": len(section_list),
                        "entry_count": source_entry_count,
                    }
                )

            category_entry_count = sum(s["entry_count"] for s in source_list)
            result.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "sources": source_list,
                    "source_count": len(source_list),
                    "section_count": sum(s["section_count"] for s in source_list),
                    "total_entries": category_entry_count,
                }
            )

        return result

    async def cleanup_old_entries(
        self,
        session: AsyncSession,
    ) -> int:
        """Remove entries older than retention period."""
        deleted = await self.repository.cleanup_old_entries(
            session,
            months=self.settings.article_retention_months,
        )
        await session.commit()

        if deleted > 0:
            logger.info("Cleaned up old news entries", deleted=deleted)

        return deleted
