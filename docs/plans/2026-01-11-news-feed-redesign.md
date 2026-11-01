# News Feed Redesign Implementation Plan

## Overview

Replace the hierarchical tree view (Category → Source → Section → Entry) with a flat chronological feed and slide-in detail panel. This implements US-5.14, US-5.15, and US-5.16 from Epic 5.

## Current State Analysis

### What Exists

| Component | File | Description |
|-----------|------|-------------|
| Tree UI | `ecox-client/templates/partials/_news_list.html` | 277-line accordion tree with `newsTree()` Alpine.js |
| Modal | `ecox-client/templates/partials/_news_entry_modal.html` | Center modal with scale animation |
| Client Routes | `ecox-client/src/ecox_client/api/routes/ui.py:535-707` | `/news`, `/news/sections/{id}/entries`, `/news/entries/{id}` |
| Backend API | `ecox-data-platform/src/ecox_platform/api/routes/news.py:377-459` | `/entries` endpoint with filters |
| Repository | `ecox-data-platform/src/ecox_platform/news/repository.py:285-343` | `get_entries()` ordered by `discovered_at DESC` |

### Key Discoveries

1. **Repository already supports filtering**: `get_entries()` handles `category_id`, `source_id`, `section_id`, `since`, `search`, `limit`, `offset`
2. **Missing sorting**: Currently orders by `discovered_at DESC`, needs `published_at DESC NULLS LAST` with fallback
3. **Missing response fields**: Need `has_more` boolean and `category_name` in entry response
4. **Existing patterns**: Toast notifications use `translate-x` slide-in (see `base.html:136-171`)

## Desired End State

After implementation:
- News tab displays a flat chronological feed of entry cards (newest first)
- Clicking a card opens a right-side detail panel (not a modal)
- Infinite scroll loads more entries as user scrolls down
- Category filter chips and search bar at the top
- Skeleton loading states during fetches
- Mobile: panel becomes full-screen overlay

### Verification
- All BDD scenarios in `ecox-client/tests/features/epic05_news_aggregation.feature` tagged `@us-5.14`, `@us-5.15`, `@us-5.16` pass
- Old tree view and modal code removed
- No regressions in existing news functionality

## What We're NOT Doing

- Preserving the tree view as an alternative (complete replacement)
- Time range filter (last 24h, last week) - can be added later
- Source-level filtering (only category-level)
- Keyboard shortcuts beyond Escape and arrow keys
- Virtualized scrolling (standard infinite scroll is sufficient)

## Implementation Approach

Four phases: Backend API → Feed UI → Detail Panel → Integration & Cleanup

---

## Phase 1: Backend - Feed Endpoint

### Overview
Add a dedicated feed endpoint with proper sorting and response format for infinite scroll.

### Changes Required

#### 1. Repository - Add Feed Query Method
**File**: `ecox-data-platform/src/ecox_platform/news/repository.py`
**Changes**: Add `get_feed_entries()` method with `published_at` sorting

```python
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
    """
    # Base query with proper ordering for feed
    query = (
        select(NewsEntry)
        .order_by(
            col(NewsEntry.published_at).desc().nulls_last(),
            col(NewsEntry.discovered_at).desc(),
        )
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
```

#### 2. API Routes - Add Feed Endpoint
**File**: `ecox-data-platform/src/ecox_platform/api/routes/news.py`
**Changes**: Add response model and endpoint

```python
# Add new response model after EntriesListResponse (around line 124)
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


# Add endpoint after list_entries (around line 460)
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
        section_map = {s.id: s for s in sections}

        source_ids = {s.source_id for s in sections}
        if source_ids:
            sources_result = await session.exec(
                select(NewsSource).where(
                    NewsSource.id.in_(source_ids)  # type: ignore[union-attr]
                )
            )
            sources = list(sources_result.all())
            source_map = {s.id: s for s in sources}

            category_ids = {s.category_id for s in sources if s.category_id}
            if category_ids:
                categories_result = await session.exec(
                    select(NewsCategory).where(
                        NewsCategory.id.in_(category_ids)  # type: ignore[union-attr]
                    )
                )
                category_map = {c.id: c.name for c in categories_result.all()}

    # Build response entries with full metadata
    feed_entries = []
    for e in entries:
        section = section_map.get(e.section_id)
        source = source_map.get(section.source_id) if section else None
        category_name = category_map.get(source.category_id) if source and source.category_id else "Unknown"

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
                category_name=category_name,
            )
        )

    return FeedResponse(
        entries=feed_entries,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )
```

