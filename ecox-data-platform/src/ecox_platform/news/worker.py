"""News worker for continuous news fetching.

This module provides a background worker that continuously fetches news from
configured sections, respecting rate limits and per-section intervals.

Hierarchy: NewsCategory → NewsSource → NewsSection → NewsEntry
The worker fetches at the section level, as sections are the fetchable units.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import structlog

from ecox_platform.infrastructure.database import DatabaseManager, get_db_manager
from ecox_platform.news.config import NewsSettings, load_news_config
from ecox_platform.news.service import FetchResult, NewsService

logger = structlog.get_logger(__name__)


class NewsWorker:
    """Worker that continuously fetches news from configured sections.

    Features:
    - Imports sources and sections from config on startup
    - Fetches stale sections (past their interval)
    - Per-domain rate limiting
    - Concurrent fetching with limits
    - Entry cleanup for old entries
    """

    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        service: NewsService | None = None,
        settings: NewsSettings | None = None,
    ) -> None:
        """Initialize the news worker.

        Args:
            db_manager: Database manager (uses global if not provided)
            service: News service (created if not provided)
            settings: News settings (loaded from config if not provided)
        """
        self.db_manager = db_manager or get_db_manager()
        self.service = service or NewsService()

        if settings:
            self._settings = settings
        else:
            self._settings, _ = load_news_config()

        # Concurrency control
        self.semaphore = asyncio.Semaphore(self._settings.max_concurrent_fetches)

        # Per-domain rate limiting: track last fetch time per domain
        self._domain_last_fetch: dict[str, datetime] = {}

        # Status tracking
        self.is_running = False
        self.last_activity: datetime | None = None
        self.sections_fetched = 0
        self.sections_failed = 0
        self.entries_found = 0
        self.entries_new = 0
        self.current_section: str | None = None

        logger.info(
            "News worker initialized",
            max_concurrent=self._settings.max_concurrent_fetches,
            rate_limit_per_domain=self._settings.rate_limit_per_domain,
            default_interval_minutes=self._settings.default_fetch_interval_minutes,
        )

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for rate limiting."""
        parsed = urlparse(url)
        return parsed.netloc.lower()

    async def _wait_for_rate_limit(self, domain: str) -> None:
        """Wait if necessary to respect per-domain rate limit.

        Args:
            domain: The domain to rate limit
        """
        if domain not in self._domain_last_fetch:
            return

        last_fetch = self._domain_last_fetch[domain]
        min_interval = 1.0 / self._settings.rate_limit_per_domain
        elapsed = (datetime.now(UTC) - last_fetch).total_seconds()

        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            logger.debug(
                "Rate limiting domain",
                domain=domain,
                wait_seconds=wait_time,
            )
            await asyncio.sleep(wait_time)

    async def _import_sources(self) -> None:
        """Import sources and sections from config to database."""
        async with self.db_manager.get_session() as session:
            result = await self.service.import_from_config(session)
            logger.info(
                "Imported news sources and sections",
                categories_created=result.categories_created,
                sources_created=result.sources_created,
                sections_created=result.sections_created,
            )

    async def _fetch_section_with_semaphore(
        self,
        section_id: int,
        section_url: str,
        section_title: str,
        source_title: str,
    ) -> FetchResult | None:
        """Fetch a section with concurrency and rate limit control.

        Args:
            section_id: Database ID of the section
            section_url: URL of the section
            section_title: Title for logging
            source_title: Parent source title for logging

        Returns:
            FetchResult or None on error
        """
        domain = self._get_domain(section_url)

        async with self.semaphore:
            # Apply per-domain rate limiting
            await self._wait_for_rate_limit(domain)

            self.current_section = f"{source_title} / {section_title}"
            self.last_activity = datetime.now()

            try:
                async with self.db_manager.get_session() as session:
                    # Get the section from database
                    section = await self.service.repository.get_section_by_id(session, section_id)
                    if not section:
                        logger.warning(
                            "Section not found",
                            section_id=section_id,
                            title=section_title,
                        )
                        return None

                    # Fetch the section
                    result = await self.service.fetch_section(session, section, source_title)

                    # Update domain rate limit tracker
                    self._domain_last_fetch[domain] = datetime.now(UTC)

                    # Update statistics
                    if result.status == "success":
                        self.sections_fetched += 1
                        self.entries_found += result.entries_found
                        self.entries_new += result.entries_new
                    else:
                        self.sections_failed += 1

                    return result

            except Exception as e:
                self.sections_failed += 1
                logger.error(
                    "Failed to fetch section",
                    section_title=section_title,
                    source_title=source_title,
                    error=str(e)[:200],
                )
                return None
            finally:
                self.current_section = None

    async def run_cycle(self) -> dict[str, Any]:
        """Run one fetch cycle: find stale sections and fetch them.

        Returns:
            Dictionary with cycle results
        """
        cycle_start = datetime.now()

        async with self.db_manager.get_session() as session:
            # Get sections that need fetching
            stale_sections = await self.service.repository.get_stale_sections(
                session,
                default_interval_minutes=self._settings.default_fetch_interval_minutes,
            )

            # Also need source titles for each section
            section_source_titles: dict[int, str] = {}
            for section in stale_sections:
                if section.source_id not in section_source_titles:
                    source = await self.service.repository.get_source_by_id(
                        session, section.source_id
                    )
                    section_source_titles[section.source_id] = source.title if source else "Unknown"

        if not stale_sections:
            logger.debug("No stale news sections to fetch")
            return {
                "stale_sections": 0,
                "fetched": 0,
                "failed": 0,
                "entries_found": 0,
                "entries_new": 0,
                "duration_seconds": 0,
            }

        logger.info("Fetching stale news sections", count=len(stale_sections))

        # Fetch all stale sections concurrently (with semaphore limiting)
        tasks = [
            self._fetch_section_with_semaphore(
                section_id=section.id,  # type: ignore[arg-type]
                section_url=section.url,
                section_title=section.title,
                source_title=section_source_titles.get(section.source_id, "Unknown"),
            )
            for section in stale_sections
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        fetched = 0
        failed = 0
        entries_found = 0
        entries_new = 0

        for result in results:
            if isinstance(result, Exception):
                failed += 1
                logger.error("Unexpected error in fetch", error=str(result)[:200])
            elif result is None:
                failed += 1
            elif isinstance(result, FetchResult):
                if result.status == "success":
                    fetched += 1
                    entries_found += result.entries_found
                    entries_new += result.entries_new
                else:
                    failed += 1

        duration = (datetime.now() - cycle_start).total_seconds()

        logger.info(
            "News fetch cycle completed",
            stale_sections=len(stale_sections),
            fetched=fetched,
            failed=failed,
            entries_found=entries_found,
            entries_new=entries_new,
            duration_seconds=duration,
        )

        return {
            "stale_sections": len(stale_sections),
            "fetched": fetched,
            "failed": failed,
            "entries_found": entries_found,
            "entries_new": entries_new,
            "duration_seconds": duration,
        }

    async def cleanup_old_entries(self) -> int:
        """Remove entries older than retention period.

        Returns:
            Number of deleted entries
        """
        async with self.db_manager.get_session() as session:
            deleted = await self.service.cleanup_old_entries(session)
            if deleted > 0:
                logger.info("Cleaned up old news entries", deleted=deleted)
            return deleted

    async def run(self) -> None:
        """Run the worker continuously.

        This method runs forever, importing config on startup then
        fetching news sections in cycles.
        """
        self.is_running = True
        logger.info("News worker starting")

        # Initial delay before first fetch
        if self._settings.startup_delay_seconds > 0:
            logger.info(
                "Waiting before first fetch",
                delay_seconds=self._settings.startup_delay_seconds,
            )
            await asyncio.sleep(self._settings.startup_delay_seconds)

        # Import sources from config
        if self._settings.fetch_on_startup:
            try:
                await self._import_sources()
            except Exception as e:
                logger.error("Failed to import sources", error=str(e)[:200])

        logger.info("News worker started")

        while self.is_running:
            try:
                # Run fetch cycle
                await self.run_cycle()

                # Cleanup old entries periodically (once per cycle)
                await self.cleanup_old_entries()

                # Sleep until next cycle
                # Check more frequently than the default interval
                sleep_seconds = min(
                    self._settings.default_fetch_interval_minutes * 60 / 4,
                    900,  # Max 15 minutes between checks
                )
                sleep_seconds = max(sleep_seconds, 60)  # At least 1 minute

                logger.debug("News worker sleeping", sleep_seconds=sleep_seconds)
                await asyncio.sleep(sleep_seconds)

            except asyncio.CancelledError:
                logger.info("News worker cancelled")
                break

            except Exception as e:
                logger.error("News worker cycle failed", error=str(e)[:200])
                # Wait before retrying after error
                await asyncio.sleep(60)

        self.is_running = False
        logger.info("News worker stopped")

    def stop(self) -> None:
        """Signal the worker to stop."""
        self.is_running = False

    def status(self) -> dict[str, Any]:
        """Get worker status.

        Returns:
            Dictionary with worker status
        """
        return {
            "is_running": self.is_running,
            "last_activity": (self.last_activity.isoformat() if self.last_activity else None),
            "sections_fetched": self.sections_fetched,
            "sections_failed": self.sections_failed,
            "entries_found": self.entries_found,
            "entries_new": self.entries_new,
            "current_section": self.current_section,
            "config": {
                "max_concurrent_fetches": self._settings.max_concurrent_fetches,
                "rate_limit_per_domain": self._settings.rate_limit_per_domain,
                "default_interval_minutes": self._settings.default_fetch_interval_minutes,
                "article_retention_months": self._settings.article_retention_months,
            },
        }


# Global worker instance
_news_worker: NewsWorker | None = None


def get_news_worker() -> NewsWorker:
    """Get the global news worker instance.

    Returns:
        NewsWorker instance
    """
    global _news_worker
    if _news_worker is None:
        _news_worker = NewsWorker()
    return _news_worker


async def start_news_worker() -> NewsWorker:
    """Start the global news worker.

    Returns:
        NewsWorker instance
    """
    worker = get_news_worker()
    asyncio.create_task(worker.run(), name="news-worker")
    return worker


async def stop_news_worker() -> None:
    """Stop the global news worker."""
    global _news_worker
    if _news_worker is not None:
        _news_worker.stop()
        await _news_worker.service.close()
        _news_worker = None
