"""UI routes for the ecox client web interface.

These routes serve HTML templates for the htmx-based frontend.
Data is fetched from the ecox-data-platform API.
"""

from datetime import datetime
from typing import Any

import structlog
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from sqlmodel import select

from ecox_client.api.templates import get_template_context, templates
from ecox_client.infrastructure.database import get_db_manager
from ecox_client.infrastructure.platform_client import (
    PlatformClientError,
    get_platform_client,
)
from ecox_client.models import SourceActivation

logger = structlog.get_logger(__name__)

router = APIRouter()


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string to datetime object."""
    if not value:
        return None
    try:
        # Handle ISO format with or without timezone
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


async def get_source_activations() -> dict[str, bool]:
    """Get activation status for all sources from database.

    Returns:
        Dictionary mapping source_code to activated status.
        Sources not in database are considered activated by default.
    """
    db = get_db_manager()
    async with db.get_session() as session:
        result = await session.execute(select(SourceActivation))
        activations = result.scalars().all()
        return {a.source_code: a.activated for a in activations}


async def is_source_activated(source_code: str) -> bool:
    """Check if a source is activated.

    Args:
        source_code: The source code to check

    Returns:
        True if activated (or not in database), False if explicitly deactivated
    """
    activations = await get_source_activations()
    # Default to True if not in database
    return activations.get(source_code, True)


@router.get("/activated-sources-json")
async def get_activated_sources_json() -> list[dict[str, str]]:
    """Return list of activated sources as JSON for dynamic dropdown updates.

    Returns:
        List of activated sources with code and name.
    """
    try:
        client = get_platform_client()
        api_sources = await client.list_sources()
        activations = await get_source_activations()

        # Filter to only activated sources
        return [
            {"code": src["code"], "name": src["name"]}
            for src in api_sources
            if activations.get(src["code"], True)  # Default to activated
        ]
    except PlatformClientError as e:
        logger.error("Failed to fetch activated sources", error=str(e))
        return []


@router.post("/sources/{source_code}/activate", response_class=HTMLResponse)
async def toggle_source_activation(
    request: Request,
    source_code: str,
) -> HTMLResponse:
    """Toggle activation status for a data source.

    If the source is activated, it will be deactivated and vice versa.
    Returns the updated catalog modal HTML.
    """
    logger.info("Toggling source activation", source_code=source_code)

    db = get_db_manager()
    async with db.get_session() as session:
        # Get existing record or create new one
        result = await session.execute(
            select(SourceActivation).where(SourceActivation.source_code == source_code)
        )
        activation = result.scalar_one_or_none()

        if activation:
            # Toggle existing record
            activation.activated = not activation.activated
            activation.updated_at = datetime.now()
            logger.info(
                "Updated source activation",
                source_code=source_code,
                activated=activation.activated,
            )
        else:
            # Create new record (default is True, so toggling creates False)
            activation = SourceActivation(
                source_code=source_code,
                activated=False,  # First toggle deactivates
                updated_at=datetime.now(),
            )
            session.add(activation)
            logger.info(
                "Created source activation",
                source_code=source_code,
                activated=False,
            )

        await session.commit()

    # Return updated catalog modal
    return await catalog_sources(request)


@router.get("/sources", response_class=HTMLResponse)
async def list_sources(request: Request) -> HTMLResponse:
    """List all activated data sources with dataset counts.

    Fetches source data from the platform API, filters by activation status,
    and renders as HTML fragment. Only activated sources are shown.
    """
    logger.info("Fetching sources from platform")

    try:
        client = get_platform_client()
        api_sources = await client.list_sources()

        # Get activation status from database
        activations = await get_source_activations()

        # Transform API response to template format, filtering by activation
        sources = []
        for src in api_sources:
            source_code = src["code"]
            # Default to activated if not in database
            is_activated = activations.get(source_code, True)

            if is_activated:
                sources.append(
                    {
                        "name": source_code,
                        "dataset_count": src.get("dataset_count", 0),
                        "available_count": src.get("total_available", 0),
                        "last_activity": _parse_datetime(src.get("last_activity")),
                    }
                )

        # Sort by name
        sources.sort(key=lambda x: x["name"])

        logger.info("Loaded sources", count=len(sources))

    except PlatformClientError as e:
        logger.error("Platform API error", error=str(e))
        sources = []

    return templates.TemplateResponse(
        "partials/_sources_grid.html",
        get_template_context(request, sources=sources),
    )


@router.get("/datasets/{source}", response_class=HTMLResponse)
async def list_datasets(
    request: Request,
    source: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
) -> HTMLResponse:
    """List datasets for a source.

    Fetches dataset data from the platform API and renders as HTML fragment.
    """
    logger.info("Fetching datasets", source=source, page=page, search=search, status=status)

    try:
        client = get_platform_client()

        # Fetch datasets from platform
        filter_source = None if source == "all" else source
        result = await client.list_datasets(
            source=filter_source,
            search=search,
            page=page,
            page_size=page_size,
        )

        # Transform datasets to template format
        datasets = []
        for ds in result.get("items", []):
            datasets.append(
                {
                    "code": ds["code"],
                    "name": ds.get("name", ds["code"]),
                    "source": ds["source"],
                    "status": "downloaded",  # All datasets in platform are downloaded
                    "last_fetched": _parse_datetime(ds.get("last_fetched")),
                }
            )

        pagination = {
            "page": result.get("page", page),
            "page_size": result.get("page_size", page_size),
            "total_pages": result.get("total_pages", 1),
            "total": result.get("total", len(datasets)),
        }

        # Build filters for template
        filters = {
            "search": search,
            "status": status,
            "source": source if source != "all" else None,
        }

        # Get activated sources for filter dropdown
        api_sources = await client.list_sources()
        activated_sources = [{"code": s["code"], "name": s["name"]} for s in api_sources]

        logger.info("Loaded datasets", source=source, count=len(datasets))

    except PlatformClientError as e:
        logger.error("Platform API error", error=str(e))
        datasets = []
        pagination = {"page": 1, "page_size": page_size, "total_pages": 0, "total": 0}
        filters = {
            "search": search,
            "status": status,
            "source": source if source != "all" else None,
        }
        activated_sources = []

    return templates.TemplateResponse(
        "partials/_datasets_table.html",
        get_template_context(
            request,
            source=source,
            datasets=datasets,
            pagination=pagination,
            filters=filters,
            activated_sources=activated_sources,
        ),
    )


@router.get("/datasets-json")
async def list_datasets_json(
    source: str = Query("all", description="Filter by source"),
    since_id: int | None = Query(None, description="Only return datasets with id > since_id"),
) -> dict[str, Any]:
    """Get all datasets or incremental updates as JSON for client-side pagination.

    Returns datasets in a single JSON response for use with Alpine.js
    client-side pagination in the WebUI. Supports incremental fetching
    via the `since_id` parameter to fetch only new datasets.

    Args:
        source: Filter by source (default: "all" for all sources)
        since_id: Only return datasets with id > since_id (for incremental sync)

    Returns:
        Dict with items (datasets) and max_id for next sync
    """
    logger.info("Fetching datasets as JSON", source=source, since_id=since_id)

    try:
        client = get_platform_client()
        filter_source = None if source == "all" else source
        result = await client.list_all_datasets(source=filter_source, since_id=since_id)

        # Transform items to consistent format
        items = [
            {
                "id": ds["id"],
                "code": ds["code"],
                "name": ds.get("name", ds["code"]),
                "source": ds["source"],
                "description": ds.get("description"),
                "last_fetched": ds.get("last_fetched"),
                "record_count": ds.get("record_count", 0),
            }
            for ds in result.get("items", [])
        ]

        return {
            "items": items,
            "max_id": result.get("max_id"),
        }

    except PlatformClientError as e:
        logger.error("Platform API error fetching datasets JSON", error=str(e))
        return {"items": [], "max_id": None}


@router.get("/datasets/{source}/{code}", response_class=HTMLResponse)
async def dataset_detail(
    request: Request,
    source: str,
    code: str,
) -> HTMLResponse:
    """Get dataset details modal.

    Fetches dataset details from the platform API and renders as HTML modal.
    """
    logger.info("Fetching dataset details", source=source, code=code)

    try:
        client = get_platform_client()

        # Get dataset details
        dataset_data = await client.get_dataset(source, code)

        # Create dataset-like object for template
        class DatasetObj:
            def __init__(self, data: dict[str, Any]) -> None:
                self.id = data.get("id")
                self.code = data.get("code", code)
                self.name = data.get("name", code)
                self.source = data.get("source", source)
                self.description = data.get("description")
                self.last_fetched = _parse_datetime(data.get("last_fetched"))

        dataset = DatasetObj(dataset_data)

        # Get fetch logs for this dataset
        try:
            logs_result = await client.list_fetch_logs(
                source=source,
                dataset_code=code,
                page_size=5,
            )
            fetch_logs = logs_result.get("items", [])

            # Convert to objects with expected attributes
            class FetchLogObj:
                def __init__(self, data: dict[str, Any]) -> None:
                    self.started_at = _parse_datetime(data.get("started_at"))
                    self.status = data.get("status", "unknown")
                    self.records_fetched = data.get("records_fetched", 0)

            fetch_logs = [FetchLogObj(log) for log in fetch_logs]
        except Exception:
            fetch_logs = []

        # Dataset status
        is_downloaded = dataset.last_fetched is not None
        is_selected = True  # We don't have selection info in platform API yet

        # Extract source URL from API response
        source_url = dataset_data.get("source_url")

        logger.info("Loaded dataset details", source=source, code=code)

    except PlatformClientError as e:
        logger.error("Platform API error", error=str(e))

        # Create minimal dataset object for error case
        class MinimalDataset:
            def __init__(self) -> None:
                self.id = None
                self.code = code
                self.name = code
                self.source = source
                self.description = None
                self.last_fetched = None

        dataset = MinimalDataset()
        fetch_logs = []
        is_downloaded = False
        is_selected = False
        source_url = None

    return templates.TemplateResponse(
        "partials/_dataset_modal.html",
        get_template_context(
            request,
            dataset=dataset,
            fetch_logs=fetch_logs,
            is_selected=is_selected,
            is_downloaded=is_downloaded,
            metadata_url=source_url,
            description_html=None,
        ),
    )


@router.get("/catalog/sources", response_class=HTMLResponse)
async def catalog_sources(request: Request) -> HTMLResponse:
    """Get the catalog of available data sources.

    Returns HTML fragment with catalog modal content showing all sources
    with their activation status.
    """
    logger.info("Fetching source catalog")

    try:
        client = get_platform_client()
        api_sources = await client.list_sources()

        # Get activation status from database
        activations = await get_source_activations()

        # Transform to catalog format with real activation status
        catalog_data = []
        for src in api_sources:
            source_code = src["code"]
            # Default to activated if not in database
            is_activated = activations.get(source_code, True)

            catalog_data.append(
                {
                    "code": source_code,
                    "name": src["name"],
                    "description": src.get("description", ""),
                    "configured": True,  # All sources from API are configured
                    "activated": is_activated,
                    "api_url": "",  # Not exposed in platform API
                    "docs_url": "",  # Not exposed in platform API
                    "dataset_count_estimate": src.get("total_available", 0),
                }
            )

        logger.info("Loaded catalog", count=len(catalog_data))

    except PlatformClientError as e:
        logger.error("Platform API error", error=str(e))
        catalog_data = []

    return templates.TemplateResponse(
        "partials/_catalog_modal.html",
        get_template_context(request, sources=catalog_data),
    )


async def _fetch_and_transform_news_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch news data from platform and transform for templates.

    Returns:
        Tuple of (categories, entries) in template format
    """
    client = get_platform_client()

    # Fetch categories with sources and sections from platform
    api_categories = await client.list_news_categories()

    # Fetch recent entries
    entries_result = await client.list_news_entries(limit=20)

    # Transform to template format (hierarchical)
    categories = []
    for cat in api_categories:
        sources = []
        for src in cat.get("sources", []):
            sections = []
            for sec in src.get("sections", []):
                sections.append(
                    {
                        "id": sec["id"],
                        "title": sec["title"],
                        "url": sec["url"],
                        "is_active": sec.get("is_active", False),
                        "last_fetched_at": _parse_datetime(sec.get("last_fetched_at")),
                        "last_fetch_status": sec.get("last_fetch_status"),
                        "last_fetch_error": sec.get("last_fetch_error"),
                        "entry_count": sec.get("entry_count", 0),
                    }
                )
            sources.append(
                {
                    "id": src["id"],
                    "title": src["title"],
                    "description": src.get("description"),
                    "is_active": src.get("is_active", False),
                    "sections": sections,
                    "section_count": src.get("section_count", 0),
                    "entry_count": src.get("entry_count", 0),
                }
            )
        categories.append(
            {
                "id": cat["id"],
                "name": cat["name"],
                "sources": sources,
                "source_count": cat.get("source_count", 0),
                "section_count": cat.get("section_count", 0),
                "total_entries": cat.get("total_entries", 0),
            }
        )

    # Transform entries
    entries = [
        {
            "id": ent["id"],
            "title": ent["title"],
            "url": ent["url"],
            "section_title": ent.get("section_title"),
            "source_title": ent.get("source_title"),
            "published_at": _parse_datetime(ent.get("published_at")),
            "discovered_at": _parse_datetime(ent.get("discovered_at")),
            "content_preview": ent.get("content_preview"),
        }
        for ent in entries_result.get("entries", [])
    ]

    return categories, entries