#### 3. Platform Client - Add Feed Method
**File**: `ecox-client/src/ecox_client/infrastructure/platform_client.py`
**Changes**: Add method to call the new feed endpoint

```python
async def get_news_feed(
    self,
    category_id: int | None = None,
    search: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Get chronological news feed.

    Args:
        category_id: Optional category filter
        search: Optional search term
        limit: Max entries to return
        offset: Pagination offset

    Returns:
        Feed response with entries and has_more indicator
    """
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if category_id is not None:
        params["category_id"] = category_id
    if search:
        params["search"] = search

    return await self._get("/news/entries/feed", params=params)
```

### Success Criteria

#### Automated Verification:
- [ ] Type checking passes: `cd ecox-data-platform && uv run pyright src/`
- [ ] Tests pass: `cd ecox-data-platform && uv run pytest tests/unit/test_news_routes.py -v`
- [ ] Linting passes: `cd ecox-data-platform && uv run pre-commit run --all`
- [ ] API endpoint returns 200: `curl "http://localhost:8000/api/news/entries/feed?limit=5"`

#### Manual Verification:
- [ ] Feed returns entries sorted by `published_at` (newest first)
- [ ] Entries without `published_at` appear after those with dates
- [ ] `has_more` is `true` when more entries exist
- [ ] Category filter works correctly
- [ ] Search filter works correctly

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 2.

---

## Phase 2: Frontend - Feed Cards UI

### Overview
Create the chronological feed UI with card stack, category filter chips, search bar, and infinite scroll.

### Changes Required

#### 1. New Feed Template
**File**: `ecox-client/templates/partials/_news_feed.html` (NEW)
**Changes**: Create main feed container with header, filters, and card list

