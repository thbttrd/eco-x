# ADR: News Feed Redesign - From Tree to Chronological Stream

**Date:** 2026-01-11
**Status:** Proposed
**Deciders:** User, Development Team

## Context

The current news section (Epic 5) uses a hierarchical tree structure:
- **Category** (e.g., "Central Banks") → **Source** (e.g., "ECB") → **Section** (e.g., "Monetary Policy Decisions") → **Entry**
- Users must expand multiple levels to reach individual news entries
- Entry details are displayed in a centered modal overlay
- Entries are grouped by source/section, not by recency across all sources

### Problems with Current Approach

1. **Navigation friction**: 3-4 clicks required to reach content
2. **Source-centric view**: Users see news organized by where it came from, not when it happened
3. **Modal disruption**: Modals interrupt reading flow and require explicit dismissal
4. **No unified timeline**: Cannot see "what happened today across all sources" at a glance

## Decision

Redesign the news section to use a **flat chronological feed** with a **slide-in detail panel**:

### New Layout: Master-Detail Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│  News Feed                                                      │
├─────────────────────────────┬───────────────────────────────────┤
│                             │                                   │
│  ┌─────────────────────┐   │   Entry Detail Panel              │
│  │ Entry Card          │   │   ─────────────────────           │
│  │ Source • 2h ago     │   │   Title of Selected Entry         │
│  └─────────────────────┘   │   Source • Section • Date         │
│                             │                                   │
│  ┌─────────────────────┐   │   Full article content...         │
│  │ Entry Card          │◀──│   Multiple paragraphs...          │
│  │ Source • 3h ago     │   │                                   │
│  └─────────────────────┘   │   [Open Original]                 │
│                             │                                   │
│  ┌─────────────────────┐   │                                   │
│  │ Entry Card          │   │                                   │
│  │ Source • 5h ago     │   │                                   │
│  └─────────────────────┘   │                                   │
│                             │                                   │
│  [Loading more...]         │                                   │
│                             │                                   │
└─────────────────────────────┴───────────────────────────────────┘
```

### Key Characteristics

| Aspect | Current (Tree) | New (Stream) |
|--------|----------------|--------------|
| **Layout** | Collapsible tree hierarchy | Flat card stack + detail panel |
| **Ordering** | Grouped by source, then by date | Chronological (newest first) |
| **Sources** | Segregated by category/source | Mixed together in timeline |
| **Detail view** | Modal overlay | Right slide-in panel |
| **Loading** | Lazy-load per section | Infinite scroll |
| **Navigation** | Expand/collapse tree nodes | Scroll + click card |

## Implementation Details

### 1. News Card Component

Each card displays:
- Entry title (truncated to 2 lines)
- Source name + section name (subtle)
- Relative time ("2 hours ago")
- Visual indicator for source category (optional: color dot or icon)

### 2. Infinite Scroll

- Load 20 entries initially
- Load more when user scrolls near bottom
- htmx `hx-trigger="revealed"` on sentinel element
- Sort by `published_at DESC` (fallback to `discovered_at DESC`)

### 3. Detail Panel

- Fixed-position right panel (400-500px width on desktop)
- Slides in when entry is selected
- Shows full content, source info, "Open Original" link
- Closes with: click outside, Escape key, or close button
- Responsive: On mobile, panel becomes full-screen overlay

### 4. Backend Changes

#### New API Endpoint

```
GET /api/news/entries/feed
  ?limit=20
  &offset=0
  &before=<timestamp>  # For cursor pagination
  &category=<id>       # Optional filter
  &search=<query>      # Optional search
```

Returns entries sorted by date with source/section info eagerly loaded.

#### Query Changes in Repository

```python
# Current: grouped by section
query = select(NewsEntry).where(NewsEntry.section_id == section_id)