@router.get("/news", response_class=HTMLResponse)
async def list_news(request: Request) -> HTMLResponse:
    """Main news endpoint - chronological feed (US-5.14).

    Returns the new feed view with category filters, search, and infinite scroll.
    Replaces the old hierarchical tree view.
    """
    # Delegate to the feed endpoint for the new UI
    return await get_news_feed(request, category_id=None, search=None)


@router.get("/news/tree", response_class=HTMLResponse)
async def list_news_tree(request: Request) -> HTMLResponse:
    """List news with hierarchical tree view (legacy/deprecated).

    Fetches news data from the platform API and renders as HTML fragment.
    Shows categories with sources, sections, and entry counts.

    Note: This is the legacy view. The new feed view at /news is now the default.
    """
    logger.info("Fetching news tree from platform")

    try:
        categories, entries = await _fetch_and_transform_news_data()
        logger.info(
            "Loaded news tree",
            categories=len(categories),
            entries=len(entries),
        )

    except PlatformClientError as e:
        logger.error("Platform API error fetching news tree", error=str(e))
        categories = []
        entries = []

    return templates.TemplateResponse(
        "partials/_news_list.html",
        get_template_context(request, categories=categories, entries=entries),
    )


@router.get("/news/sections/{section_id}/entries", response_class=HTMLResponse)
async def list_section_entries(
    request: Request,
    section_id: int,
) -> HTMLResponse:
    """List entries for a section (htmx lazy-loading).

    Called when a section is expanded in the tree view.
    Returns entries directly without additional grouping.

    Args:
        section_id: Section ID
    """
    logger.info("Fetching section entries", section_id=section_id)

    try:
        client = get_platform_client()
        # Fetch entries (platform API limit is 100)
        result = await client.list_section_entries(section_id, limit=100, offset=0)

        entries = [
            {
                "id": ent["id"],
                "title": ent["title"],
                "url": ent["url"],
                "published_at": _parse_datetime(ent.get("published_at")),
                "discovered_at": _parse_datetime(ent.get("discovered_at")),
            }
            for ent in result.get("entries", [])
        ]

    except PlatformClientError as e:
        logger.error("Platform API error fetching entries", error=str(e))
        entries = []

    return templates.TemplateResponse(
        "partials/_news_section_entries.html",
        get_template_context(
            request,
            entries=entries,
            section_id=section_id,
        ),
    )