```html
{% if toast %}
<!-- Toast notification trigger -->
<script>
    window.dispatchEvent(new CustomEvent('show-toast', {
        detail: { message: {{ toast.message|tojson }}, type: {{ toast.type|tojson }} }
    }));
</script>
{% endif %}

<!-- News Feed Container (US-5.14) -->
<div x-data="newsFeed()" class="h-full flex flex-col">

    <!-- Header -->
    <div class="flex-shrink-0 mb-4">
        <div class="flex items-center justify-between mb-4">
            <div>
                <h2 class="text-xl font-semibold text-slate-900 dark:text-slate-100">{{ t('news.title') }}</h2>
                <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
                    {% if total > 0 %}
                    {{ total }} {{ t('news.entries_total') }}
                    {% endif %}
                </p>
            </div>
            <!-- Refresh button -->
            <button
                type="button"
                class="p-2 text-slate-400 hover:text-blue-500 transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
                hx-post="/api/news/fetch"
                hx-swap="none"
                title="{{ t('news.refresh') }}"
            >
                <svg class="h-5 w-5 htmx-indicator-rotate" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
            </button>
        </div>

        <!-- Search Bar -->
        <div class="relative mb-4">
            <input
                type="text"
                x-model="searchQuery"
                @input.debounce.300ms="applyFilters()"
                placeholder="{{ t('news.search_placeholder') }}"
                class="w-full pl-10 pr-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <svg class="absolute left-3 top-2.5 h-5 w-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
        </div>

        <!-- Category Filter Chips -->
        <div class="flex flex-wrap gap-2">
            <button
                type="button"
                @click="selectCategory(null)"
                :class="selectedCategory === null
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'"
                class="px-3 py-1.5 text-sm font-medium rounded-full transition-colors"
            >
                {{ t('news.all_categories') }}
            </button>
            {% for category in categories %}
            <button
                type="button"
                @click="selectCategory({{ category.id }})"
                :class="selectedCategory === {{ category.id }}
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'"
                class="px-3 py-1.5 text-sm font-medium rounded-full transition-colors"
            >
                {{ category.name }}
            </button>
            {% endfor %}
        </div>
    </div>

    <!-- Feed Content Area (master-detail layout) -->
    <div class="flex-1 flex gap-4 min-h-0 overflow-hidden">

        <!-- Feed Cards (scrollable) -->
        <div
            id="feed-cards-container"
            class="flex-1 overflow-y-auto pr-2"
            :class="{ 'lg:w-1/2': selectedEntry !== null }"
        >
            <div id="feed-cards" class="space-y-3">
                {% if entries %}
                {% for entry in entries %}
                {% include "partials/_news_feed_card.html" %}
                {% endfor %}

                {% if has_more %}
                <!-- Infinite scroll sentinel -->
                <div
                    hx-get="/api/news/feed/more?offset={{ offset + limit }}{% if selected_category %}&category_id={{ selected_category }}{% endif %}{% if search %}&search={{ search }}{% endif %}"
                    hx-trigger="revealed"
                    hx-swap="outerHTML"
                    class="py-4 text-center"
                >
                    <div class="inline-flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                        <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        {{ t('news.loading_more') }}
                    </div>
                </div>
                {% endif %}

                {% else %}
                <!-- Empty state -->
                <div class="flex flex-col items-center justify-center py-16 px-4">
                    <svg class="h-16 w-16 text-slate-300 dark:text-slate-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                            d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                    </svg>
                    <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">{{ t('news.empty_title') }}</h3>
                    <p class="text-sm text-slate-600 dark:text-slate-400">{{ t('news.empty_description') }}</p>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- Detail Panel (US-5.15) -->
        <div
            x-show="selectedEntry !== null"
            x-transition:enter="transition ease-out duration-300"
            x-transition:enter-start="translate-x-full opacity-0"
            x-transition:enter-end="translate-x-0 opacity-100"
            x-transition:leave="transition ease-in duration-200"
            x-transition:leave-start="translate-x-0 opacity-100"
            x-transition:leave-end="translate-x-full opacity-0"
            @keydown.escape.window="closePanel()"
            @keydown.arrow-down.window="nextEntry()"
            @keydown.arrow-up.window="prevEntry()"
            class="hidden lg:block w-1/2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden"
        >
            <div id="detail-panel-content">
                <!-- Content loaded via htmx -->
            </div>
        </div>
    </div>

    <!-- Mobile Detail Panel (full-screen overlay) -->
    <div
        x-show="selectedEntry !== null"
        x-transition:enter="transition ease-out duration-300"
        x-transition:enter-start="translate-x-full"
        x-transition:enter-end="translate-x-0"
        x-transition:leave="transition ease-in duration-200"
        x-transition:leave-start="translate-x-0"
        x-transition:leave-end="translate-x-full"
        @keydown.escape.window="closePanel()"
        class="lg:hidden fixed inset-0 z-50 bg-white dark:bg-slate-900"
    >
        <div id="mobile-detail-panel-content">
            <!-- Content loaded via htmx -->
        </div>
    </div>
</div>

<script>
function newsFeed() {
    return {
        selectedEntry: null,
        selectedCategory: {{ selected_category|tojson if selected_category else 'null' }},
        searchQuery: {{ search|tojson if search else '""' }},
        entryIds: {{ entry_ids|tojson if entry_ids else '[]' }},
        currentIndex: -1,

        selectEntry(entryId) {
            this.selectedEntry = entryId;
            this.currentIndex = this.entryIds.indexOf(entryId);

            // Load detail panel content
            htmx.ajax('GET', `/api/news/entries/${entryId}/panel`, {
                target: '#detail-panel-content',
                swap: 'innerHTML'
            });

            // Also load mobile panel
            htmx.ajax('GET', `/api/news/entries/${entryId}/panel?mobile=true`, {
                target: '#mobile-detail-panel-content',
                swap: 'innerHTML'
            });
        },

        closePanel() {
            this.selectedEntry = null;
            this.currentIndex = -1;
        },

        nextEntry() {
            if (this.selectedEntry === null) return;
            if (this.currentIndex < this.entryIds.length - 1) {
                this.selectEntry(this.entryIds[this.currentIndex + 1]);
            }
        },

        prevEntry() {
            if (this.selectedEntry === null) return;
            if (this.currentIndex > 0) {
                this.selectEntry(this.entryIds[this.currentIndex - 1]);
            }
        },

        selectCategory(categoryId) {
            this.selectedCategory = categoryId;
            this.applyFilters();
        },

        applyFilters() {
            const params = new URLSearchParams();
            if (this.selectedCategory !== null) {
                params.set('category_id', this.selectedCategory);
            }
            if (this.searchQuery) {
                params.set('search', this.searchQuery);
            }

            const url = '/api/news/feed' + (params.toString() ? '?' + params.toString() : '');
            htmx.ajax('GET', url, {
                target: '#news-content',
                swap: 'innerHTML'
            });
        }
    };
}
</script>

<style>
.htmx-request .htmx-indicator-rotate {
    animation: spin 1s linear infinite;
}
@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}
</style>
```

