"""News endpoints for the platform API.

Provides access to news categories, sources, sections, and entries.

Hierarchy: Category → Source → Section → Entry
- Categories group related sources
- Sources are conceptual containers
- Sections are fetchable pages with URLs
- Entries are individual articles discovered from sections
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from ecox_shared.models import NewsSection, NewsSource
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ecox_platform.api.dependencies import get_session
from ecox_platform.news import (
    NewsRepository,
    NewsService,
    get_news_worker,
)
from ecox_platform.news.events import get_event_manager

router = APIRouter(prefix="/news", tags=["news"])


# Dependency injection functions for testability
def get_news_repository() -> NewsRepository:
    """Get news repository instance."""
    return NewsRepository()


def get_news_service(
    repository: NewsRepository = Depends(get_news_repository),
) -> NewsService:
    """Get news service instance with injected repository."""
    return NewsService(repository=repository)


# Response models
class EntryResponse(BaseModel):
    """Response model for a news entry (list view)."""

    id: int
    title: str
    url: str
    section_id: int
    section_title: str | None = None
    source_title: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime
    content_preview: str | None = None


class EntryDetailResponse(BaseModel):
    """Response model for a news entry with full content (US-5.12)."""

    id: int
    title: str
    url: str
    section_id: int
    section_title: str | None = None
    source_id: int | None = None
    source_title: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime
    content_full: str | None = None
    content_preview: str | None = None


class SectionResponse(BaseModel):
    """Response model for a news section (US-5.9)."""

    id: int
    title: str
    url: str
    source_id: int
    is_active: bool = False
    last_fetched_at: datetime | None = None
    last_fetch_status: str | None = None
    last_fetch_error: str | None = None
    entry_count: int = 0


class SourceResponse(BaseModel):
    """Response model for a news source."""

    id: int
    title: str
    description: str | None = None
    is_active: bool = False
    sections: list[SectionResponse] = []
    section_count: int = 0
    entry_count: int = 0


class CategoryResponse(BaseModel):
    """Response model for a news category."""

    id: int
    name: str
    sources: list[SourceResponse]
    source_count: int
    section_count: int = 0
    total_entries: int


class EntriesListResponse(BaseModel):
    """Response model for paginated entries list."""

    entries: list[EntryResponse]
    total: int
    limit: int
    offset: int


class FeedEntryResponse(BaseModel):
    """Response model for a feed entry (US-5.14)."""

    id: int
    title: str
    url: str
    published_at: datetime | None = None
    discovered_at: datetime
    content_preview: str | None = None
    source_title: str
    section_title: str
    category_name: str


class FeedResponse(BaseModel):
    """Response model for chronological feed (US-5.14)."""

    entries: list[FeedEntryResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class NewsStatusResponse(BaseModel):
    """Response model for news worker status."""

    is_running: bool
    last_activity: datetime | None = None
    sections_fetched: int
    sections_failed: int
    entries_found: int
    entries_new: int
    current_section: str | None = None
    config: dict[str, Any]


class FetchResultResponse(BaseModel):
    """Response model for section fetch result."""

    section_id: int
    section_title: str
    source_title: str
    status: str
    entries_found: int = 0
    entries_new: int = 0
    error: str | None = None
    duration_seconds: float = 0.0


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    session: AsyncSession = Depends(get_session),
    service: NewsService = Depends(get_news_service),
) -> list[CategoryResponse]:
    """List all news categories with their sources, sections, and entry counts.

    Returns hierarchical structure for UI tree view (US-5.11).

    Returns:
        List of categories with nested sources and sections
    """
    categories_data = await service.get_categories_with_sources_and_sections(session)

    return [
        CategoryResponse(
            id=cat["id"],
            name=cat["name"],
            sources=[
                SourceResponse(
                    id=s["id"],
                    title=s["title"],
                    description=s.get("description"),
                    is_active=s["is_active"],
                    sections=[
                        SectionResponse(
                            id=sec["id"],
                            title=sec["title"],
                            url=sec["url"],
                            source_id=s["id"],
                            is_active=sec["is_active"],
                            last_fetched_at=sec["last_fetched_at"],
                            last_fetch_status=sec["last_fetch_status"],
                            last_fetch_error=sec["last_fetch_error"],
                            entry_count=sec["entry_count"],
                        )
                        for sec in s["sections"]
                    ],
                    section_count=s["section_count"],
                    entry_count=s["entry_count"],
                )
                for s in cat["sources"]
            ],
            source_count=cat["source_count"],
            section_count=cat["section_count"],
            total_entries=cat["total_entries"],
        )
        for cat in categories_data
    ]


@router.get("/sources/{source_id}/sections", response_model=list[SectionResponse])
async def list_source_sections(
    source_id: int,
    session: AsyncSession = Depends(get_session),
    repository: NewsRepository = Depends(get_news_repository),
) -> list[SectionResponse]:
    """List sections for a specific source (US-5.9).

    Args:
        source_id: The source ID to get sections for

    Returns:
        List of sections for this source
    """
    # Verify source exists
    source = await repository.get_source_by_id(session, source_id)
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")

    sections = await repository.get_sections(session, source_id=source_id)
    entry_counts = await repository.get_entry_count_by_section(session)

    return [
        SectionResponse(
            id=section.id,  # type: ignore[arg-type]
            title=section.title,
            url=section.url,
            source_id=section.source_id,
            is_active=section.is_active,
            last_fetched_at=section.last_fetched_at,
            last_fetch_status=section.last_fetch_status,
            last_fetch_error=section.last_fetch_error,
            entry_count=entry_counts.get(section.id, 0),  # type: ignore[arg-type]
        )
        for section in sections
    ]


@router.get("/sections/{section_id}", response_model=SectionResponse)
async def get_section(
    section_id: int,
    session: AsyncSession = Depends(get_session),
    repository: NewsRepository = Depends(get_news_repository),
) -> SectionResponse:
    """Get details for a specific section (US-5.13).

    Args:
        section_id: The section ID

    Returns:
        Section details including fetch status
    """
    section = await repository.get_section_by_id(session, section_id)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section {section_id} not found")

    entry_counts = await repository.get_entry_count_by_section(session)

    return SectionResponse(
        id=section.id,  # type: ignore[arg-type]
        title=section.title,
        url=section.url,
        source_id=section.source_id,
        is_active=section.is_active,
        last_fetched_at=section.last_fetched_at,
        last_fetch_status=section.last_fetch_status,
        last_fetch_error=section.last_fetch_error,
        entry_count=entry_counts.get(section.id, 0),  # type: ignore[arg-type]
    )


@router.get("/sections/{section_id}/entries", response_model=EntriesListResponse)
async def list_section_entries(
    section_id: int,
    session: AsyncSession = Depends(get_session),
    repository: NewsRepository = Depends(get_news_repository),
    limit: int = Query(20, ge=1, le=100, description="Max entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> EntriesListResponse:
    """List entries for a specific section (for lazy-loading in UI).

    This endpoint is designed for htmx lazy-loading of entries when
    a section is expanded in the tree view (US-5.11).

    Args:
        section_id: The section ID to get entries for
        limit: Maximum number of entries to return
        offset: Pagination offset

    Returns:
        Paginated list of entries from this section
    """
    # Verify section exists and get source info
    section = await repository.get_section_by_id(session, section_id)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section {section_id} not found")

    source = await repository.get_source_by_id(session, section.source_id)
    source_title = source.title if source else None

    entries, total = await repository.get_entries(
        session=session,
        section_id=section_id,
        limit=limit,
        offset=offset,
    )

    return EntriesListResponse(
        entries=[
            EntryResponse(
                id=e.id,  # type: ignore[arg-type]
                title=e.title,
                url=e.url,
                section_id=e.section_id,
                section_title=section.title,
                source_title=source_title,
                published_at=e.published_at,
                discovered_at=e.discovered_at,
                content_preview=e.content_preview,
            )
            for e in entries
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/entries/feed", response_model=FeedResponse)
async def get_feed(
    session: AsyncSession = Depends(get_session),
    repository: NewsRepository = Depends(get_news_repository),
    category_id: int | None = Query(None, description="Filter by category ID"),
    search: str | None = Query(None, description="Search in entry titles"),
    limit: int = Query(20, ge=1, le=100, description="Max entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> FeedResponse:
    """Get chronological news feed (US-5.14).

    Returns entries sorted by published_at (newest first) with fallback
    to discovered_at. Designed for infinite scroll UI.

    Args:
        category_id: Optional category filter
        search: Optional search term for titles
        limit: Maximum entries to return (default 20)
        offset: Pagination offset

    Returns:
        Feed entries with has_more indicator for infinite scroll
    """
    from ecox_shared.models import NewsCategory

    entries, total = await repository.get_feed_entries(
        session=session,
        category_id=category_id,
        search=search,
        limit=limit,
        offset=offset,
    )

    # Batch fetch section, source, and category info
    section_ids = {e.section_id for e in entries}
    section_map: dict[int, NewsSection] = {}
    source_map: dict[int, NewsSource] = {}
    category_map: dict[int, str] = {}

    if section_ids:
        sections_result = await session.exec(
            select(NewsSection).where(
                NewsSection.id.in_(section_ids)  # type: ignore[union-attr]
            )
        )
        sections = list(sections_result.all())
        section_map = {s.id: s for s in sections}  # type: ignore[misc]

        source_ids = {s.source_id for s in sections}
        if source_ids:
            sources_result = await session.exec(
                select(NewsSource).where(
                    NewsSource.id.in_(source_ids)  # type: ignore[union-attr]
                )
            )
            sources = list(sources_result.all())
            source_map = {s.id: s for s in sources}  # type: ignore[misc]

            category_ids = {s.category_id for s in sources if s.category_id}
            if category_ids:
                categories_result = await session.exec(
                    select(NewsCategory).where(
                        NewsCategory.id.in_(category_ids)  # type: ignore[union-attr]
                    )
                )
                category_map = {c.id: c.name for c in categories_result.all()}  # type: ignore[misc]

    # Build response entries with full metadata
    feed_entries = []
    for e in entries:
        section = section_map.get(e.section_id)
        source = source_map.get(section.source_id) if section else None
        category_name = (
            category_map.get(source.category_id) if source and source.category_id else None
        )

        feed_entries.append(
            FeedEntryResponse(
                id=e.id,  # type: ignore[arg-type]
                title=e.title,
                url=e.url,
                published_at=e.published_at,
                discovered_at=e.discovered_at,
                content_preview=e.content_preview,
                source_title=source.title if source else "Unknown",
                section_title=section.title if section else "Unknown",
                category_name=category_name or "Unknown",
            )
        )

    return FeedResponse(
        entries=feed_entries,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get("/entries/{entry_id}", response_model=EntryDetailResponse)
async def get_entry(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
    repository: NewsRepository = Depends(get_news_repository),
) -> EntryDetailResponse:
    """Get full entry details including content (US-5.12).

    This endpoint returns the complete entry with full content for
    display in a modal or detail view.

    Args:
        entry_id: The entry ID

    Returns:
        Entry with full content and metadata
    """
    entry = await repository.get_entry_by_id(session, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry {entry_id} not found")

    # Get section and source info
    section = await repository.get_section_by_id(session, entry.section_id)
    section_title = section.title if section else None
    source_id = section.source_id if section else None

    source_title = None
    if source_id:
        source = await repository.get_source_by_id(session, source_id)
        source_title = source.title if source else None

    return EntryDetailResponse(
        id=entry.id,  # type: ignore[arg-type]
        title=entry.title,
        url=entry.url,
        section_id=entry.section_id,
        section_title=section_title,
        source_id=source_id,
        source_title=source_title,
        published_at=entry.published_at,
        discovered_at=entry.discovered_at,
        content_full=entry.content_full,
        content_preview=entry.content_preview,
    )


@router.get("/entries", response_model=EntriesListResponse)
async def list_entries(
    session: AsyncSession = Depends(get_session),
    repository: NewsRepository = Depends(get_news_repository),
    section_id: int | None = Query(None, description="Filter by section ID"),
    source_id: int | None = Query(None, description="Filter by source ID"),
    category_id: int | None = Query(None, description="Filter by category ID"),
    since: datetime | None = Query(None, description="Filter entries since date"),
    search: str | None = Query(None, description="Search in entry titles"),
    limit: int = Query(10, ge=1, le=100, description="Max entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> EntriesListResponse:
    """List news entries with filtering and pagination.

    Args:
        section_id: Optional section ID filter
        source_id: Optional source ID filter
        category_id: Optional category ID filter
        since: Optional date filter (entries since this date)
        search: Optional search term for titles
        limit: Maximum number of entries to return
        offset: Pagination offset

    Returns:
        Paginated list of entries
    """
    entries, total = await repository.get_entries(
        session=session,
        section_id=section_id,
        source_id=source_id,
        category_id=category_id,
        since=since,
        search=search,
        limit=limit,
        offset=offset,
    )

    # Batch fetch section and source titles
    section_ids = {e.section_id for e in entries}
    section_map: dict[int, NewsSection] = {}
    source_map: dict[int, str] = {}

    if section_ids:
        sections_result = await session.exec(
            select(NewsSection).where(
                NewsSection.id.in_(section_ids)  # type: ignore[union-attr]
            )
        )
        sections = list(sections_result.all())
        section_map = {s.id: s for s in sections}  # type: ignore[misc]

        source_ids = {s.source_id for s in sections}
        if source_ids:
            sources_result = await session.exec(
                select(NewsSource).where(
                    NewsSource.id.in_(source_ids)  # type: ignore[union-attr]
                )
            )
            source_map = {s.id: s.title for s in sources_result.all()}  # type: ignore[misc]

    return EntriesListResponse(
        entries=[
            EntryResponse(
                id=e.id,  # type: ignore[arg-type]
                title=e.title,
                url=e.url,
                section_id=e.section_id,
                section_title=section_map[e.section_id].title
                if e.section_id in section_map
                else None,
                source_title=source_map.get(section_map[e.section_id].source_id)
                if e.section_id in section_map
                else None,
                published_at=e.published_at,
                discovered_at=e.discovered_at,
                content_preview=e.content_preview,
            )
            for e in entries
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/sections/{section_id}/refresh", response_model=FetchResultResponse)
async def refresh_section(
    section_id: int,
    session: AsyncSession = Depends(get_session),
    repository: NewsRepository = Depends(get_news_repository),
    service: NewsService = Depends(get_news_service),
) -> FetchResultResponse:
    """Manually refresh a specific section (US-5.13).

    Triggers an immediate fetch of the section regardless of its
    normal fetch interval.

    Args:
        section_id: The section ID to refresh

    Returns:
        Fetch result with entries found/new counts
    """
    # Verify section exists
    section = await repository.get_section_by_id(session, section_id)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section {section_id} not found")

    # Get source title
    source = await repository.get_source_by_id(session, section.source_id)
    source_title = source.title if source else "Unknown"

    # Fetch the section
    result = await service.fetch_section(session, section, source_title)

    return FetchResultResponse(
        section_id=result.section_id,
        section_title=result.section_title,
        source_title=result.source_title,
        status=result.status,
        entries_found=result.entries_found,
        entries_new=result.entries_new,
        error=result.error,
        duration_seconds=result.duration_seconds,
    )


@router.get("/status", response_model=NewsStatusResponse)
async def get_news_status() -> NewsStatusResponse:
    """Get news worker status.

    Returns:
        Current status of the news worker
    """
    try:
        worker = get_news_worker()
        status = worker.status()

        return NewsStatusResponse(
            is_running=status["is_running"],
            last_activity=(
                datetime.fromisoformat(status["last_activity"]) if status["last_activity"] else None
            ),
            sections_fetched=status["sections_fetched"],
            sections_failed=status["sections_failed"],
            entries_found=status["entries_found"],
            entries_new=status["entries_new"],
            current_section=status["current_section"],
            config=status["config"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get news status: {str(e)}",
        ) from e


@router.post("/fetch", response_model=dict[str, Any])
async def trigger_news_fetch(
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Trigger a news fetch cycle.

    This runs the fetch cycle in the background and returns immediately.

    Returns:
        Acknowledgment message
    """
    try:
        worker = get_news_worker()

        async def run_cycle() -> None:
            await worker.run_cycle()

        background_tasks.add_task(run_cycle)

        return {
            "status": "started",
            "message": "News fetch cycle triggered",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger news fetch: {str(e)}",
        ) from e


