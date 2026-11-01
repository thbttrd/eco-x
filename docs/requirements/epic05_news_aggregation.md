# Epic 5: Economic News Aggregation

## Overview

Provide curated economic news sources organized by category, with automated fetching and parsing of news articles from configured sources.

**Packages:**
- `ecox-data-platform` - News fetching, parsing, and storage
- `ecox-client` - News browsing UI

**Feature Files:**
- `ecox-data-platform/tests/features/epic05_news_aggregation.feature`
- `ecox-client/tests/features/epic05_news_aggregation.feature`

---

## User Stories

### US-5.1: Browse News Sources

**As a** user
**I want to** browse curated economic news sources
**So that** I can quickly access relevant economic information

**Acceptance Criteria:**
- Display news sources organized by category
- Categories include: Central Banks, National Statistics, International Institutions, Economic Indicators, Research & Analysis, Press & Media
- Show source title and direct link
- Click to open source in new tab
- Show last fetched timestamp for each source

---

### US-5.2: Configure News Sources

**As an** administrator
**I want to** manage news sources via configuration
**So that** I can customize the news aggregation

**Acceptance Criteria:**
- YAML configuration for news sources (`config/news.yaml`)
- Support categories and nested sources
- Each source has: title, url, parse_selector (optional), parse_comment (optional)
- Admin endpoint to re-import from config (`POST /api/news/import`)
- Parse selector supports CSS selectors or XPath for article extraction

---

### US-5.3: Configure Fetch Interval

**As an** administrator
**I want to** configure how often news sources are fetched
**So that** I can balance freshness with resource usage

**Acceptance Criteria:**
- Global default fetch interval in `config/news.yaml` (default: 60 minutes)
- Per-category fetch interval override
- Per-source fetch interval override
- Minimum fetch interval: 15 minutes
- Maximum fetch interval: 24 hours
- Environment variable override: `ECOX_NEWS_FETCH_INTERVAL_MINUTES`

---

### US-5.4: Automatic News Fetching

**As a** user
**I want** news sources to be fetched automatically
**So that** I always have up-to-date economic news

**Acceptance Criteria:**
- Background task fetches news at configured interval
- Fetch runs on startup (after delay to allow app initialization)
- Concurrent fetch limit (configurable, default: 3)
- Rate limiting per domain (configurable, default: 2 req/sec)
- Graceful handling of unreachable sources (skip, log, continue)
- SSE notification when new articles are found

---

### US-5.5: News Article Parsing

**As a** system
**I want to** parse articles from news source pages
**So that** users can browse article headlines without visiting each site

**Acceptance Criteria:**
- Extract article headlines and links from source pages
- Support CSS selector-based parsing (`parse_selector` in config)
- Support XPath-based parsing (prefix with `xpath:`)
- Fallback to RSS/Atom feed detection if no selector configured
- Store parsed articles with: title, url, published_date (if available), source_id
- Detect and skip duplicate articles (by URL)
- Store raw HTML for debugging (optional, configurable)

---

### US-5.6: Browse Fetched Articles

**As a** user
**I want to** browse fetched news articles in the UI
**So that** I can see headlines without visiting each source

**Acceptance Criteria:**
- Display articles grouped by category
- Show article title, source name, and time ago
- Click to open original article in new tab
- Filter by category
- Filter by time range (last 24h, last week, all)
- Search articles by title keywords
- Pagination (10 articles per page)

---

### US-5.7: Article Freshness Indicator

**As a** user
**I want to** see how fresh the news articles are
**So that** I know if I'm looking at current information

**Acceptance Criteria:**
- Show "last updated" timestamp per source
- Show "last checked" timestamp per source
- Visual indicator for sources that failed to fetch
- Show number of new articles since last visit

---

### US-5.8: Manual Refresh

**As a** user
**I want to** manually trigger a news refresh
**So that** I can get the latest news on demand

**Acceptance Criteria:**
- Refresh button in the News tab
- Refresh single source by clicking refresh icon next to source
- Show loading indicator during refresh
- Disable refresh button during active fetch
- SSE updates for real-time progress