#### 2. Feed Card Component
**File**: `ecox-client/templates/partials/_news_feed_card.html` (NEW)
**Changes**: Create individual card component

```html
<!-- News Feed Card (US-5.14) -->
<button
    type="button"
    @click="selectEntry({{ entry.id }})"
    :class="{ 'ring-2 ring-blue-500 bg-blue-50 dark:bg-blue-900/20': selectedEntry === {{ entry.id }} }"
    class="w-full text-left bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-md transition-all cursor-pointer"
>
    <!-- Source & Time -->
    <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-2">
        <span class="font-medium text-slate-700 dark:text-slate-300">{{ entry.source_title }}</span>
        <span>&middot;</span>
        <span>{{ entry.section_title }}</span>
        <span>&middot;</span>
        <time datetime="{{ entry.published_at.isoformat() if entry.published_at else entry.discovered_at.isoformat() }}">
            {% if entry.published_at %}
            {{ entry.published_at | timeago }}
            {% else %}
            {{ entry.discovered_at | timeago }}
            {% endif %}
        </time>
    </div>

    <!-- Title -->
    <h3 class="text-sm font-medium text-slate-900 dark:text-slate-100 line-clamp-2 leading-snug">
        {{ entry.title }}
    </h3>

    <!-- Preview (optional) -->
    {% if entry.content_preview %}
    <p class="mt-2 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
        {{ entry.content_preview[:150] }}{% if entry.content_preview|length > 150 %}...{% endif %}
    </p>
    {% endif %}
</button>
```

#### 3. Feed Cards Partial (for infinite scroll)
**File**: `ecox-client/templates/partials/_news_feed_cards.html` (NEW)
**Changes**: Partial that returns just cards for infinite scroll loading

```html
<!-- Additional feed cards loaded via infinite scroll -->
{% for entry in entries %}
{% include "partials/_news_feed_card.html" %}
{% endfor %}

{% if has_more %}
<!-- Next infinite scroll sentinel -->
<div
    hx-get="/api/news/feed/more?offset={{ offset + limit }}{% if selected_category %}&category_id={{ selected_category }}{% endif %}{% if search %}&search={{ search }}{% endif %}"
    hx-trigger="revealed"
    hx-swap="outerHTML"
    class="py-4 text-center"
>
    <div class="inline-flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        {{ t('news.loading_more') }}
    </div>
</div>
{% endif %}
```

#### 4. Skeleton Loading Template
**File**: `ecox-client/templates/partials/_news_feed_skeleton.html` (NEW)
**Changes**: Create skeleton loading state for initial load

