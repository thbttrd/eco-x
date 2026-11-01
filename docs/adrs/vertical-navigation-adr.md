# ADR: Vertical Navigation Panel

**Status:** Proposed
**Date:** 2026-01-31
**Author:** User Request

## Context

The ECO-X client application currently uses a horizontal tab bar at the top of the page to navigate between the main sections: Sources, Datasets, and News. As the application grows with planned features (e.g., "Ask" tab for agentic features in Epic 14), the horizontal navigation has limitations:

1. **Limited scalability** - Horizontal tabs become cramped as more sections are added
2. **Wasted horizontal space** - The tab bar spans the full width but only uses a small portion for navigation
3. **Inconsistent with modern dashboard patterns** - Most data/analytics dashboards use vertical sidebars
4. **Mobile responsiveness challenges** - Horizontal tabs need complex responsive handling

## Decision

**Replace the horizontal tab bar with a fixed left vertical navigation panel (sidebar).**

### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Header (App Name, Dark Mode Toggle, Connection Status)      │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                   │
│  Sidebar │           Main Content Area                      │
│  (fixed) │                                                   │
│          │                                                   │
│  [icon]  │   (Tab content rendered here)                    │
│  Sources │                                                   │
│          │                                                   │
│  [icon]  │                                                   │
│  Datasets│                                                   │
│          │                                                   │
│  [icon]  │                                                   │
│  News    │                                                   │
│          │                                                   │
│  ─────── │                                                   │
│  (future │                                                   │
│   items) │                                                   │
│          │                                                   │
└──────────┴──────────────────────────────────────────────────┘
```

### Design Specifications

| Aspect | Specification |
|--------|---------------|
| **Width** | 64px collapsed (icon-only), 200px expanded |
| **Behavior** | Expand on hover or toggle button |
| **Position** | Fixed left, below header |
| **Active indicator** | Left border accent (4px, blue-500) |
| **Icons** | Same icons as current tabs (h-5 w-5) |
| **Labels** | Show on hover/expanded state |
| **Mobile** | Bottom navigation bar or hamburger menu |

### Navigation Items

Current:
1. **Data Sources** - Database icon
2. **Datasets** - Archive/box icon
3. **News** - Newspaper icon

Planned (Epic 14):
4. **Ask** - Chat/sparkle icon (agentic features)

### Active State Styling

```css
/* Active navigation item */
.nav-item-active {
  @apply border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400;
}

/* Inactive navigation item */
.nav-item {
  @apply border-l-4 border-transparent text-slate-500 dark:text-slate-400
         hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-700 dark:hover:text-slate-300;
}
```

### State Management

- Maintain Alpine.js `activeTab` state pattern
- Continue URL sync with `?tab=` parameter
- Add `sidebarExpanded` state for collapse/expand behavior
- Persist sidebar state in `localStorage`

## Consequences

### Positive

1. **Better scalability** - Easy to add more navigation items vertically
2. **More horizontal space** - Main content area gains the space previously used by the tab bar
3. **Modern UX pattern** - Aligns with dashboard/admin panel conventions
4. **Improved mobile experience** - Can collapse to icons or bottom nav
5. **Future-ready** - Accommodates planned "Ask" tab and potential future features

### Negative

1. **Development effort** - Requires template restructuring
2. **Test updates** - BDD feature files referencing tabs need updating
3. **User adjustment** - Existing users familiar with top tabs need to adapt

### Neutral

1. **Same state management** - Alpine.js patterns remain unchanged
2. **Same routing** - URL `?tab=` parameter continues to work

## Alternatives Considered

### 1. Keep Horizontal Tabs, Add Overflow Menu

Add a "More" dropdown when tabs exceed available width.

**Rejected because:** Doesn't solve the fundamental scalability issue and creates inconsistent navigation UX.

### 2. Horizontal Tabs with Icons Only

Reduce tab labels to icons only, with tooltips on hover.

**Rejected because:** Reduces discoverability for new users and doesn't match modern dashboard patterns.

### 3. Full-Width Top Navigation Bar

A horizontal navbar spanning full width with logo, navigation, and utilities.

**Rejected because:** Still has horizontal scalability limits and wastes vertical space.

## Implementation Notes

### Files to Modify

| File | Changes |
|------|---------|
| `templates/pages/index.html` | Replace tab bar with sidebar layout |
| `templates/base.html` | Adjust layout grid for sidebar |
| `locales/en.yaml` | Add sidebar-related translations |
| `locales/fr.yaml` | Add sidebar-related translations |

### CSS/Tailwind Patterns

Use existing codebase patterns:
- `border-l-4` for active indicator (from `_news_list.html`)
- `transition-all duration-200` for smooth expand/collapse
- `w-16` collapsed, `w-48` or `w-52` expanded
- `group` and `group-hover:` for hover effects

### Keyboard Navigation

- `Tab` cycles through navigation items
- `Enter`/`Space` activates selected item
- Arrow keys for item navigation within sidebar
