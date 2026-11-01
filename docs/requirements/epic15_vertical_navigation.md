# Epic 15: Vertical Navigation Panel

## Overview

Replace the horizontal tab bar navigation with a fixed left vertical navigation panel (sidebar) to improve scalability, align with modern dashboard patterns, and better utilize screen space.

**Package:** ecox-client
**ADR:** [vertical-navigation-adr.md](../adrs/vertical-navigation-adr.md)

---

## User Stories

### US-15.1: Vertical Navigation Sidebar

**As a** user
**I want to** see a vertical navigation panel on the left side of the screen
**So that** I can easily switch between application sections with better visual hierarchy

**Acceptance Criteria:**

- [ ] Display a fixed vertical sidebar on the left side, below the header
- [ ] Show navigation icons for each section (Sources, Datasets, News)
- [ ] Display section labels next to icons (or on hover in collapsed mode)
- [ ] Highlight the active section with a left border accent (blue-500)
- [ ] Maintain the same icons used in the current horizontal tabs
- [ ] Support dark mode with appropriate color variations

**Technical Notes:**
- Sidebar position: `fixed` or integrated into main layout grid
- Width: ~64px collapsed (icon-only), ~200px expanded
- Active indicator: `border-l-4 border-blue-500`

---

### US-15.2: Sidebar Expand/Collapse

**As a** user
**I want to** expand or collapse the sidebar
**So that** I can maximize content space when needed while still having quick access to navigation

**Acceptance Criteria:**

- [ ] Provide a toggle button to expand/collapse the sidebar
- [ ] Show icons only in collapsed state (64px width)
- [ ] Show icons + labels in expanded state (200px width)
- [ ] Animate the transition smoothly (duration-200)
- [ ] Persist the expanded/collapsed preference in localStorage
- [ ] Show tooltips on icon hover in collapsed mode

**Technical Notes:**
- Alpine.js state: `sidebarExpanded: boolean`
- localStorage key: `ecox_sidebar_expanded`
- Transition: `transition-all duration-200`

---

### US-15.3: Sidebar Hover Expansion

**As a** user
**I want to** see the sidebar expand when I hover over it (in collapsed mode)
**So that** I can quickly see navigation labels without permanently expanding

**Acceptance Criteria:**

- [ ] Expand sidebar width on hover (if currently collapsed)
- [ ] Show section labels when hovering
- [ ] Collapse back to icon-only when mouse leaves
- [ ] Disable hover expansion if user has manually expanded the sidebar
- [ ] Add slight delay before collapsing (200ms) to prevent flickering

**Technical Notes:**
- Use `@mouseenter` and `@mouseleave` with Alpine.js
- Conditional behavior based on `sidebarExpanded` state

---

### US-15.4: Navigation State Persistence

**As a** user
**I want to** return to the same section when I refresh the page
**So that** my navigation context is preserved

**Acceptance Criteria:**

- [ ] Maintain URL sync with `?tab=` query parameter (existing behavior)
- [ ] Restore active section from URL on page load
- [ ] Update URL when navigating between sections
- [ ] Preserve sidebar expanded/collapsed state across sessions

**Technical Notes:**
- Reuse existing `activeTab` and `setTab()` logic from current implementation
- Add localStorage for sidebar state

---

### US-15.5: Mobile Navigation

**As a** mobile user
**I want to** access navigation on smaller screens
**So that** I can use the application on my phone or tablet

**Acceptance Criteria:**

- [ ] Hide vertical sidebar on screens < 768px (md breakpoint)
- [ ] Show a horizontal bottom navigation bar on mobile
- [ ] Display icons with small labels in bottom nav
- [ ] Highlight active section in bottom nav
- [ ] Support touch interactions for navigation

**Technical Notes:**
- Use `hidden md:block` for desktop sidebar
- Use `md:hidden fixed bottom-0` for mobile nav
- Bottom nav height: ~64px

---

### US-15.6: Keyboard Navigation

**As a** keyboard user
**I want to** navigate the sidebar using keyboard controls
**So that** I can use the application without a mouse