```html
<!-- Feed Skeleton Loading State (US-5.16) -->
<div class="space-y-3 animate-pulse">
    {% for _ in range(5) %}
    <div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
        <!-- Source & time skeleton -->
        <div class="flex items-center gap-2 mb-2">
            <div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-24"></div>
            <div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-16"></div>
        </div>
        <!-- Title skeleton -->
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-2"></div>
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
        <!-- Preview skeleton -->
        <div class="mt-2 h-3 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
    </div>
    {% endfor %}
</div>
```

#### 5. Client Routes - Feed Endpoints
**File**: `ecox-client/src/ecox_client/api/routes/ui.py`
**Changes**: Add routes for feed and infinite scroll

```python
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
```

#### 6. Timeago Filter
**File**: `ecox-client/src/ecox_client/api/templates.py`
**Changes**: Add Jinja2 filter for relative time display

```python
from datetime import datetime, UTC

def timeago(value: datetime | None) -> str:
    """Convert datetime to relative time string (e.g., '2 hours ago')."""
    if value is None:
        return ""

    now = datetime.now(UTC).replace(tzinfo=None)
    if value.tzinfo:
        value = value.replace(tzinfo=None)

    diff = now - value
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days}d ago"
    else:
        return value.strftime("%b %d")

# Register filter in templates setup
templates.env.filters["timeago"] = timeago
```

### Success Criteria

#### Automated Verification:
- [ ] Type checking passes: `cd ecox-client && uv run pyright src/`
- [ ] Linting passes: `cd ecox-client && uv run pre-commit run --all`
- [ ] Templates render without errors

#### Manual Verification:
- [ ] Feed displays cards sorted by date (newest first)
- [ ] Category filter chips work (clicking filters the feed)
- [ ] Search bar filters entries by title
- [ ] Infinite scroll loads more entries when scrolling to bottom
- [ ] Skeleton loading shows during initial load
- [ ] "Loading more..." indicator shows during infinite scroll

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 3.

---

## Phase 3: Frontend - Detail Panel

### Overview
Create the slide-in detail panel that replaces the modal.

### Changes Required

#### 1. Detail Panel Template
**File**: `ecox-client/templates/partials/_news_detail_panel.html` (NEW)
**Changes**: Create the slide-in panel content

```html
{% if entry %}
<!-- Detail Panel Content (US-5.15) -->
<div class="h-full flex flex-col">
    <!-- Header -->
    <div class="flex-shrink-0 px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
        <div class="flex items-start justify-between gap-3">
            <div class="flex-1 min-w-0">
                <h2 class="text-base font-semibold text-slate-900 dark:text-slate-100 line-clamp-2">
                    {{ entry.title }}
                </h2>
                <div class="flex items-center gap-2 mt-1 text-xs text-slate-500 dark:text-slate-400">
                    <span class="font-medium">{{ entry.source_title }}</span>
                    {% if entry.section_title %}
                    <span>&middot;</span>
                    <span>{{ entry.section_title }}</span>
                    {% endif %}
                    {% if entry.published_at %}
                    <span>&middot;</span>
                    <time datetime="{{ entry.published_at.isoformat() }}">
                        {{ entry.published_at.strftime('%B %d, %Y') }}
                    </time>
                    {% endif %}
                </div>
            </div>
            <button
                type="button"
                @click="closePanel()"
                class="flex-shrink-0 p-1.5 -m-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                aria-label="{{ t('common.close') }}"
            >
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto px-4 py-4">
        {% if entry.content_full %}
        <div class="prose prose-slate dark:prose-invert prose-sm max-w-none">
            {% for paragraph in entry.content_full.split('\n\n') %}
            {% if paragraph.strip() %}
            <p class="mb-4 text-slate-700 dark:text-slate-300 leading-relaxed">{{ paragraph.strip() }}</p>
            {% endif %}
            {% endfor %}
        </div>
        {% elif entry.content_preview %}
        <div class="prose prose-slate dark:prose-invert prose-sm max-w-none">
            <p class="text-slate-700 dark:text-slate-300 leading-relaxed">{{ entry.content_preview }}</p>
            <p class="text-slate-500 dark:text-slate-400 italic text-xs mt-4">{{ t('news.content_preview_only') }}</p>
        </div>
        {% else %}
        <div class="py-8 text-center">
            <svg class="mx-auto h-12 w-12 text-slate-300 dark:text-slate-600 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p class="text-sm text-slate-500 dark:text-slate-400">{{ t('news.no_content_available') }}</p>
        </div>
        {% endif %}
    </div>

    <!-- Footer -->
    <div class="flex-shrink-0 px-4 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
        <div class="flex items-center justify-between">
            <a
                href="{{ entry.url }}"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
            >
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                {{ t('news.open_original') }}
            </a>
            <!-- Keyboard hints -->
            <div class="hidden sm:flex items-center gap-3 text-xs text-slate-400 dark:text-slate-500">
                <span class="flex items-center gap-1">
                    <kbd class="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px]">↑</kbd>
                    <kbd class="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px]">↓</kbd>
                    navigate
                </span>
                <span class="flex items-center gap-1">
                    <kbd class="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px]">Esc</kbd>
                    close
                </span>
            </div>
        </div>
    </div>
</div>
{% else %}
<!-- Error state -->
<div class="h-full flex items-center justify-center">
    <div class="text-center p-6">
        <svg class="mx-auto h-12 w-12 text-red-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2">{{ t('news.entry_not_found') }}</h3>
        <p class="text-sm text-slate-600 dark:text-slate-400">{{ t('news.entry_load_error') }}</p>
    </div>
</div>
{% endif %}
```