# New: global chronological feed
query = (
    select(NewsEntry)
    .join(NewsSection)
    .join(NewsSource)
    .order_by(col(NewsEntry.published_at).desc().nulls_last())
    .order_by(col(NewsEntry.discovered_at).desc())
    .limit(limit)
    .offset(offset)
)
```

### 5. UI/UX Considerations

- **Filters available**: Category filter (optional, as chips or dropdown)
- **Search**: Retained as header search bar
- **Time range**: Optional filter for last 24h, last week, all
- **Source identification**: Each card shows source name; color coding optional
- **Empty state**: "No news yet" with refresh prompt

## Alternatives Considered

### 1. Keep Tree, Add Timeline Tab

Add a second "Timeline" view alongside the tree. Rejected because:
- Maintains two UIs to develop and maintain
- Users have to choose between two mental models
- Tree view usage would likely decline anyway

### 2. Horizontal Tabs per Category

Replace tree with horizontal tabs (one per category). Rejected because:
- Still source-centric, not time-centric
- Many categories would create tab overflow
- Doesn't solve the "what happened today" problem

### 3. Modal with Navigation Arrows

Keep modal but add prev/next arrows. Rejected because:
- Modals still feel interruptive
- Arrow navigation feels disconnected from feed context
- Doesn't address the tree hierarchy issue

## Consequences

### Positive

- **Faster access**: Single click from feed to full content
- **Time-centric**: See latest news regardless of source
- **Familiar pattern**: Similar to email (Outlook), news readers (Feedly), social feeds
- **Reduced complexity**: Remove tree state management, session persistence
- **Better scanning**: Users can quickly scroll through headlines

### Negative

- **Loss of hierarchy**: Users can no longer browse "all ECB news" at a glance
- **Source grouping gone**: Some users may prefer seeing all content from one source together
- **Panel takes space**: Detail panel reduces card list width on desktop

### Mitigations

- Add category filter chips to restore "filter by source type" capability
- Add search to find specific sources or topics
- On mobile, use full-screen detail view (no split)

## Related User Stories

- **US-5.11** (superseded): Browse Sections in Collapsible Tree
- **US-5.12** (modified): View Entry Full Content → now in panel, not modal
- **New US-5.14**: Browse Chronological News Feed
- **New US-5.15**: View Entry in Detail Panel

## Migration Strategy

1. Create new templates alongside existing ones
2. Build new API endpoint for feed
3. Implement and test new UI
4. Remove old tree templates and related code
5. Update BDD scenarios

## Addendum: Independent Scrolling Layout (US-5.17)

**Date:** 2026-01-30
**Status:** Proposed

### Problem Discovered

Initial implementation had a critical UX bug: the detail panel scrolled with the page instead of staying fixed. When users scrolled the feed, they lost the article they were reading.

**Root Cause:** The CSS height chain was broken. For `overflow-y: auto` to work, every parent element needs a defined height. The news container used `h-full` but its parents (main content area) had no height constraint.

### Solution: Viewport-Height Container

Replace the flexible-height layout with a fixed viewport-height container:

```css
/* News container fills remaining viewport */
.news-container {
    height: calc(100vh - 120px); /* header + tabs */
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    overflow: hidden;
}

/* Each panel scrolls independently */
.feed-panel { overflow-y: auto; }
.detail-panel {
    display: flex;
    flex-direction: column;
}
.detail-panel-content {
    flex: 1;
    overflow-y: auto;
}
```

### Key Insight

For master-detail layouts with independent scrolling:
1. **Parent must have fixed height** (viewport-based or explicit)
2. **Both panels need `overflow-y: auto`** on their scroll containers
3. **Use `min-height: 0`** on flex children to allow shrinking below content size
4. **Panel header/footer stay fixed** using flex with `flex-shrink: 0`

## References

- Similar patterns: Gmail reading pane, Feedly, Outlook, Slack threads
- htmx infinite scroll: https://htmx.org/examples/infinite-scroll/
- Alpine.js slide-in panel: x-transition with translateX
- CSS independent scroll containers: https://developer.mozilla.org/en-US/docs/Web/CSS/overflow