@router.get("/news/entries/{entry_id}", response_class=HTMLResponse)
async def get_entry_detail(
    request: Request,
    entry_id: int,
) -> HTMLResponse:
    """Get entry detail modal with full content (US-5.12).

    Args:
        entry_id: Entry ID
    """
    logger.info("Fetching entry detail", entry_id=entry_id)

    try:
        client = get_platform_client()
        entry_data = await client.get_entry(entry_id)

        entry = {
            "id": entry_data["id"],
            "title": entry_data["title"],
            "url": entry_data["url"],
            "section_title": entry_data.get("section_title"),
            "source_title": entry_data.get("source_title"),
            "published_at": _parse_datetime(entry_data.get("published_at")),
            "discovered_at": _parse_datetime(entry_data.get("discovered_at")),
            "content_full": entry_data.get("content_full"),
            "content_preview": entry_data.get("content_preview"),
        }

    except PlatformClientError as e:
        logger.error("Platform API error fetching entry", error=str(e))
        entry = None

    return templates.TemplateResponse(
        "partials/_news_entry_modal.html",
        get_template_context(request, entry=entry),
    )


@router.post("/news/sections/{section_id}/refresh", response_class=HTMLResponse)
async def refresh_section(
    request: Request,
    section_id: int,
) -> HTMLResponse:
    """Manually refresh a section (US-5.13).

    Args:
        section_id: Section ID to refresh
    """
    logger.info("Refreshing section", section_id=section_id)

    toast = None
    try:
        client = get_platform_client()
        result = await client.refresh_section(section_id)

        if result.get("status") == "success":
            entries_new = result.get("entries_new", 0)
            toast = {
                "message": f"Section refreshed: {entries_new} new entries found",
                "type": "success",
            }
        else:
            error = result.get("error", "Unknown error")
            toast = {
                "message": f"Refresh failed: {error[:100]}",
                "type": "error",
            }

    except PlatformClientError as e:
        logger.error("Platform API error refreshing section", error=str(e))
        toast = {
            "message": f"Refresh failed: {str(e)[:100]}",
            "type": "error",
        }

    # Return the full news list with toast
    return await list_news_with_toast(request, toast)


