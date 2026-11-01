# Vertical Navigation Panel Implementation Plan

## Overview

Replace the horizontal tab bar navigation with a fixed left vertical navigation panel (sidebar) to improve scalability, align with modern dashboard patterns, and better utilize screen space. This implements Epic 15 (US-15.1 through US-15.7).

## Current State Analysis

### Existing Implementation

The current horizontal tab bar is in `ecox-client/templates/pages/index.html`:
- **Lines 330-371**: Tab navigation bar with three tabs (Sources, Datasets, News)
- **Alpine.js state**: `activeTab` variable manages current tab
- **URL sync**: `?tab=` query parameter via `setTab()` function (lines 60-66)
- **Height calculation**: News container uses `h-[calc(100vh-11rem)]` (line 655)

### Key Measurements

| Element | Current Height |
|---------|---------------|
| Header (py-4 + content + border) | ~5rem |
| Main content top padding (py-6) | 1.5rem |
| Tab bar (py-4 + content) | ~3rem |
| Tab bar margin (mb-6) | 1.5rem |
| **Total offset** | **11rem** |

After removing tab bar: ~6.5rem (we'll use 7rem for safety)

## Desired End State

After implementation:
- Vertical sidebar on the left side, below the header
- Desktop: Collapsible sidebar (64px collapsed, 200px expanded)
- Mobile (<768px): Bottom navigation bar
- Smooth transitions and hover effects
- Persistent sidebar state in localStorage
- Full keyboard accessibility

### Verification

1. Navigate to the main page - sidebar should be visible on desktop
2. Click each nav item - content should switch correctly
3. Toggle sidebar collapse - should animate smoothly
4. Resize browser to mobile width - bottom nav should appear
5. Refresh page - sidebar state should persist
6. Use keyboard to navigate - Tab/Enter/Arrow keys work

## What We're NOT Doing

- Server-side routing changes (keeping client-side tab switching)
- Adding the "Ask" tab (that's Epic 14)
- Major refactoring of tab content components
- Changes to the header component
- Changes to HTMX loading patterns

## Implementation Approach

We'll restructure `index.html` to use a CSS Grid layout with the sidebar and main content as columns. The sidebar will be a new component with Alpine.js state management for collapse/expand. Mobile will use a separate bottom navigation bar that appears via CSS media queries.

---

## Phase 1: Layout Restructure

### Overview
Replace the current layout with a CSS Grid structure: full-width header, then sidebar + main content side by side.

### Changes Required:

#### 1. Update base.html layout structure
**File**: `ecox-client/templates/base.html`
**Changes**: Modify main content wrapper to support sidebar layout

The base template's `<main>` element needs to be made compatible with the sidebar layout. We'll add a wrapper that can contain both the sidebar and main content.

Replace lines 213-216:
```html
    {# Main content area #}
    <main id="main" class="mx-auto max-w-7xl px-4 py-6">
        {% block content %}{% endblock %}
    </main>
```

With:
```html
    {# Main content area - grid layout for sidebar pages #}
    <div id="app-container" class="flex-1 flex flex-col">
        {% block content %}{% endblock %}
    </div>
```

Also update body tag (line 138) to use flexbox for full-height layout:
```html
<body class="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 text-slate-900 dark:text-slate-100 antialiased">
```

#### 2. Create new index.html layout structure
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Wrap content in grid layout with sidebar

Replace the entire Alpine.js x-data block opening (lines 9-328) with an updated version that includes sidebar state:

```html
{% extends "base.html" %}

{% block title %}{{ t('app.name') }}{% endblock %}

{% block description %}{{ t('app.description') }}{% endblock %}

{% block content %}

<!-- Main Layout with Sidebar (Alpine.js state) -->
<div x-data="{
    activeTab: new URLSearchParams(window.location.search).get('tab') || 'sources',
    selectedSource: null,

    // Sidebar state
    sidebarExpanded: localStorage.getItem('ecox_sidebar_expanded') !== 'false',
    sidebarHovered: false,

    // Computed sidebar width
    get sidebarOpen() {
        return this.sidebarExpanded || this.sidebarHovered;
    },

    // [... keep all existing dataset state: allDatasets through forceRefresh() ...]

    setTab(tab) {
        this.activeTab = tab;
        this.selectedSource = null;
        const url = new URL(window.location.href);
        url.searchParams.set('tab', tab);
        history.replaceState({}, '', url.toString());
    },

    toggleSidebar() {
        this.sidebarExpanded = !this.sidebarExpanded;
        localStorage.setItem('ecox_sidebar_expanded', this.sidebarExpanded);
    }
}" x-init="refreshSources(); if (activeTab === 'datasets') { initDatasets() }"
   @sources-changed.window="refreshSources()"
   class="flex-1 flex">
```

#### 3. Add grid layout for sidebar + content
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Create the two-column layout

After the x-data block opening, add:

```html
    <!-- Sidebar Navigation (Desktop) -->
    <aside
        class="hidden md:flex flex-col bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 transition-all duration-200"
        :class="sidebarOpen ? 'w-52' : 'w-16'"
        @mouseenter="sidebarHovered = true"
        @mouseleave="sidebarHovered = false"
    >
        <!-- Sidebar content will be added in Phase 2 -->
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 overflow-hidden">
        <div class="h-full overflow-y-auto px-4 py-6 md:px-6 lg:px-8">
            <div class="mx-auto max-w-6xl">
                <!-- Tab content sections go here -->
            </div>
        </div>
    </main>
```

### Success Criteria:

#### Automated Verification:
- [x] Application starts without errors: `cd /home/user/eco-x && podman-compose up -d`
- [x] No JavaScript console errors on page load
- [x] Type checking passes: `cd ecox-client && uv run pyright src/` (pre-existing errors only)
- [x] Pre-commit passes: `uv run pre-commit run --all` (pre-existing pyright errors only)

#### Manual Verification:
- [x] Page renders with empty sidebar space on left
- [x] Main content area displays correctly
- [x] Dark mode still works
- [x] Existing tab switching works (via URL parameter)

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the layout structure is correct before proceeding to the next phase.

---

## Phase 2: Sidebar Navigation Component

### Overview
Build the vertical navigation items with icons, labels, and active state indicator.

### Changes Required:

#### 1. Add navigation items to sidebar
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Fill in the sidebar content

Replace the sidebar placeholder with:

```html
    <!-- Sidebar Navigation (Desktop) -->
    <aside
        class="hidden md:flex flex-col bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 transition-all duration-200"
        :class="sidebarOpen ? 'w-52' : 'w-16'"
        @mouseenter="sidebarHovered = true"
        @mouseleave="sidebarHovered = false"
    >
        <!-- Navigation Items -->
        <nav class="flex-1 py-4" role="navigation" aria-label="Main navigation">
            <!-- Data Sources -->
            <button
                @click="setTab('sources')"
                class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors duration-150"
                :class="activeTab === 'sources'
                    ? 'border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 pl-3'
                    : 'border-l-4 border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-slate-100'"
            >
                <svg class="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                </svg>
                <span x-show="sidebarOpen" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100" class="whitespace-nowrap">
                    {{ t('nav.data_sources') }}
                </span>
            </button>

            <!-- Datasets -->
            <button
                @click="setTab('datasets'); initDatasets()"
                class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors duration-150"
                :class="activeTab === 'datasets'
                    ? 'border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 pl-3'
                    : 'border-l-4 border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-slate-100'"
            >
                <svg class="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <span x-show="sidebarOpen" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100" class="whitespace-nowrap">
                    {{ t('nav.datasets') }}
                </span>
            </button>

            <!-- News -->
            <button
                @click="setTab('news')"
                class="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium transition-colors duration-150"
                :class="activeTab === 'news'
                    ? 'border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 pl-3'
                    : 'border-l-4 border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-slate-100'"
            >
                <svg class="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
                <span x-show="sidebarOpen" x-transition:enter="transition ease-out duration-200" x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100" class="whitespace-nowrap">
                    {{ t('nav.news') }}
                </span>
            </button>
        </nav>

        <!-- Sidebar Toggle Button (at bottom) -->
        <div class="border-t border-slate-200 dark:border-slate-700 p-2">
            <button
                @click="toggleSidebar()"
                class="w-full flex items-center justify-center p-2 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                :title="sidebarExpanded ? '{{ t('sidebar.collapse') }}' : '{{ t('sidebar.expand') }}'"
            >
                <svg class="h-5 w-5 transition-transform duration-200" :class="sidebarExpanded ? '' : 'rotate-180'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                </svg>
            </button>
        </div>
    </aside>
```

#### 2. Remove old horizontal tab bar
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Delete lines 330-371 (the horizontal tab navigation)

The old tab bar markup:
```html
    <!-- Tab Navigation -->
    <div class="mb-6 border-b border-slate-200 dark:border-slate-700">
        <nav class="flex space-x-8" aria-label="Tabs">
            <!-- ... tab buttons ... -->
        </nav>
    </div>
```

This entire section should be removed.

#### 3. Update tab content wrappers
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Move tab content inside the new main content area

Ensure the tab content sections are wrapped properly:

```html
    <!-- Main Content Area -->
    <main class="flex-1 overflow-hidden">
        <div class="h-full overflow-y-auto px-4 py-6 md:px-6 lg:px-8">
            <div class="mx-auto max-w-6xl">

                <!-- Tab Content: Data Sources -->
                <div x-show="activeTab === 'sources'" x-transition:enter="transition ease-out duration-200"
                    x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100">
                    <!-- Sources content (existing) -->
                </div>

                <!-- Tab Content: Datasets -->
                <div x-show="activeTab === 'datasets'" x-cloak x-transition:enter="transition ease-out duration-200"
                    x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100">
                    <!-- Datasets content (existing) -->
                </div>

                <!-- Tab Content: News -->
                <div x-show="activeTab === 'news'" x-cloak x-transition:enter="transition ease-out duration-200"
                    x-transition:enter-start="opacity-0" x-transition:enter-end="opacity-100">
                    <!-- News content (existing) -->
                </div>

            </div>
        </div>
    </main>
```

#### 4. Add sidebar translations
**File**: `ecox-client/locales/en.yaml`
**Changes**: Add sidebar-related translations

Add to the `nav:` section:
```yaml
sidebar:
  expand: "Expand sidebar"
  collapse: "Collapse sidebar"
  toggle: "Toggle sidebar"
```

**File**: `ecox-client/locales/fr.yaml`
**Changes**: Add French translations

```yaml
sidebar:
  expand: "Agrandir la barre laterale"
  collapse: "Reduire la barre laterale"
  toggle: "Basculer la barre laterale"
```

### Success Criteria:

#### Automated Verification:
- [x] Application starts without errors
- [x] No JavaScript console errors
- [x] Pre-commit passes: `uv run pre-commit run --all`

#### Manual Verification:
- [x] Sidebar displays with three navigation items (Sources, Datasets, News)
- [x] Clicking nav items switches the active tab content
- [x] Active item shows blue left border and highlighted background
- [x] Sidebar expands on hover when collapsed
- [x] Toggle button at bottom expands/collapses sidebar
- [x] Labels appear/disappear smoothly with transitions
- [x] Dark mode styling is correct
- [x] Sidebar stays fixed while main content scrolls (critical fix: body h-screen overflow-hidden)

**Implementation Note**: After completing this phase, pause for manual verification that navigation works correctly before proceeding.

---

## Phase 3: Update Height Calculations

### Overview
Fix the news container height calculation now that the tab bar is removed.

### Changes Required:

#### 1. Update news container height
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Update the height calculation for the news container

The news container currently uses:
```html
<div id="news-container" class="h-[calc(100vh-11rem)]" ...>
```

With the sidebar layout, the content area is now inside a flexbox container with `overflow-y-auto`. The news container needs to fill the available height.

Change to:
```html
<div id="news-container" class="h-[calc(100vh-8rem)]" ...>
```

Where 8rem accounts for:
- Header: ~5rem
- Main content padding (py-6): 1.5rem
- Buffer: 1.5rem

Alternatively, if using flex layout properly, we can use:
```html
<div id="news-container" class="flex-1 min-h-0" ...>
```

This allows the container to fill remaining space in a flex column.

### Success Criteria:

#### Automated Verification:
- [x] Application starts without errors
- [x] No JavaScript console errors

#### Manual Verification:
- [x] News tab displays with correct height
- [x] News feed cards scroll within the container
- [x] Detail panel appears correctly on the right
- [x] No content is cut off or has extra scroll bars

**Implementation Note**: After completing this phase, verify news tab layout before proceeding.

---

## Phase 4: Mobile Bottom Navigation

### Overview
Add a bottom navigation bar for mobile devices (screens < 768px).

### Changes Required:

#### 1. Add mobile bottom navigation
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Add bottom nav after the main content, before closing the main x-data div

```html
    <!-- Mobile Bottom Navigation -->
    <nav class="md:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 z-40 safe-area-inset-bottom">
        <div class="flex items-stretch h-16">
            <!-- Data Sources -->
            <button
                @click="setTab('sources')"
                class="flex-1 flex flex-col items-center justify-center gap-1 text-xs font-medium transition-colors"
                :class="activeTab === 'sources'
                    ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                    : 'text-slate-600 dark:text-slate-400'"
            >
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
                </svg>
                <span>{{ t('nav.data_sources') }}</span>
            </button>

            <!-- Datasets -->
            <button
                @click="setTab('datasets'); initDatasets()"
                class="flex-1 flex flex-col items-center justify-center gap-1 text-xs font-medium transition-colors"
                :class="activeTab === 'datasets'
                    ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                    : 'text-slate-600 dark:text-slate-400'"
            >
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                <span>{{ t('nav.datasets') }}</span>
            </button>

            <!-- News -->
            <button
                @click="setTab('news')"
                class="flex-1 flex flex-col items-center justify-center gap-1 text-xs font-medium transition-colors"
                :class="activeTab === 'news'
                    ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
                    : 'text-slate-600 dark:text-slate-400'"
            >
                <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
                <span>{{ t('nav.news') }}</span>
            </button>
        </div>
    </nav>
```

#### 2. Add bottom padding for mobile content
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Ensure content doesn't get hidden behind the bottom nav

Add `pb-20 md:pb-0` to the main content wrapper on mobile to add padding at the bottom:

```html
    <!-- Main Content Area -->
    <main class="flex-1 overflow-hidden">
        <div class="h-full overflow-y-auto px-4 py-6 md:px-6 lg:px-8 pb-20 md:pb-6">
```

#### 3. Add safe-area-inset CSS
**File**: `ecox-client/templates/base.html`
**Changes**: Add CSS for iPhone safe area support

In the `<style>` section (after line 136), add:
```css
/* Safe area for iOS devices with notch/home indicator */
.safe-area-inset-bottom {
    padding-bottom: env(safe-area-inset-bottom, 0);
}
```

### Success Criteria:

#### Automated Verification:
- [x] Application starts without errors
- [x] No JavaScript console errors

#### Manual Verification:
- [x] Resize browser to < 768px width
- [x] Top navigation bar appears (changed from bottom per user preference)
- [x] Sidebar is hidden on mobile
- [x] Tapping nav items switches tabs
- [x] Active item is highlighted
- [x] Content scrolls properly with proper top padding
- [x] Footer hidden on mobile to avoid clutter

**Implementation Note**: After completing this phase, test on mobile viewport sizes before proceeding.

---

## Phase 5: Keyboard Navigation & Accessibility

### Overview
Add keyboard navigation support and accessibility improvements.

### Changes Required:

#### 1. Add keyboard navigation to sidebar
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Add keyboard event handlers and ARIA attributes

Update sidebar nav buttons with `tabindex`, `role`, and keyboard handlers:

```html
<nav class="flex-1 py-4" role="navigation" aria-label="{{ t('nav.main_navigation') }}">
    <div role="menubar" aria-orientation="vertical">
        <!-- Data Sources -->
        <button
            role="menuitem"
            tabindex="0"
            @click="setTab('sources')"
            @keydown.enter="setTab('sources')"
            @keydown.space.prevent="setTab('sources')"
            @keydown.arrow-down.prevent="$el.nextElementSibling?.focus()"
            @keydown.arrow-up.prevent="$el.previousElementSibling?.focus()"
            class="..."
            :aria-current="activeTab === 'sources' ? 'page' : undefined"
        >
            <!-- ... -->
        </button>

        <!-- Datasets -->
        <button
            role="menuitem"
            tabindex="0"
            @click="setTab('datasets'); initDatasets()"
            @keydown.enter="setTab('datasets'); initDatasets()"
            @keydown.space.prevent="setTab('datasets'); initDatasets()"
            @keydown.arrow-down.prevent="$el.nextElementSibling?.focus()"
            @keydown.arrow-up.prevent="$el.previousElementSibling?.focus()"
            class="..."
            :aria-current="activeTab === 'datasets' ? 'page' : undefined"
        >
            <!-- ... -->
        </button>

        <!-- News -->
        <button
            role="menuitem"
            tabindex="0"
            @click="setTab('news')"
            @keydown.enter="setTab('news')"
            @keydown.space.prevent="setTab('news')"
            @keydown.arrow-up.prevent="$el.previousElementSibling?.focus()"
            class="..."
            :aria-current="activeTab === 'news' ? 'page' : undefined"
        >
            <!-- ... -->
        </button>
    </div>
</nav>
```

#### 2. Add focus styles
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Add focus ring styles to nav buttons

Add to the button classes:
```
focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-slate-800
```

#### 3. Add translations for accessibility
**File**: `ecox-client/locales/en.yaml`
**Changes**: Add navigation label translation

```yaml
nav:
  main_navigation: "Main navigation"
```

**File**: `ecox-client/locales/fr.yaml`
```yaml
nav:
  main_navigation: "Navigation principale"
```

#### 4. Add tooltips in collapsed state
**File**: `ecox-client/templates/pages/index.html`
**Changes**: Add title attributes for tooltips when sidebar is collapsed

Update each nav button to include:
```html
:title="!sidebarOpen ? '{{ t('nav.data_sources') }}' : ''"
```

### Success Criteria:

#### Automated Verification:
- [x] Application starts without errors
- [x] No JavaScript console errors
- [x] Pre-commit passes

#### Manual Verification:
- [x] Press Tab to focus sidebar items
- [x] Press Enter or Space to activate focused item
- [x] Press Arrow Up/Down to move between items
- [x] Focus ring is visible on keyboard navigation
- [x] Screen reader announces navigation correctly
- [x] Tooltips appear when hovering collapsed sidebar icons

**Implementation Note**: After completing this phase, do final accessibility testing before marking complete.

---

## Testing Strategy

### Unit Tests

No new unit tests required for this frontend-only change.

### Integration Tests

The existing BDD tests in `epic15_vertical_navigation.feature` cover the acceptance criteria.

### Manual Testing Steps

1. **Desktop Navigation**
   - [ ] Open app in desktop browser (> 1024px)
   - [ ] Verify sidebar appears on left
   - [ ] Click each nav item and verify content switches
   - [ ] Click toggle button to collapse/expand sidebar
   - [ ] Hover over collapsed sidebar to see it expand
   - [ ] Refresh page and verify sidebar state persists

2. **Mobile Navigation**
   - [ ] Resize browser to < 768px (or use mobile emulation)
   - [ ] Verify sidebar is hidden
   - [ ] Verify bottom navigation appears
   - [ ] Tap each item and verify content switches
   - [ ] Verify active state highlighting

3. **Keyboard Navigation**
   - [ ] Tab to focus sidebar
   - [ ] Use arrow keys to move between items
   - [ ] Press Enter to activate
   - [ ] Verify focus ring is visible

4. **Dark Mode**
   - [ ] Toggle dark mode
   - [ ] Verify all sidebar elements have correct dark mode styling

5. **Cross-Browser**
   - [ ] Test in Chrome
   - [ ] Test in Firefox
   - [ ] Test in Safari (if available)

## Performance Considerations

- Sidebar uses CSS transitions (not JavaScript animations) for smooth performance
- localStorage access is synchronous but minimal (single boolean)
- No additional API calls required for navigation

## Migration Notes

- No database changes required
- No API changes required
- Existing URL `?tab=` parameters continue to work unchanged
- Users will see the new layout immediately after deployment

## References

- Original requirements: `docs/requirements/epic15_vertical_navigation.md`
- Related ADR: `docs/adrs/vertical-navigation-adr.md`
- Existing responsive patterns: `ecox-client/templates/partials/_news_feed.html:131-166`
- Existing navigation translations: `ecox-client/locales/en.yaml:10-13`