#### 2. Mobile Panel Template
**File**: `ecox-client/templates/partials/_news_detail_panel_mobile.html` (NEW)
**Changes**: Full-screen mobile version with back button

```html
{% if entry %}
<!-- Mobile Detail Panel (US-5.15) -->
<div class="h-full flex flex-col bg-white dark:bg-slate-900">
    <!-- Header with back button -->
    <div class="flex-shrink-0 px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 sticky top-0 z-10">
        <div class="flex items-center gap-3">
            <button
                type="button"
                @click="closePanel()"
                class="p-2 -ml-2 text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
                aria-label="{{ t('common.back') }}"
            >
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                </svg>
            </button>
            <div class="flex-1 min-w-0">
                <span class="text-sm font-medium text-slate-500 dark:text-slate-400">{{ entry.source_title }}</span>
            </div>
        </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto">
        <div class="px-4 py-4">
            <h1 class="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">
                {{ entry.title }}
            </h1>
            <div class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 mb-6">
                {% if entry.section_title %}
                <span>{{ entry.section_title }}</span>
                <span>&middot;</span>
                {% endif %}
                {% if entry.published_at %}
                <time datetime="{{ entry.published_at.isoformat() }}">
                    {{ entry.published_at.strftime('%B %d, %Y') }}
                </time>
                {% endif %}
            </div>

            {% if entry.content_full %}
            <div class="prose prose-slate dark:prose-invert max-w-none">
                {% for paragraph in entry.content_full.split('\n\n') %}
                {% if paragraph.strip() %}
                <p class="mb-4 text-slate-700 dark:text-slate-300 leading-relaxed">{{ paragraph.strip() }}</p>
                {% endif %}
                {% endfor %}
            </div>
            {% elif entry.content_preview %}
            <div class="prose prose-slate dark:prose-invert max-w-none">
                <p class="text-slate-700 dark:text-slate-300 leading-relaxed">{{ entry.content_preview }}</p>
            </div>
            {% else %}
            <p class="text-slate-500 dark:text-slate-400 italic">{{ t('news.no_content_available') }}</p>
            {% endif %}
        </div>
    </div>

    <!-- Footer -->
    <div class="flex-shrink-0 px-4 py-4 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
        <a
            href="{{ entry.url }}"
            target="_blank"
            rel="noopener noreferrer"
            class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
        >
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            {{ t('news.open_original') }}
        </a>
    </div>
</div>
{% endif %}
```

#### 3. Panel Loading Skeleton
**File**: `ecox-client/templates/partials/_news_detail_panel_skeleton.html` (NEW)
**Changes**: Loading state for panel content

