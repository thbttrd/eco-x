# Appendix

## Non-Functional Requirements

### Performance
- Page load under 2 seconds
- API responses under 500ms (cached)
- Support pagination for large datasets
- Non-blocking startup (background refresh)

### Security
- API keys stored in environment variables
- No sensitive data in logs
- Input validation via Pydantic
- Security scanning with bandit

### Quality
- 80% minimum test coverage
- Type hints throughout codebase
- 95% docstring coverage
- Automated pre-commit hooks

### Reliability
- Automatic retry on transient failures
- Graceful degradation on API unavailability
- SSE auto-reconnect on disconnect
- Partial success handling for batch operations
- SQLite WAL mode for concurrent read/write access
- Database busy timeout (30s) for lock contention handling

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main dashboard page |
| GET | `/api/sources` | List data sources with statistics |
| GET | `/api/datasets` | List all datasets with filtering (query params: `search`, `status`, `source`, `page`) |
| GET | `/api/datasets/{source}` | List datasets for source (paginated, query params: `search`, `status`, `page`) |
| GET | `/api/datasets/{source}/{code}` | Dataset detail modal |
| GET | `/api/news/categories` | List news categories with sources |
| GET | `/api/news/articles` | List all entries (paginated, query: `category`, `since`, `search`, `page`) |
| POST | `/api/news/import` | Re-import news sources from config |
| POST | `/api/news/refresh` | Trigger full refresh of all sources |
| GET | `/api/news/status` | Get fetch status (running/idle, progress) |
| GET | `/api/news/sources/{source_id}/sections` | List sections for a source (US-5.9) |
| GET | `/api/news/sections/{section_id}` | Get section details (US-5.9) |
| GET | `/api/news/sections/{section_id}/entries` | List entries in section (US-5.11) |
| GET | `/api/news/entries/{entry_id}` | Get full entry with content (US-5.12) |
| POST | `/api/news/sections/{section_id}/refresh` | Refresh single section (US-5.13) |
| GET | `/api/events` | SSE stream for real-time updates |
| GET | `/health` | Health check endpoint |
| GET | `/static/{file}` | Static asset serving |
| GET | `/api/catalog/sources` | List available data sources in catalog (with activation status) |
| POST | `/api/sources` | Add a data source to the instance |
| POST | `/api/sources/{code}/activate` | Toggle source activation status |
| POST | `/api/datasets/{source}/{code}/download` | Download dataset and enable auto-fetch |
| DELETE | `/api/datasets/{source}/{code}/purge` | Purge dataset data and disable auto-fetch |

---

## Database Schema

### Tables

**dataset**
- `id` (PK)
- `code` (unique, indexed)
- `name`
- `source` (indexed)
- `description`
- `last_fetched`
- `source_last_update` (indexed) - Last update from source TOC
- `content_hash` - SHA256 hash for change detection
- `extra_metadata` (JSON)

**data_value**
- `id` (PK)
- `dataset_id` (FK → dataset)
- `geo` (indexed)
- `time_period` (indexed)
- `indicator` (indexed)
- `value`
- `unit`
- `flags`

**fetch_log**
- `id` (PK)
- `dataset_code` (indexed)
- `source` (indexed)
- `status` (success/error/partial)
- `records_fetched`
- `error_message`
- `filters` (JSON)
- `started_at` (indexed)
- `completed_at`
- `duration_seconds`

**source_metadata**
- `id` (PK)
- `source` (unique, indexed)
- `total_datasets`
- `cached_toc` (JSON)
- `last_updated`

**news_category**
- `id` (PK)
- `name` (indexed)
- `parent_id` (FK, nullable)
- `fetch_interval_minutes` - Override fetch interval for category
- `add_date`

**news_source** (MODIFIED - US-5.9)
- `id` (PK)
- `title`
- `description` - Source description (NEW)
- `category_id` (FK → news_category, indexed)
- `is_active` - Enable/disable source
- `add_date`

> Note: `url`, `parse_selector`, `parse_comment`, `last_fetched_at`, etc. moved to news_section

**news_section** (NEW - US-5.9)
- `id` (PK)
- `source_id` (FK → news_source, indexed)
- `title`
- `url` (unique)
- `parse_selector` - CSS selector or XPath (optional, inherits from source)
- `parse_comment` - Parsing notes (optional)
- `is_active` - Enable/disable fetching
- `fetch_interval_minutes` - Override interval (optional)
- `last_fetched_at` - Last successful fetch
- `last_checked_at` - Last fetch attempt
- `last_fetch_status` - success/error
- `last_fetch_error` - Error message if failed
- `add_date`