async def list_news_with_toast(
    request: Request,
    toast: dict[str, str] | None = None,
) -> HTMLResponse:
    """Render feed with optional toast notification.

    Helper function to render the feed after an action
    like refreshing a section.
    """
    try:
        client = get_platform_client()

        # Get feed entries
        feed_result = await client.get_news_feed(limit=20, offset=0)
        categories = await client.list_news_categories()

        entries = [
            {
                "id": e["id"],
                "title": e["title"],
                "url": e["url"],
                "source_title": e["source_title"],
                "section_title": e["section_title"],
                "category_name": e["category_name"],
                "published_at": _parse_datetime(e.get("published_at")),
                "discovered_at": _parse_datetime(e.get("discovered_at")),
                "content_preview": e.get("content_preview"),
            }
            for e in feed_result.get("entries", [])
        ]
        entry_ids = [e["id"] for e in entries]

    except PlatformClientError as e:
        logger.error("Platform API error fetching feed", error=str(e))
        entries = []
        categories = []
        entry_ids = []
        feed_result = {"total": 0, "has_more": False}

    return templates.TemplateResponse(
        "partials/_news_feed.html",
        get_template_context(
            request,
            entries=entries,
            entry_ids=entry_ids,
            categories=categories,
            total=feed_result.get("total", 0),
            has_more=feed_result.get("has_more", False),
            limit=20,
            offset=0,
            selected_category=None,
            search=None,
            toast=toast,
        ),
    )