**Acceptance Criteria:**

- [ ] Tab key cycles through navigation items
- [ ] Enter or Space activates the focused item
- [ ] Arrow Up/Down navigates between items within the sidebar
- [ ] Visible focus indicator on keyboard navigation
- [ ] Escape key closes any expanded hover state

**Technical Notes:**
- Add `tabindex="0"` to nav items
- Handle `@keydown.enter`, `@keydown.space`, `@keydown.arrow-up`, `@keydown.arrow-down`
- Focus styles: `focus:ring-2 focus:ring-blue-500`

---

### US-15.7: Updated Layout Structure

**As a** developer
**I want to** have a clean layout structure with sidebar + main content
**So that** the codebase is maintainable and consistent

**Acceptance Criteria:**

- [ ] Header spans full width at the top
- [ ] Sidebar is positioned below header, fixed height (viewport - header)
- [ ] Main content area fills remaining space to the right of sidebar
- [ ] Content area scrolls independently of sidebar
- [ ] Remove the old horizontal tab bar markup
- [ ] Update any height calculations that reference the old tab bar height

**Technical Notes:**
- Current news container uses `h-[calc(100vh-11rem)]` which accounts for header + tabs
- New calculation will be `h-[calc(100vh-<header_height>)]`
- Use CSS Grid or Flexbox for the layout: `grid grid-cols-[auto_1fr]`

---

## Test Plan

### Unit Tests Required

**Package: ecox-client**
- [ ] `tests/unit/test_navigation.py`
  - Test: Sidebar renders with all navigation items
  - Test: Active state correctly applied based on URL
  - Test: Sidebar collapse/expand state persists

### Integration Tests

- [ ] Navigation between sections works correctly
- [ ] URL updates when switching sections
- [ ] Mobile bottom nav appears on small screens
- [ ] Keyboard navigation functions properly

### After Implementation
Run `/add-ut US-15.1` to generate the unit tests.

---

## UI Mockup (ASCII)

### Desktop - Expanded Sidebar
```
┌──────────────────────────────────────────────────────────────────────┐
│  EconoScope                                    [🌙] [● Live]         │
├─────────────────┬────────────────────────────────────────────────────┤
│                 │                                                     │
│  ▌ 📊 Sources   │    [Section Content Area]                          │
│                 │                                                     │
│    📦 Datasets  │                                                     │
│                 │                                                     │
│    📰 News      │                                                     │
│                 │                                                     │
│  ─────────────  │                                                     │
│                 │                                                     │
│    🤖 Ask       │    (future)                                        │
│    (planned)    │                                                     │
│                 │                                                     │
└─────────────────┴────────────────────────────────────────────────────┘
```

### Desktop - Collapsed Sidebar
```
┌──────────────────────────────────────────────────────────────────────┐
│  EconoScope                                    [🌙] [● Live]         │
├────────┬─────────────────────────────────────────────────────────────┤
│        │                                                              │
│ ▌ 📊   │    [Section Content Area - More horizontal space]           │
│        │                                                              │
│   📦   │                                                              │
│        │                                                              │
│   📰   │                                                              │
│        │                                                              │
└────────┴─────────────────────────────────────────────────────────────┘
```

### Mobile - Bottom Navigation
```
┌────────────────────────────┐
│  EconoScope      [🌙] [●]  │
├────────────────────────────┤
│                            │
│   [Section Content Area]   │
│                            │
│                            │
│                            │
├────────────────────────────┤
│  📊      📦       📰       │
│ Sources Datasets  News     │
└────────────────────────────┘
```

---

## Dependencies

- **Epic 14 (Agentic Features)**: Will add "Ask" item to navigation
- **Epic 11 (i18n)**: Navigation labels need translations

## Related Files

| File | Purpose |
|------|---------|
| `templates/pages/index.html` | Main layout with tab navigation → sidebar |
| `templates/base.html` | Base layout template |
| `locales/en.yaml` | English translations (nav section) |
| `locales/fr.yaml` | French translations (nav section) |