---

### US-5.9: Define News Sections

**As an** administrator
**I want to** organize news sources into sections with their own index pages
**So that** I can group related content within a single news source

**Acceptance Criteria:**
- Each news source can have multiple sections
- Each section has: title, URL (index page), parse_selector (optional)
- Sections inherit parse_selector from source if not specified
- Sections can be individually enabled/disabled
- YAML config supports nested sections under sources:
  ```yaml
  sources:
    - title: "ECB Monetary Policy"
      sections:
        - title: "Monetary policy decisions"
          url: "https://www.ecb.europa.eu/press/govcdec/mopo/html/index.en.html"
        - title: "Monetary policy statements"
          url: "https://www.ecb.europa.eu/press/press_conference/..."
  ```
- Database schema includes `newssection` table with FK to `newssource`

---

### US-5.10: Fetch Full Entry Content

**As a** user
**I want** news entries to include full text content
**So that** I can read articles without leaving the platform

**Acceptance Criteria:**
- Fetch and store complete text content for each entry (not just 500 chars)
- Store content in TEXT field (unlimited length)
- Generate 500-char preview automatically from full content
- Extract main article content (remove nav, footer, scripts, ads)
- Content extraction uses heuristics: article tag, main tag, content class names
- Handle entries that fail content extraction gracefully (store empty, log error)
- Database column `content_full` added to entry table

---

### US-5.11: Browse Sections in Collapsible Tree *(SUPERSEDED)*

> **Note:** This user story has been superseded by US-5.14 (Chronological News Feed).
> The tree structure is being replaced with a flat chronological feed.
> See ADR: `docs/adrs/news-feed-redesign-adr.md` for rationale.

~~**As a** user~~
~~**I want to** browse news sources with their sections in a collapsible tree~~
~~**So that** I can easily navigate the hierarchical structure~~

---

### US-5.12: View Entry Full Content *(MODIFIED)*

**As a** user
**I want to** view the full content of a news entry
**So that** I can read the complete article text

> **Modified:** Entry details now display in a slide-in right panel instead of a modal.
> See US-5.15 for updated acceptance criteria.

**Acceptance Criteria:** *(Original - being replaced)*
- ~~Click on entry title opens detail view/modal~~
- Display entry title, source, section, published date
- Display full text content with proper formatting
- Show "Open original" link to external URL
- Support keyboard navigation (Escape to close)
- API endpoint: `GET /api/news/entries/{entry_id}`

---

### US-5.13: Section-Level Fetch Status

**As a** user
**I want to** see fetch status per section
**So that** I know which sections are up-to-date

**Acceptance Criteria:**
- Each section has: `last_fetched_at`, `last_fetch_status`, `last_fetch_error`
- ~~Display last fetched time per section in tree view~~ *(tree removed)*
- Show error indicator (red dot) for sections with fetch errors
- Tooltip shows error message on hover
- Allow manual refresh of individual section

---

### US-5.14: Browse Chronological News Feed *(NEW)*

**As a** user
**I want to** browse all news entries in a single chronological feed
**So that** I can see the latest economic news regardless of source

**Acceptance Criteria:**
- Display news entries as a vertical stack of cards (no tree hierarchy)
- Entries sorted by date (newest first), using `published_at` with fallback to `discovered_at`
- All sources are mixed together in a single timeline
- Each card shows: entry title (max 2 lines), source name, relative time (e.g., "2 hours ago")
- Clicking a card selects it and opens the detail panel (see US-5.15)
- Infinite scroll: load 20 entries initially, load more as user scrolls down
- htmx loads additional entries when scroll sentinel is revealed
- Empty state: show "No news yet" message with refresh prompt
- API endpoint: `GET /api/news/entries/feed?limit=20&offset=0`

**Optional Filters:**
- Category filter (chips or dropdown) to narrow by source category
- Search bar to filter entries by title keywords
- Time range filter (last 24h, last week, all)

---

### US-5.15: View Entry in Detail Panel *(NEW)*

**As a** user
**I want to** view entry details in a slide-in panel
**So that** I can read full content while keeping the feed visible

