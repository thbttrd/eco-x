# Eco-X Architecture

This document describes the architecture of the eco-x economic data platform.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                        ecox-client                               │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────┐  ┌───────────────┐  │    │
│  │  │  Jinja2 │  │  htmx   │  │  Alpine.js  │  │   SQLite     │  │    │
│  │  │Templates│  │  AJAX   │  │   State     │  │   Cache      │  │    │
│  │  └─────────┘  └─────────┘  └─────────────┘  └───────────────┘  │    │
│  └──────────────────────────────┬──────────────────────────────────┘    │
│                                 │ HTTP                                   │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼───────────────────────────────────────┐
│                              BACKEND                                     │
│  ┌──────────────────────────────▼──────────────────────────────────┐    │
│  │                     ecox-data-platform                           │    │
│  │                                                                   │    │
│  │  ┌──────────────────────────────────────────────────────────┐   │    │
│  │  │                    FastAPI Application                     │   │    │
│  │  │                                                            │   │    │
│  │  │  /api/sources    /api/datasets    /api/fetch-logs         │   │    │
│  │  │  /health         /live            /ready                   │   │    │
│  │  └─────────────────────────┬──────────────────────────────────┘   │    │
│  │                            │                                       │    │
│  │  ┌─────────────────────────▼──────────────────────────────────┐   │    │
│  │  │                  Continuous Fetcher                         │   │    │
│  │  │                                                             │   │    │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │   │    │
│  │  │  │ Eurostat  │ │   FRED    │ │    NBS    │ │   OECD    │  │   │    │
│  │  │  │  Worker   │ │  Worker   │ │  Worker   │ │  Worker   │  │   │    │
│  │  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  └──────────────────────────────┬──────────────────────────────────┘    │
│                                 │                                        │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │
┌─────────────────────────────────┼────────────────────────────────────────┐
│                            DATABASE                                       │
│  ┌──────────────────────────────▼──────────────────────────────────┐    │
│  │                        PostgreSQL                                 │    │
│  │                                                                   │    │
│  │   datasets   │   data_values   │   fetch_logs   │   metadata    │    │
│  └───────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

## Package Dependencies

```
ecox-shared (library)
    ├── models (Dataset, DataValue, FetchLog, SourceMetadata)
    ├── schemas (API request/response)
    └── http (ResilientHttpClient)
        │
        ├──────────────────┐
        ▼                  ▼
ecox-data-platform      ecox-client
(REST API + workers)    (Web UI)
```

## Data Flow

### 1. Automated Data Fetching

```
1. ContinuousFetcher starts workers for each enabled source
2. SourceWorker checks refresh schedule
3. Worker fetches data from external API (Eurostat, FRED, etc.)
4. Data is parsed and normalized
5. Records are stored in PostgreSQL
6. FetchLog entry is created
```

### 2. User Request Flow

```
1. User opens ecox-client UI
2. Client sends request to platform API
3. Platform queries PostgreSQL
4. Response is returned as JSON
5. htmx updates the DOM
6. Client caches response in SQLite
```

## Database Schema

### datasets

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| code | VARCHAR | Dataset code (e.g., "nama_10_gdp") |
| name | VARCHAR | Human-readable name |
| source | VARCHAR | Data source (eurostat, fred, etc.) |
| description | TEXT | Dataset description |
| last_fetched | TIMESTAMP | Last successful fetch |
| extra_metadata | JSON | Source-specific metadata |

### data_values

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| dataset_id | INT | FK to datasets |
| geo | VARCHAR | Geographic area |
| time_period | VARCHAR | Time period |
| indicator | VARCHAR | Indicator code |
| value | FLOAT | Numeric value |
| unit | VARCHAR | Unit of measure |
| flags | VARCHAR | Quality flags |

### fetch_logs

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Primary key |
| dataset_code | VARCHAR | Dataset code |
| source | VARCHAR | Data source |
| status | VARCHAR | success/error/partial |
| records_fetched | INT | Number of records |
| error_message | TEXT | Error details if failed |
| started_at | TIMESTAMP | Start time |
| completed_at | TIMESTAMP | End time |

## Component Details

### ecox-shared

Shared library used by both platform and client:

- **Models**: SQLModel database models
- **Schemas**: Pydantic schemas for API
- **HTTP Client**: Resilient async HTTP with retries

### ecox-data-platform

Backend service with:

- **FastAPI App**: REST API endpoints
- **Workers**: Per-source fetch workers
- **Scheduler**: Continuous fetcher coordinator
- **Database**: PostgreSQL with SQLModel

### ecox-client

Frontend service with:

- **Templates**: Jinja2 + htmx
- **State**: Alpine.js for UI state
- **Cache**: SQLite for API responses
- **Styles**: Tailwind CSS

## External APIs

### Eurostat

- Base URL: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data`
- Format: JSON-stat 2.0
- Auth: None (public)
- Rate limit: 2 req/s

### FRED

- Base URL: `https://api.stlouisfed.org/fred`
- Format: JSON
- Auth: API key required
- Rate limit: 10 req/s

### NBS China

- Base URL: `https://data.stats.gov.cn/english/easyquery.htm`
- Format: Custom JSON
- Auth: None (public)
- Rate limit: 2 req/s

## Configuration

All services are configured via environment variables:

### Platform

```bash
ECOX_DATABASE_URL=postgresql+asyncpg://...
ECOX_LOG_LEVEL=INFO
ECOX_EUROSTAT_RATE_LIMIT=2.0
ECOX_FRED_API_KEY=...
```

### Client

```bash
ECOX_CLIENT_PLATFORM_URL=http://platform:8000
ECOX_CLIENT_DATABASE_URL=sqlite+aiosqlite:///./cache.db
```

## Scaling Considerations

### Current Design (Single Instance)

- One platform instance
- One client instance
- Single PostgreSQL database

### Future Scaling Options

1. **Horizontal scaling**: Multiple platform instances behind load balancer
2. **Read replicas**: PostgreSQL read replicas for read-heavy workloads
3. **Cache layer**: Redis for API response caching
4. **Queue**: Message queue (RabbitMQ/Redis) for worker coordination