@router.post("/import", response_model=dict[str, Any])
async def import_news_sources(
    session: AsyncSession = Depends(get_session),
    service: NewsService = Depends(get_news_service),
) -> dict[str, Any]:
    """Import news sources and sections from config/news.yaml.

    This will create or update categories, sources, and sections in the database
    based on the configuration file.

    Returns:
        Import statistics
    """
    try:
        result = await service.import_from_config(session)

        return {
            "status": "success",
            "categories_created": result.categories_created,
            "categories_updated": result.categories_updated,
            "sources_created": result.sources_created,
            "sources_updated": result.sources_updated,
            "sections_created": result.sections_created,
            "sections_updated": result.sections_updated,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import sources: {str(e)}",
        ) from e


@router.get("/logs", response_model=list[dict[str, Any]])
async def get_fetch_logs(
    session: AsyncSession = Depends(get_session),
    repository: NewsRepository = Depends(get_news_repository),
    section_id: int | None = Query(None, description="Filter by section ID"),
    limit: int = Query(50, ge=1, le=200, description="Max logs to return"),
) -> list[dict[str, Any]]:
    """Get recent news fetch logs.

    Args:
        section_id: Optional section ID filter
        limit: Maximum number of logs to return

    Returns:
        List of recent fetch log entries
    """
    logs = await repository.get_fetch_logs(
        session=session,
        section_id=section_id,
        limit=limit,
    )

    return [
        {
            "id": log.id,
            "section_id": log.section_id,
            "status": log.status,
            "entries_found": log.entries_found,
            "entries_new": log.entries_new,
            "error_message": log.error_message,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "duration_seconds": log.duration_seconds,
        }
        for log in logs
    ]


async def news_event_generator(
    request: Request,
) -> AsyncGenerator[dict[str, str], None]:
    """Generate SSE events for news updates.

    Subscribes to the news event manager and yields events as they occur.

    Args:
        request: The incoming request (used to detect client disconnect)

    Yields:
        SSE event dictionaries with event type and data
    """
    event_manager = get_event_manager()

    try:
        async for event in event_manager.subscribe():
            if await request.is_disconnected():
                break
            yield {
                "event": event.event_type,
                "data": json.dumps(event.to_dict()),
            }
    except asyncio.CancelledError:
        pass


@router.get("/events")
async def news_sse_events(request: Request) -> EventSourceResponse:
    """SSE endpoint for real-time news updates.

    Establishes a Server-Sent Events connection to receive live updates
    when new entries are discovered.

    Event types:
    - new_entries: New entries discovered from a section

    Returns:
        EventSourceResponse streaming SSE events
    """
    return EventSourceResponse(news_event_generator(request))