**Acceptance Criteria:**
- Clicking an entry card opens a right-side panel (400-500px width on desktop)
- Panel slides in from the right with smooth animation
- Panel displays:
  - Entry title (full, not truncated)
  - Source name, section name, published date
  - Full article content with proper paragraph formatting
  - "Open original" link to external URL
- Panel closes when:
  - User clicks the close button (X)
  - User presses Escape key
  - User clicks outside the panel (on the feed area)
- Selected entry card is visually highlighted in the feed
- Keyboard navigation: arrow keys to move between entries while panel is open
- Mobile/responsive: Panel becomes full-screen overlay on narrow screens (<768px)
- API endpoint: `GET /api/news/entries/{entry_id}` (existing)

---

### US-5.16: News Feed Loading States *(NEW)*

**As a** user
**I want to** see clear loading indicators in the news feed
**So that** I know when content is being fetched

**Acceptance Criteria:**
- Initial load: Show skeleton cards (3-5 placeholder cards with pulse animation)
- Infinite scroll: Show "Loading more..." indicator at bottom while fetching
- Panel load: Show content skeleton in panel while fetching entry details
- Error state: Show "Failed to load news" with retry button
- Empty state after filter: Show "No entries match your filters" with clear filters option

---

### US-5.17: Independent Scrolling Layout *(NEW - BUG FIX)*

**As a** user browsing the news feed
**I want** the feed and detail panel to scroll independently
**So that** I can browse headlines while reading an article

**Problem Statement:**

The current layout has a UX bug: when scrolling the feed, the detail panel scrolls with the page instead of remaining fixed. This causes the article content to scroll out of view while browsing.

**Acceptance Criteria:**

- News tab uses a viewport-height container (fills available space below header/tabs)
- Left panel (feed cards) scrolls vertically within its container
- Right panel (detail panel) has its own independent vertical scroll
- Scrolling the feed does NOT affect the detail panel position
- Panel header (title, close button) remains fixed at top of panel
- Panel footer (keyboard hints) remains fixed at bottom of panel
- Long article content scrolls within the panel content area
- Panel only closes when: user clicks X, presses Escape, or clicks a different entry
- Clicking outside the panel (on the feed) does NOT close it
- On mobile (<768px), continue using full-screen overlay (unchanged)
- On desktop (>1024px), use side-by-side layout with independent scroll

**Technical Approach (CSS Grid with Viewport Height):**

```css
/* News container fills remaining viewport */
.news-container {
    height: calc(100vh - var(--header-height) - var(--tabs-height));
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    overflow: hidden;
}

/* Each panel scrolls independently */
.feed-panel {
    overflow-y: auto;
}

.detail-panel {
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.detail-panel-content {
    flex: 1;
    overflow-y: auto;
}
```

**Layout Diagram:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Header (sticky, ~64px)                                         │
├─────────────────────────────────────────────────────────────────┤
│  Tab Bar (~56px)  [Sources] [Datasets] [News ✓]                 │
├─────────────────────────────────────────────────────────────────┤
│  News Container (height: calc(100vh - 120px))                   │
│  ┌─────────────────────────┬───────────────────────────────────┐│
│  │ Feed Panel              │ Detail Panel                      ││
│  │ (overflow-y: auto)      │ (overflow-y: auto)                ││
│  │                         │                                   ││
│  │ ┌───────────────────┐  │ ┌─────────────────────────────┐   ││
│  │ │ Entry Card        │  │ │ Header (sticky in panel)    │   ││
│  │ └───────────────────┘  │ │ Title • Source • Close [X]  │   ││
│  │ ┌───────────────────┐  │ ├─────────────────────────────┤   ││
│  │ │ Entry Card (sel.) │◀─┼─│ Scrollable content area     │   ││
│  │ └───────────────────┘  │ │                             │   ││
│  │ ┌───────────────────┐  │ │ Article text scrolls here   │   ││
│  │ │ Entry Card        │  │ │ independently...            │   ││
│  │ └───────────────────┘  │ └─────────────────────────────┘   ││
│  │ [Loading more...]      │ ┌─────────────────────────────┐   ││
│  │                         │ │ Footer: ↑↓ Navigate • Esc  │   ││
│  └─────────────────────────┴───────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
  Feed scrolls here ↕        Panel content scrolls here ↕
  (independent)              (independent)
                             Page does NOT scroll
