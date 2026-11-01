"""News repository for database operations.

Handles CRUD operations for news categories, sources, sections, and entries.

Hierarchy:
- NewsCategory: Groups related sources
- NewsSource: Container for sections
- NewsSection: Specific page/feed with URL and fetch status
- NewsEntry: Individual article/item discovered from a section
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from ecox_shared.models import NewsCategory, NewsEntry, NewsFetchLog, NewsSection, NewsSource
from sqlalchemy import delete, func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

logger = structlog.get_logger()


def _utc_now() -> datetime:
    """Return current UTC time as naive datetime for database compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class NewsRepository:
    """Repository for news database operations."""

    # --- Categories ---

    async def get_categories(
        self,
        session: AsyncSession,
    ) -> list[NewsCategory]:
        """Get all news categories."""
        categories = await session.exec(select(NewsCategory).order_by(NewsCategory.name))
        return list(categories.all())

    async def get_or_create_category(
        self,
        session: AsyncSession,
        name: str,
        fetch_interval_minutes: int | None = None,
    ) -> NewsCategory:
        """Get existing category or create new one."""
        category = (
            await session.exec(select(NewsCategory).where(NewsCategory.name == name))
        ).one_or_none()

        if category:
            # Update interval if changed
            if fetch_interval_minutes is not None:
                category.fetch_interval_minutes = fetch_interval_minutes
            return category

        category = NewsCategory(
            name=name,
            fetch_interval_minutes=fetch_interval_minutes,
        )
        session.add(category)
        await session.flush()
        return category

    # --- Sources ---

    async def get_sources(
        self,
        session: AsyncSession,
        category_id: int | None = None,
    ) -> list[NewsSource]:
        """Get news sources, optionally filtered by category."""
        query = select(NewsSource).order_by(NewsSource.title)
        if category_id is not None:
            query = query.where(NewsSource.category_id == category_id)
        return list((await session.exec(query)).all())

    async def get_source_by_id(
        self,
        session: AsyncSession,
        source_id: int,
    ) -> NewsSource | None:
        """Get a single source by ID."""
        return (
            await session.exec(select(NewsSource).where(NewsSource.id == source_id))
        ).one_or_none()

    async def get_source_by_title(
        self,
        session: AsyncSession,
        title: str,
        category_id: int,
    ) -> NewsSource | None:
        """Get a source by title within a category."""
        return (
            await session.exec(
                select(NewsSource).where(
                    NewsSource.title == title,
                    NewsSource.category_id == category_id,
                )
            )
        ).one_or_none()

    async def upsert_source(
        self,
        session: AsyncSession,
        title: str,
        category_id: int,
        description: str | None = None,
        is_active: bool = True,
        fetch_interval_minutes: int | None = None,
    ) -> NewsSource:
        """Insert or update a news source."""
        source = await self.get_source_by_title(session, title, category_id)

        if source:
            # Update existing source
            source.description = description
            source.is_active = is_active
            if fetch_interval_minutes is not None:
                source.fetch_interval_minutes = fetch_interval_minutes
        else:
            # Create new source
            source = NewsSource(
                title=title,
                description=description,
                category_id=category_id,
                is_active=is_active,
                fetch_interval_minutes=fetch_interval_minutes,
            )
            session.add(source)

        await session.flush()
        return source

    # --- Sections (US-5.9) ---

    async def get_sections(
        self,
        session: AsyncSession,
        source_id: int | None = None,
    ) -> list[NewsSection]:
        """Get sections, optionally filtered by source."""
        query = select(NewsSection).order_by(NewsSection.title)
        if source_id is not None:
            query = query.where(NewsSection.source_id == source_id)
        return list((await session.exec(query)).all())

    async def get_section_by_id(
        self,
        session: AsyncSession,
        section_id: int,
    ) -> NewsSection | None:
        """Get a single section by ID."""
        return (
            await session.exec(select(NewsSection).where(NewsSection.id == section_id))
        ).one_or_none()

    async def get_section_by_url(
        self,
        session: AsyncSession,
        url: str,
    ) -> NewsSection | None:
        """Get a section by URL."""
        return (await session.exec(select(NewsSection).where(NewsSection.url == url))).one_or_none()

    async def upsert_section(
        self,
        session: AsyncSession,
        source_id: int,
        title: str,
        url: str,
        is_active: bool = True,
        parse_selector: str | None = None,
        parse_comment: str | None = None,
        fetch_interval_minutes: int | None = None,
    ) -> NewsSection:
        """Insert or update a news section.

        Args:
            session: Database session
            source_id: Parent source ID
            title: Section title
            url: Section URL (must be unique)
            is_active: Whether section is enabled for fetching
            parse_selector: CSS/XPath selector for parsing
            parse_comment: Notes about parsing
            fetch_interval_minutes: Override fetch interval

        Returns:
            Created or updated NewsSection

        Raises:
            ValueError: If required fields are empty
        """
        # Input validation
        if not title or not title.strip():
            raise ValueError("Section title cannot be empty")
        if not url or not url.strip():
            raise ValueError("Section URL cannot be empty")

        section = await self.get_section_by_url(session, url)

        if section:
            # Update existing section
            section.source_id = source_id
            section.title = title
            section.is_active = is_active
            section.parse_selector = parse_selector
            section.parse_comment = parse_comment
            if fetch_interval_minutes is not None:
                section.fetch_interval_minutes = fetch_interval_minutes
        else:
            # Create new section
            section = NewsSection(
                source_id=source_id,
                title=title,
                url=url,
                is_active=is_active,
                parse_selector=parse_selector,
                parse_comment=parse_comment,
                fetch_interval_minutes=fetch_interval_minutes,
            )
            session.add(section)

        await session.flush()
        return section

    async def update_section_status(
        self,
        session: AsyncSession,
        section_id: int,
        status: str,
        error: str | None = None,
    ) -> None:
        """Update section fetch status (US-5.13)."""
        section = (
            await session.exec(select(NewsSection).where(NewsSection.id == section_id))
        ).one_or_none()

        if section:
            section.last_checked_at = _utc_now()
            section.last_fetch_status = status
            section.last_fetch_error = error
            if status == "success":
                section.last_fetched_at = _utc_now()

    async def get_stale_sections(
        self,
        session: AsyncSession,
        default_interval_minutes: int = 60,
    ) -> list[NewsSection]:
        """Get active sections that need to be fetched.

        A section is stale if:
        - is_active is True (must be enabled)
        - Parent source is_active is True
        - Never fetched (last_fetched_at is None) OR last_fetched_at + interval < now
        """
        now = _utc_now()
        cutoff = now - timedelta(minutes=default_interval_minutes)

        # Filter for active sections with active sources
        return list(
            (
                await session.exec(
                    select(NewsSection)
                    .join(NewsSource)
                    .where(
                        NewsSection.is_active == True,  # noqa: E712
                        NewsSource.is_active == True,  # noqa: E712
                    )
                    .where(
                        (col(NewsSection.last_fetched_at).is_(None))
                        | (col(NewsSection.last_fetched_at) < cutoff)
                    )
                )
            ).all()
        )

    # --- Entries (renamed from Articles) ---

    async def get_entries(
        self,
        session: AsyncSession,
        section_id: int | None = None,
        source_id: int | None = None,
        category_id: int | None = None,
        since: datetime | None = None,
        search: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[NewsEntry], int]:
        """Get entries with filtering and pagination.

        Returns tuple of (entries, total_count).
        """
        query = select(NewsEntry).order_by(col(NewsEntry.discovered_at).desc())
        count_query = select(func.count()).select_from(NewsEntry)

        # Apply filters
        if section_id is not None:
            query = query.where(NewsEntry.section_id == section_id)
            count_query = count_query.where(NewsEntry.section_id == section_id)

        if source_id is not None:
            # Join with section to filter by source
            query = query.join(NewsSection).where(NewsSection.source_id == source_id)
            count_query = count_query.join(NewsSection).where(NewsSection.source_id == source_id)

        if category_id is not None:
            # Join with section and source to filter by category
            query = (
                query.join(NewsSection)
                .join(NewsSource)
                .where(NewsSource.category_id == category_id)
            )
            count_query = (
                count_query.join(NewsSection)
                .join(NewsSource)
                .where(NewsSource.category_id == category_id)
            )

        if since is not None:
            query = query.where(NewsEntry.discovered_at >= since)
            count_query = count_query.where(NewsEntry.discovered_at >= since)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(col(NewsEntry.title).ilike(search_pattern))
            count_query = count_query.where(col(NewsEntry.title).ilike(search_pattern))

        # Get total count
        total = (await session.exec(count_query)).one() or 0

        # Apply pagination
        query = query.limit(limit).offset(offset)

        entries = list((await session.exec(query)).all())

        return entries, total

    async def get_entry_by_id(
        self,
        session: AsyncSession,
        entry_id: int,
    ) -> NewsEntry | None:
        """Get a single entry by ID with full content."""
        return (await session.exec(select(NewsEntry).where(NewsEntry.id == entry_id))).one_or_none()

    async def entry_exists(
        self,
        session: AsyncSession,
        url: str,
    ) -> bool:
        """Check if an entry with this URL already exists."""
        count = (
            await session.exec(
                select(func.count()).select_from(NewsEntry).where(NewsEntry.url == url)
            )
        ).one() or 0
        return count > 0

    async def get_existing_urls(
        self,
        session: AsyncSession,
        urls: list[str],
    ) -> set[str]:
        """Batch check for existing entry URLs.

        Args:
            session: Database session
            urls: List of URLs to check

        Returns:
            Set of URLs that already exist in the database
        """
        if not urls:
            return set()

        result = await session.execute(
            select(col(NewsEntry.url)).where(col(NewsEntry.url).in_(urls))
        )
        return {row[0] for row in result.all()}

    async def upsert_entries(
        self,
        session: AsyncSession,
        section_id: int,
        entries: list[dict[str, Any]],
    ) -> int:
        """Insert entries that don't already exist.

        Args:
            session: Database session
            section_id: ID of the section these entries came from
            entries: List of entry dicts with:
                - title, url, published_at
                - content_full (US-5.10)
                - content_preview (computed from content_full)

        Returns:
            Number of new entries inserted
        """
        if not entries:
            return 0

        # Batch fetch all existing URLs in ONE query (fixes N+1 problem)
        entry_urls = [e["url"] for e in entries]
        existing_entries = (
            await session.exec(select(NewsEntry).where(col(NewsEntry.url).in_(entry_urls)))
        ).all()
        existing_urls = {entry.url for entry in existing_entries}

        new_count = 0
        for entry_data in entries:
            url = entry_data["url"]

            # O(1) set lookup instead of database query
            if url in existing_urls:
                continue

            # Generate content_preview from content_full if not provided
            content_full = entry_data.get("content_full")
            content_preview = entry_data.get("content_preview")
            if content_full and not content_preview:
                content_preview = content_full[:500] if len(content_full) > 500 else content_full

            entry = NewsEntry(
                section_id=section_id,
                title=entry_data["title"],
                url=url,
                published_at=entry_data.get("published_at"),
                content_full=content_full,
                content_preview=content_preview,
            )
            session.add(entry)
            new_count += 1

        if new_count > 0:
            await session.flush()

        return new_count

    async def cleanup_old_entries(
        self,
        session: AsyncSession,
        months: int = 12,
    ) -> int:
        """Delete entries older than specified months.

        Returns number of deleted entries.
        """
        cutoff = _utc_now() - timedelta(days=months * 30)

        result = await session.execute(
            delete(NewsEntry).where(col(NewsEntry.discovered_at) < cutoff)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def get_entry_count_by_section(
        self,
        session: AsyncSession,
        section_ids: list[int] | None = None,
    ) -> dict[int, int]:
        """Get entry count per section.

        Args:
            session: Database session
            section_ids: Optional list of section IDs to filter by.
                If None, returns counts for all sections.

        Returns:
            Dictionary mapping section_id to entry count
        """
        query = select(
            col(NewsEntry.section_id),
            func.count(),
        ).group_by(col(NewsEntry.section_id))

        if section_ids:
            query = query.where(col(NewsEntry.section_id).in_(section_ids))

        result = await session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    # --- Fetch Log (US-5.13) ---

    async def log_fetch(
        self,
        session: AsyncSession,
        section_id: int,
        status: str,
        entries_found: int = 0,
        entries_new: int = 0,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> NewsFetchLog:
        """Log a fetch operation for a section."""
        duration = None
        if started_at and completed_at:
            duration = (completed_at - started_at).total_seconds()

        log_entry = NewsFetchLog(
            section_id=section_id,
            status=status,
            entries_found=entries_found,
            entries_new=entries_new,
            error_message=error_message,
            started_at=started_at or _utc_now(),
            completed_at=completed_at,
            duration_seconds=duration,
        )
        session.add(log_entry)
        await session.flush()
        return log_entry

    async def get_fetch_logs(
        self,
        session: AsyncSession,
        section_id: int | None = None,
        limit: int = 50,
    ) -> list[NewsFetchLog]:
        """Get recent fetch logs."""
        query = select(NewsFetchLog).order_by(col(NewsFetchLog.started_at).desc())

        if section_id is not None:
            query = query.where(NewsFetchLog.section_id == section_id)

        query = query.limit(limit)
        return list((await session.exec(query)).all())

    # --- Feed (US-5.14) ---

    async def get_feed_entries(
        self,
        session: AsyncSession,
        category_id: int | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[NewsEntry], int]:
        """Get entries for chronological feed (US-5.14).

        Sorted by published_at DESC (nulls last), then discovered_at DESC.
        Returns tuple of (entries, total_count).

        Args:
            session: Database session
            category_id: Optional category filter
            search: Optional search term for titles
            limit: Max entries to return (default 20)
            offset: Pagination offset

        Returns:
            Tuple of (entries list, total count)
        """
        # Base query with proper ordering for feed
        query = select(NewsEntry).order_by(
            col(NewsEntry.published_at).desc().nulls_last(),
            col(NewsEntry.discovered_at).desc(),
        )
        count_query = select(func.count()).select_from(NewsEntry)

        # Category filter requires joining through section and source
        if category_id is not None:
            query = (
                query.join(NewsSection)
                .join(NewsSource)
                .where(NewsSource.category_id == category_id)
            )
            count_query = (
                count_query.join(NewsSection)
                .join(NewsSource)
                .where(NewsSource.category_id == category_id)
            )

        # Search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.where(col(NewsEntry.title).ilike(search_pattern))
            count_query = count_query.where(col(NewsEntry.title).ilike(search_pattern))

        # Get total count
        total = (await session.exec(count_query)).one() or 0

        # Apply pagination
        query = query.limit(limit).offset(offset)
        entries = list((await session.exec(query)).all())

        return entries, total