```html
<!-- Panel Loading Skeleton (US-5.16) -->
<div class="h-full flex flex-col animate-pulse">
    <!-- Header skeleton -->
    <div class="flex-shrink-0 px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <div class="h-5 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-2"></div>
        <div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
    </div>
    <!-- Content skeleton -->
    <div class="flex-1 px-4 py-4 space-y-4">
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4"></div>
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full"></div>
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-5/6"></div>
    </div>
</div>
```

#### 4. Client Route - Panel Endpoint
**File**: `ecox-client/src/ecox_client/api/routes/ui.py`
**Changes**: Add route for panel content loading

```python
@router.get("/news/entries/{entry_id}/panel", response_class=HTMLResponse)
async def get_entry_panel(
    request: Request,
    entry_id: int,
    mobile: bool = Query(False),
) -> HTMLResponse:
    """Get entry detail panel content (US-5.15).

    Args:
        entry_id: Entry ID
        mobile: If true, returns mobile-optimized template
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
        logger.error("Platform API error fetching entry for panel", error=str(e))
        entry = None

    template_name = (
        "partials/_news_detail_panel_mobile.html" if mobile
        else "partials/_news_detail_panel.html"
    )

    return templates.TemplateResponse(
        template_name,
        get_template_context(request, entry=entry),
    )
```

### Success Criteria

#### Automated Verification:
- [ ] Type checking passes: `cd ecox-client && uv run pyright src/`
- [ ] Linting passes: `cd ecox-client && uv run pre-commit run --all`

#### Manual Verification:
- [ ] Clicking a card opens the detail panel on the right
- [ ] Panel slides in smoothly from the right
- [ ] Panel displays full entry content
- [ ] "Open original" link opens entry URL in new tab
- [ ] Escape key closes the panel
- [ ] Arrow up/down keys navigate between entries
- [ ] On mobile (<768px), panel covers full screen
- [ ] Mobile panel has back button to close

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 4.

---

## Phase 4: Integration & Cleanup

### Overview
Wire everything together, update the main news route, and remove deprecated code.

### Changes Required

#### 1. Update Main News Route
**File**: `ecox-client/src/ecox_client/api/routes/ui.py`
**Changes**: Change `/news` to serve the new feed instead of tree

```python
@router.get("/news", response_class=HTMLResponse)
async def list_news(request: Request) -> HTMLResponse:
    """Display chronological news feed (US-5.14).

    Replaces the old hierarchical tree view with a flat card feed.
    """
    # Redirect to the new feed endpoint
    return await get_news_feed(request, category_id=None, search=None)
```

#### 2. Remove Old Templates
**Files to delete**:
- `ecox-client/templates/partials/_news_list.html` (old tree view)
- `ecox-client/templates/partials/_news_entry_modal.html` (old modal)
- `ecox-client/templates/partials/_news_section_entries.html` (tree lazy-load)

#### 3. Remove Deprecated Client Routes
**File**: `ecox-client/src/ecox_client/api/routes/ui.py`
**Changes**: Remove or deprecate old routes

```python
# Remove these functions:
# - _fetch_and_transform_news_data() (lines 462-532)
# - list_section_entries() (lines 564-606) - only if not needed for other purposes
# - list_news_with_toast() (lines 688-707)

# Keep get_entry_detail() but update template reference
@router.get("/news/entries/{entry_id}", response_class=HTMLResponse)
async def get_entry_detail(
    request: Request,
    entry_id: int,
) -> HTMLResponse:
    """Get entry detail (legacy endpoint, redirects to panel).

    Kept for backwards compatibility. New code should use /news/entries/{id}/panel.
    """
    return await get_entry_panel(request, entry_id, mobile=False)
```

#### 4. Update Index.html News Container
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Update the news container to work with new feed

Find the news container (around line 654-662) and ensure it points to the new endpoint:

```html
<!-- News Container - loads chronological feed -->
<div id="news-content" hx-get="/api/news/feed" hx-trigger="intersect once" hx-indicator="#global-spinner">
    <!-- Loading skeleton -->
    {% include "partials/_news_feed_skeleton.html" %}
</div>
```