```

**Files to Modify:**

| File | Changes |
|------|---------|
| `ecox-client/templates/partials/_news_feed.html` | Add viewport-height container, fix overflow classes |
| `ecox-client/templates/partials/_news_detail_panel.html` | Ensure panel has flex layout with scrollable content |
| `ecox-client/templates/pages/index.html` | Add height constraint to `#news-container` wrapper |

---

## Database Schema Updates

### news_section (NEW - US-5.9)

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `source_id` | INTEGER FK | Reference to news_source |
| `title` | TEXT | Section title |
| `url` | TEXT UNIQUE | Section index page URL |
| `parse_selector` | TEXT | CSS selector or XPath (optional, inherits from source) |
| `parse_comment` | TEXT | Parsing notes (optional) |
| `is_active` | BOOLEAN | Enable/disable fetching |
| `fetch_interval_minutes` | INTEGER | Override interval (optional) |
| `last_fetched_at` | DATETIME | Last successful fetch |
| `last_checked_at` | DATETIME | Last fetch attempt |
| `last_fetch_status` | TEXT | success/error |
| `last_fetch_error` | TEXT | Error message if failed |
| `add_date` | DATETIME | When section was added |

### news_entry (RENAMED from news_article - US-5.10)

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `section_id` | INTEGER FK | Reference to news_section (changed from source_id) |
| `title` | TEXT | Entry headline |
| `url` | TEXT UNIQUE | Entry URL (unique constraint) |
| `published_at` | DATETIME | Publication date (if parseable) |
| `discovered_at` | DATETIME | When we first found the entry |
| `content_full` | TEXT | Full text content (NEW) |
| `content_preview` | TEXT | First 500 chars (computed from content_full) |

### news_source (MODIFIED - US-5.9)

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `title` | TEXT | Source title |
| `description` | TEXT | Source description (NEW) |
| `category_id` | INTEGER FK | Reference to news_category |
| `is_active` | BOOLEAN | Enable/disable source |
| `add_date` | DATETIME | When source was added |

> **Note:** `url`, `parse_selector`, `parse_comment`, `last_fetched_at`, `last_checked_at`, `last_fetch_status`, `last_fetch_error` have been moved to `news_section`.

### news_fetch_log (MODIFIED - US-5.13)

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `source_id` | INTEGER FK | Reference to news_source |
| `section_id` | INTEGER FK | Reference to news_section (NEW) |
| `status` | TEXT | success/error |
| `entries_found` | INTEGER | Number of entries parsed (renamed from articles_found) |
| `entries_new` | INTEGER | Number of new entries (renamed from articles_new) |
| `error_message` | TEXT | Error details if failed |
| `started_at` | DATETIME | Fetch start time |
| `completed_at` | DATETIME | Fetch end time |
| `duration_seconds` | FLOAT | Fetch duration |

---

## Configuration Updates

### config/news.yaml (UPDATED - US-5.9)

