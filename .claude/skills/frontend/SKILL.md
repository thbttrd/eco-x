---
name: frontend
description: Frontend development with htmx, Jinja2, Alpine.js, Tailwind. Use when modifying UI, templates, adding components, or working on client-side interactivity.
allowed-tools: Read, Edit, Write, Glob, Grep, Bash(curl*)
---

# Frontend Development Guide

## Stack Overview

The application uses a **hypermedia-driven architecture** (HDA):

- **htmx 2.0** - AJAX without writing JavaScript, server communication
- **Jinja2** - Server-side templating for FastAPI
- **Alpine.js 3.x** - Client-side interactivity (modals, toasts)
- **Tailwind CSS** - Utility-first CSS framework
- **FastAPI** - Python web framework serving HTML fragments

## Architecture

```
Browser ──htmx──> FastAPI ──Jinja2──> HTML Fragments ──htmx──> Browser DOM
   │                                                               │
   └────Alpine.js (local state: modals, toasts, animations)───────┘
```

**Request Flow:**
1. User clicks element with `hx-get="/api/sources"`
2. htmx sends AJAX request with `HX-Request: true` header
3. FastAPI route renders Jinja2 template → HTML fragment
4. htmx swaps fragment into `hx-target="#container"`
5. Alpine.js manages local UI state (modals, toasts)

## Template Structure

```
ecox-client/src/ecox_client/templates/
├── base.html              # Base layout with htmx/Alpine/Tailwind
├── pages/
│   └── index.html         # Main page (extends base)
├── partials/              # htmx response fragments
│   ├── _sources_grid.html
│   ├── _datasets_table.html
│   └── _dataset_modal.html
└── components/            # Reusable includes
    └── _toast.html
```

## htmx Patterns

### Load content on page load
```html
<div hx-get="/api/sources" hx-trigger="load" hx-target="#container"></div>
```

### Click to load datasets
```html
<div hx-get="/api/datasets/eurostat" hx-target="#datasets-container"></div>
```

### Server-Sent Events for real-time updates
```html
<script>
    htmx.createEventSource('/api/events');
</script>
```

## Alpine.js Patterns

### Modal with state
```html
<div x-data="{ show: false }"
     @open-modal.window="show = true"
     @close-modal.window="show = false">
    <div x-show="show" x-transition>Modal content</div>
</div>
```

### Toast notifications
```html
<div x-data="{ toasts: [] }"
     @show-toast.window="toasts.push($event.detail)">
    <template x-for="toast in toasts">
        <div x-text="toast.message"></div>
    </template>
</div>
```

## Jinja2 Templates

```html
{# partials/_sources_grid.html #}
{% for source, count, last_activity in sources %}
<div hx-get="/api/datasets/{{ source }}"
     hx-target="#datasets-container">
    <h3>{{ source.title() }}</h3>
    <span>{{ count }} datasets</span>
</div>
{% endfor %}
```

## FastAPI Routes

```python
from fastapi import Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

@router.get("/sources")
async def list_sources(request: Request, session: AsyncSession):
    sources = await fetch_sources(session)
    return templates.TemplateResponse(
        "partials/_sources_grid.html",
        {"request": request, "sources": sources}
    )
```

## Real-Time Updates (SSE)

Server-Sent Events handled by htmx SSE extension + Alpine.js:

```javascript
// SSE connection (htmx extension)
htmx.createEventSource('/api/events');

// Listen for events
document.body.addEventListener('htmx:sseMessage', function(event) {
    if (event.detail.type === 'dataset-update') {
        const data = JSON.parse(event.detail.data);
        window.dispatchEvent(new CustomEvent('show-toast', {
            detail: { message: `${data.source}/${data.dataset_code}`, type: 'success' }
        }));
    }
});
```

## Self-Hosted Dependencies

htmx and SSE extension are self-hosted (unpkg.com CDN was unreliable):

```
ecox-client/src/ecox_client/static/
├── htmx.min.js (50KB)  # htmx 2.0.4 core library
└── sse.js (10KB)       # htmx SSE extension
```

```html
<!-- Self-hosted for reliability -->
<script src="/static/htmx.min.js"></script>
<script src="/static/sse.js"></script>
```

CDN Status:
- Tailwind CSS - cdn.tailwindcss.com (reliable)
- Alpine.js - unpkg.com (reliable)
- htmx - **self-hosted** (unpkg unreliable)
- htmx SSE ext - **self-hosted** (unpkg unreliable)

## URL State Management

Store UI state in URL query parameters and sync with Alpine.js:

### Read state from URL on init, update URL on state change

```html
<!-- templates/pages/index.html -->
<div x-data="{
    activeTab: new URLSearchParams(window.location.search).get('tab') || 'sources',
    selectedSource: null,
    setTab(tab) {
        this.activeTab = tab;
        this.selectedSource = null;
        const url = new URL(window.location.href);
        url.searchParams.set('tab', tab);
        history.replaceState({}, '', url.toString());
    }
}" x-init="if (activeTab === 'datasets') { htmx.ajax('GET', '/api/datasets/all', {target: '#datasets-container'}) }">

    <button @click="setTab('sources')">Sources</button>
    <button @click="setTab('datasets')">Datasets</button>
</div>
```

### Language switcher preserves query parameters

```html
<div x-data="{
    open: false,
    switchLang(lang) {
        const url = new URL(window.location.href);
        url.searchParams.set('lang', lang);
        window.location.href = url.toString();
    }
}">
    <button @click="switchLang('en')">EN</button>
    <button @click="switchLang('fr')">FR</button>
</div>
```

### Key Principles

1. **Read from URL on page load**: `new URLSearchParams(window.location.search).get('param')`
2. **Update URL on state change**: `history.replaceState()` (no page reload)
3. **Preserve existing params**: Use `URL` API to modify only specific params
4. **Initialize dependent content**: Use `x-init` to load data if starting on non-default tab

### URL Structure

```
http://localhost:8080/?tab=datasets&lang=fr
                       ↑            ↑
                       │            └── Language preference
                       └── Active tab (sources|datasets|news)
```

## Testing Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Static files
curl http://localhost:8080/static/htmx.min.js
curl http://localhost:8080/static/sse.js

# API endpoints (return HTML fragments)
curl http://localhost:8080/api/sources
curl http://localhost:8080/api/datasets/eurostat

# SSE stream
curl -N http://localhost:8080/api/events
```