# --- News Feed Routes (US-5.14, US-5.15, US-5.16) ---


@router.get("/news/feed", response_class=HTMLResponse)
async def get_news_feed(
    request: Request,
    category_id: int | None = Query(None),
    search: str | None = Query(None),
) -> HTMLResponse:
    """Get chronological news feed (US-5.14).

    Returns the full feed template with header, filters, and cards.
    """
    logger.info("Fetching news feed", category_id=category_id, search=search)

    try:
        client = get_platform_client()

        # Get feed entries
        feed_result = await client.get_news_feed(
            category_id=category_id,
            search=search,
            limit=20,
            offset=0,
        )

        # Get categories for filter chips
        categories = await client.list_news_categories()

        # Transform entries for template
        entries = [
            {
                "id": e["id"],
                "title": e["title"],
                "url": e["url"],
                "source_title": e["source_title"],
                "section_title": e["section_title"],
                "category_name": e["category_name"],
                "published_at": _parse_datetime(e.get("published_at")),
                "discovered_at": _parse_datetime(e.get("discovered_at")),
                "content_preview": e.get("content_preview"),
            }
            for e in feed_result.get("entries", [])
        ]

        entry_ids = [e["id"] for e in entries]

    except PlatformClientError as e:
        logger.error("Platform API error fetching feed", error=str(e))
        entries = []
        categories = []
        entry_ids = []
        feed_result = {"total": 0, "has_more": False}

    return templates.TemplateResponse(
        "partials/_news_feed.html",
        get_template_context(
            request,
            entries=entries,
            entry_ids=entry_ids,
            categories=categories,
            total=feed_result.get("total", 0),
            has_more=feed_result.get("has_more", False),
            limit=20,
            offset=0,
            selected_category=category_id,
            search=search,
        ),
    )