```yaml
settings:
  # Global defaults
  default_fetch_interval_minutes: 60
  max_concurrent_fetches: 3
  rate_limit_per_domain: 2.0  # requests per second
  fetch_on_startup: true
  startup_delay_seconds: 30
  store_full_content: true  # NEW: Enable full content storage (US-5.10)
  article_retention_months: 12

news:
  - category: "Central Banks"
    fetch_interval_minutes: 30  # Override for category
    sources:
      # NEW: Hierarchical structure with sections (US-5.9)
      - title: "ECB Monetary Policy"
        description: "European Central Bank monetary policy communications"
        enabled: true
        sections:
          - title: "Monetary policy decisions"
            url: "https://www.ecb.europa.eu/press/govcdec/mopo/html/index.en.html"
            enabled: true
            parse_selector: "main .content-box a"
            parse_comment: "Extract decision announcements"

          - title: "Monetary policy statements"
            url: "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/html/index.en.html"
            enabled: true
            parse_selector: ".content-box a[href*='is2']"

      - title: "Federal Reserve"
        description: "US Federal Reserve communications"
        enabled: true
        sections:
          - title: "Beige Book"
            url: "https://www.federalreserve.gov/monetarypolicy/beige-book-default.htm"
            enabled: true
            parse_selector: ".col-xs-12 a[href*='beigebook']"
            fetch_interval_minutes: 120  # Section-level override

  - category: "National Statistics"
    sources:
      - title: "U.S. Bureau of Labor Statistics"
        description: "US labor market statistics and releases"
        enabled: true
        sections:
          - title: "News Releases"
            url: "https://www.bls.gov/bls/newsrels.htm"
            enabled: true
            parse_selector: "table.release-list a"
            parse_comment: "Extract press releases from the releases table"
```

---

## API Endpoints (NEW/UPDATED)

### Existing Endpoints (US-5.1 to US-5.8)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/news/categories` | List news categories with sources |
| GET | `/api/news/articles` | List all articles (paginated, filterable) |
| POST | `/api/news/import` | Re-import sources from config |
| POST | `/api/news/refresh` | Trigger full refresh of all sources |
| GET | `/api/news/status` | Get fetch status (running/idle, progress) |

### New Endpoints (US-5.9 to US-5.16)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/news/sources/{source_id}/sections` | List sections for a source (US-5.9) |
| GET | `/api/news/sections/{section_id}` | Get section details (US-5.9) |
| GET | `/api/news/sections/{section_id}/entries` | List entries in section *(legacy, for tree view)* |
| GET | `/api/news/entries/{entry_id}` | Get full entry with content (US-5.12, US-5.15) |
| POST | `/api/news/sections/{section_id}/refresh` | Refresh single section (US-5.13) |
| GET | `/api/news/entries/feed` | **NEW (US-5.14)**: Get chronological feed of all entries |

### Feed Endpoint Details (US-5.14)

```
GET /api/news/entries/feed
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Number of entries to return (max 100) |
| `offset` | int | 0 | Offset for pagination |
| `category_id` | int | null | Filter by category |
| `search` | string | null | Search entries by title |
| `since` | datetime | null | Only entries after this timestamp |

**Response:**
```json
{
  "entries": [
    {
      "id": 123,
      "title": "ECB raises rates by 25 basis points",
      "url": "https://ecb.europa.eu/...",
      "published_at": "2026-01-11T10:30:00Z",
      "discovered_at": "2026-01-11T10:45:00Z",
      "content_preview": "The European Central Bank announced...",
      "source_title": "ECB Monetary Policy",
      "section_title": "Monetary policy decisions",
      "category_name": "Central Banks"
    }
  ],
  "total": 1523,
  "has_more": true
}

---

## SSE Events (NEW)

| Event | Payload | Description |
|-------|---------|-------------|
| `news-fetch-started` | `{source_id, source_title}` | Source fetch started |
| `news-fetch-completed` | `{source_id, articles_new}` | Source fetch completed |
| `news-fetch-error` | `{source_id, error}` | Source fetch failed |
| `news-refresh-completed` | `{total_sources, total_articles}` | Full refresh done |

---

## Implementation Notes

### Parsing Strategy

1. **CSS Selector** (default): Use BeautifulSoup or lxml with CSS selectors
2. **XPath**: Prefix selector with `xpath:` for XPath parsing
3. **RSS/Atom fallback**: If no selector, look for `<link rel="alternate" type="application/rss+xml">`
4. **Link extraction**: If all else fails, extract all `<a>` tags from main content

### Rate Limiting

- Per-domain rate limiting to avoid overloading sources
- Exponential backoff on repeated failures
- Respect `Retry-After` headers

### Deduplication

- Articles are deduplicated by URL
- Hash URL to handle trailing slashes, query params, etc.
- Store discovered_at to show when we first saw the article

---