**news_entry** (RENAMED from news_article - US-5.10)
- `id` (PK)
- `section_id` (FK → news_section, indexed) - Changed from source_id
- `title`
- `url` (unique)
- `published_at` - Publication date (if parseable)
- `discovered_at` (indexed) - When we first found the entry
- `content_full` (TEXT) - Full text content (NEW)
- `content_preview` - First 500 chars (computed from content_full)

**news_fetch_log** (MODIFIED - US-5.13)
- `id` (PK)
- `source_id` (FK → news_source, indexed)
- `section_id` (FK → news_section, indexed) - NEW
- `status` (success/error)
- `entries_found` - Renamed from articles_found
- `entries_new` - Renamed from articles_new
- `error_message`
- `started_at` (indexed)
- `completed_at`
- `duration_seconds`

**source_activation**
- `id` (PK)
- `source` (unique, indexed) - Source code (e.g., 'eurostat', 'fred', 'ons')
- `activated` - Boolean activation status override from UI
- `updated_at` - Timestamp of last update

---

## Configuration Files

### config/catalog.yaml
```yaml
# Data Source Catalog
# activated: true/false controls default activation state (UI can override)
sources:
  - code: eurostat
    name: Eurostat
    description: EU economic statistics (GDP, inflation, prices)
    dataset_count_estimate: 12000
    auth_required: false
    base_url: https://ec.europa.eu/eurostat
    activated: true

  - code: fred
    name: FRED
    description: US Federal Reserve economic data
    dataset_count_estimate: 500000
    auth_required: true
    base_url: https://fred.stlouisfed.org
    activated: true

  - code: ons
    name: ONS
    description: UK Office for National Statistics - GDP, inflation, employment
    dataset_count_estimate: 500
    auth_required: false
    base_url: https://www.ons.gov.uk
    activated: false  # Disabled by default
```

### config/datasets.yaml
```yaml
settings:
  default_max_age_hours: 24
  max_concurrent_fetches: 3
  fetch_on_startup: true

eurostat:
  - dataset_code: nama_10_gdp
    filters:
      geo: EU27_2020
      unit: CP_MEUR
    max_age_hours: 24
    enabled: true

fred:
  - dataset_code: GDP
    enabled: true
```

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
        description: "US labor market statistics"
        enabled: true
        sections:
          - title: "News Releases"
            url: "https://www.bls.gov/bls/newsrels.htm"
            enabled: true
            parse_selector: "table.release-list a"
```

### locales/en.yaml (Translation Files)
```yaml
# English translations (default)
app:
  name: "EconoScope"
  tagline: "Economic Data Platform"

nav:
  data_sources: "Data Sources"
  datasets: "Datasets"
  news: "Economical News"

status:
  connecting: "Connecting..."
  live: "Live"
  disconnected: "Disconnected"

# Additional sections: sources, datasets, table, modal, catalog, news, error, language
```

---

## Tech Stack

### Backend
- **FastAPI** - Web framework
- **SQLModel** - ORM (SQLAlchemy + Pydantic)
- **Alembic** - Database migrations
- **httpx** - Async HTTP client
- **tenacity** - Retry logic
- **aiolimiter** - Rate limiting
- **structlog** - Structured logging

### Frontend
- **htmx 2.0** - AJAX without JavaScript
- **Alpine.js 3.x** - Lightweight interactivity
- **Tailwind CSS** - Utility CSS
- **Jinja2** - Server-side templates

### Development
- **pytest** - Testing
- **pytest-bdd** - BDD testing
- **factory_boy** - Test data factories
- **ruff** - Linting/formatting
- **mypy** - Type checking
- **pre-commit** - Git hooks

---

## Glossary

| Term | Definition |
|------|------------|
| **Dataset** | A collection of economic data from a specific source |
| **Source** | An economic data provider (Eurostat, FRED, etc.) |
| **TOC** | Table of Contents - list of all available datasets from a source |
| **SSE** | Server-Sent Events - real-time server-to-client communication |
| **HICP** | Harmonised Index of Consumer Prices (EU inflation measure) |
| **JSON-stat** | JSON format for statistical data exchange |
| **htmx** | Library for AJAX requests using HTML attributes |
| **Alembic** | Database migration tool for SQLAlchemy/SQLModel |
| **Migration** | A versioned change to the database schema |
| **Factory** | A test pattern for generating model instances with realistic data |
| **WAL** | Write-Ahead Logging - SQLite mode enabling concurrent reads/writes |
| **Smart Refresh** | Optimization that skips fetching when source data hasn't changed |