@router.get("/news/feed/more", response_class=HTMLResponse)
async def get_news_feed_more(
    request: Request,
    offset: int = Query(0, ge=0),
    category_id: int | None = Query(None),
    search: str | None = Query(None),
) -> HTMLResponse:
    """Get more feed cards for infinite scroll (US-5.14).

    Returns just the cards partial for htmx to append.
    """
    logger.info("Fetching more feed entries", offset=offset, category_id=category_id)

    try:
        client = get_platform_client()
        feed_result = await client.get_news_feed(
            category_id=category_id,
            search=search,
            limit=20,
            offset=offset,
        )

        entries = [
            {
                "id": e["id"],
                "title": e["title"],
                "url": e["url"],
                "source_title": e["source_title"],
                "section_title": e["section_title"],
                "category_name": e["category_name"],
                "published_at": _parse_datetime(e.get("published_at")),
                "discovered_at": _parse_datetime(e.get("discovered_at")),
                "content_preview": e.get("content_preview"),
            }
            for e in feed_result.get("entries", [])
        ]

    except PlatformClientError as e:
        logger.error("Platform API error fetching more feed", error=str(e))
        entries = []
        feed_result = {"has_more": False}

    return templates.TemplateResponse(
        "partials/_news_feed_cards.html",
        get_template_context(
            request,
            entries=entries,
            has_more=feed_result.get("has_more", False),
            limit=20,
            offset=offset,
            selected_category=category_id,
            search=search,
        ),
    )


@router.get("/news/entries/{entry_id}/panel", response_class=HTMLResponse)
async def get_entry_panel(
    request: Request,
    entry_id: int,
    mobile: bool = Query(False),
) -> HTMLResponse:
    """Get entry detail panel for slide-in view (US-5.15).

    Args:
        entry_id: Entry ID
        mobile: Whether this is for mobile full-screen overlay
    """
    logger.info("Fetching entry panel", entry_id=entry_id, mobile=mobile)

    try:
        client = get_platform_client()
        entry_data = await client.get_entry(entry_id)

        entry = {
            "id": entry_data["id"],
            "title": entry_data["title"],
            "url": entry_data["url"],
            "section_title": entry_data.get("section_title"),
            "source_title": entry_data.get("source_title"),
            "published_at": _parse_datetime(entry_data.get("published_at")),
            "discovered_at": _parse_datetime(entry_data.get("discovered_at")),
            "content_full": entry_data.get("content_full"),
            "content_preview": entry_data.get("content_preview"),
        }

    except PlatformClientError as e:
        logger.error("Platform API error fetching entry panel", error=str(e))
        entry = None

    return templates.TemplateResponse(
        "partials/_news_detail_panel.html",
        get_template_context(request, entry=entry, mobile=mobile),
    )
