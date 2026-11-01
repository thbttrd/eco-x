# ecox-client

Web client for the eco-x economic data platform.

## Overview

The client provides:

- **Web UI**: Interactive interface with htmx, Alpine.js, and Tailwind CSS
- **API Caching**: Local SQLite cache for platform API responses
- **User Preferences**: Local storage for language, theme, favorites
- **Platform Integration**: HTTP client for ecox-data-platform API

## Installation

```bash
cd ecox-client
uv sync
```

## Quick Start

### 1. Ensure Platform is Running

The client requires `ecox-data-platform` to be running at http://localhost:8000

### 2. Start the Client

```bash
uv run uvicorn ecox_client.main:app --host 0.0.0.0 --port 8080 --reload
```

### 3. Access the UI

Open http://localhost:8080 in your browser.

## Features

### Dashboard

- View all data sources and their status
- Browse datasets with search and filtering
- View data values with dimension filtering

### Favorites

- Bookmark frequently accessed datasets
- Quick access from the sidebar

### Settings

- Language selection (EN, FR)
- Theme preferences
- Cache management

## Configuration

Environment variables:

```bash
# Platform API
ECOX_CLIENT_PLATFORM_URL=http://localhost:8000
ECOX_CLIENT_PLATFORM_TIMEOUT=30.0

# Local database (SQLite)
ECOX_CLIENT_DATABASE_URL=sqlite+aiosqlite:///./ecox_client.db

# API
ECOX_CLIENT_API_HOST=0.0.0.0
ECOX_CLIENT_API_PORT=8080

# Cache
ECOX_CLIENT_CACHE_TTL_SECONDS=300
```

## Architecture

```
ecox_client/
├── api/
│   └── routes/            # API route handlers
├── infrastructure/
│   ├── database.py        # SQLite database manager
│   └── platform_client.py # HTTP client for platform
├── models/
│   ├── cache.py           # API cache model
│   └── preferences.py     # User preferences model
├── config.py              # Configuration
└── main.py                # FastAPI application

templates/
├── base.html              # Base layout
├── pages/
│   └── index.html         # Main page
└── partials/              # htmx response fragments
    ├── _sources_grid.html
    ├── _datasets_table.html
    └── _dataset_modal.html
```

## Frontend Stack

- **htmx 2.0**: AJAX without JavaScript
- **Alpine.js 3.x**: Client-side interactivity
- **Tailwind CSS**: Utility-first styling
- **Jinja2**: Server-side templating

### htmx Patterns

```html
<!-- Load content on page load -->
<div hx-get="/api/sources" hx-trigger="load" hx-target="#container"></div>

<!-- Click to load datasets -->
<div hx-get="/api/datasets/eurostat" hx-target="#datasets-container"></div>
```

### Alpine.js Patterns

```html
<!-- Modal with state -->
<div x-data="{ show: false }" @open-modal.window="show = true">
    <div x-show="show" x-transition>Modal content</div>
</div>
```

## Development

### Running Tests

```bash
uv run pytest                    # run all tests
uv run pytest --cov              # with coverage
```

### Code Quality

```bash
uv run ruff format               # format code
uv run ruff check                # lint
uv run mypy src                  # type check
```

## Container Deployment

```bash
# Build image
podman build -t ecox-client -f Containerfile .

# Run container
podman run -d \
  -p 8080:8080 \
  -e ECOX_CLIENT_PLATFORM_URL=http://platform:8000 \
  ecox-client
```