#### 5. Add Translation Keys
**File**: `ecox-client/src/ecox_client/i18n/messages.py` (or equivalent)
**Changes**: Add new translation keys

```python
# Add these keys to the news section
"news.all_categories": "All",
"news.search_placeholder": "Search news...",
"news.loading_more": "Loading more...",
"news.content_preview_only": "Preview only - open original for full content",
```

#### 6. Update BDD Step Definitions
**File**: `ecox-client/tests/step_defs/news_steps.py`
**Changes**: Update step definitions for new UI structure

The step definitions need to be updated to work with the new card-based feed instead of the tree view. Key changes:
- Update selectors to find cards instead of tree nodes
- Update panel interaction steps (slide-in vs modal)
- Add steps for infinite scroll testing

### Success Criteria

#### Automated Verification:
- [ ] All type checking passes: `cd ecox-client && uv run pyright src/`
- [ ] All linting passes: `uv run pre-commit run --all`
- [ ] BDD tests pass: `cd ecox-client && uv run pytest tests/bdd/ -v -m "us_5_14 or us_5_15 or us_5_16"`
- [ ] No import errors in removed code

#### Manual Verification:
- [ ] News tab loads the new feed (not tree)
- [ ] All features work end-to-end:
  - [ ] Feed displays cards chronologically
  - [ ] Category filter chips work
  - [ ] Search bar filters entries
  - [ ] Infinite scroll loads more
  - [ ] Clicking card opens panel
  - [ ] Panel keyboard navigation works
  - [ ] Mobile full-screen panel works
- [ ] No console errors
- [ ] No 404 errors for old endpoints

**Implementation Note**: After completing this phase, run full regression testing before considering the implementation complete.

---

## Testing Strategy

### Unit Tests

**Backend (`ecox-data-platform`):**
- Test `get_feed_entries()` sorting (published_at nulls last)
- Test feed endpoint with various filters
- Test `has_more` calculation

**Client (`ecox-client`):**
- Test `timeago` filter with various dates
- Test feed route returns correct template context

### Integration Tests

**BDD Scenarios to pass:**
- All `@us-5.14` scenarios in `epic05_news_aggregation.feature`
- All `@us-5.15` scenarios
- All `@us-5.16` scenarios

### Manual Testing Steps

1. **Feed Display**
   - Navigate to News tab
   - Verify cards show newest entries first
   - Verify cards show source name and relative time

2. **Filtering**
   - Click a category chip, verify feed filters
   - Click "All" chip, verify filter clears
   - Type in search bar, verify results filter

3. **Infinite Scroll**
   - Scroll to bottom of feed
   - Verify "Loading more..." appears
   - Verify more cards load

4. **Detail Panel**
   - Click a card, verify panel slides in
   - Press Escape, verify panel closes
   - Click card, press Down arrow, verify next entry loads
   - Click "Open original", verify new tab opens

5. **Mobile**
   - Resize to mobile width (<768px)
   - Click card, verify full-screen panel
   - Tap back button, verify returns to feed

## Performance Considerations

- **Batch queries**: Feed endpoint fetches section/source/category info in batch, not per-entry
- **Infinite scroll**: Loads 20 entries at a time, not all at once
- **Panel lazy-loading**: Detail content loaded only when card is clicked
- **Index on published_at**: Consider adding database index on `NewsEntry.published_at` if performance degrades

## Migration Notes

- Old tree view code can be removed immediately (no data migration needed)
- Modal container in `index.html` can be removed if no other features use it
- Session storage for tree state (`newsTreeState`) will be orphaned but harmless

## References

- Original requirements: `docs/requirements/epic05_news_aggregation.md`
- Related ADR: `docs/adrs/news-feed-redesign-adr.md`
- Existing patterns:
  - Infinite scroll: `_news_list.html:195-210`
  - Slide-in animation: `base.html:136-171`
  - Skeleton loading: `index.html:397-403`
