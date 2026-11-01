# ecox-data-platform

Data platform service for the eco-x economic data system.

## Overview

The data platform provides:

- **REST API**: FastAPI-based API for accessing economic data
- **Data Sources**: Integrations with Eurostat, FRED, NBS China, OECD, ONS
- **Scheduler**: Continuous fetch workers for automated data updates
- **Storage**: PostgreSQL database for persistent storage

## Installation

```bash
cd ecox-data-platform
uv sync
```

## Quick Start

### 1. Start PostgreSQL

```bash
podman run -d --name ecox-postgres \
  -e POSTGRES_USER=ecox \
  -e POSTGRES_PASSWORD=ecox \
  -e POSTGRES_DB=ecox_platform \
  -p 5432:5432 postgres:16
```

### 2. Run the Platform

```bash
uv run uvicorn ecox_platform.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Access the API

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## API Endpoints

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/live` | Liveness probe |
| GET | `/ready` | Readiness probe |
| GET | `/health` | Full health status |

### Sources

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sources` | List all data sources |
| GET | `/api/sources/{source}` | Get source status |

### Datasets

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/datasets` | List datasets (paginated) |
| GET | `/api/datasets/{source}/{code}` | Get dataset details |
| GET | `/api/datasets/{source}/{code}/values` | Get data values |
| GET | `/api/datasets/{source}/{code}/dimensions/{dim}` | Get dimension values |

### Fetch Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/fetch-logs` | List fetch operations |
| GET | `/api/fetch-logs/summary` | Fetch statistics |

## Configuration

Environment variables:

```bash
# Database
ECOX_DATABASE_URL=postgresql+asyncpg://ecox:ecox@localhost:5432/ecox_platform

# API
ECOX_API_HOST=0.0.0.0
ECOX_API_PORT=8000

# Logging
ECOX_LOG_LEVEL=INFO

# Source-specific
ECOX_EUROSTAT_RATE_LIMIT=2.0
ECOX_FRED_RATE_LIMIT=2.0
ECOX_FRED_API_KEY=your_api_key
```

## Data Sources

### Eurostat

European Union statistics:
- GDP and national accounts
- Prices and inflation (HICP)
- Employment and labor

### FRED

Federal Reserve Economic Data (US):
- GDP, unemployment
- Interest rates
- Money supply

Requires `ECOX_FRED_API_KEY`.

### NBS China

National Bureau of Statistics of China:
- GDP by industry
- CPI and inflation
- Population statistics

## Architecture

```
ecox_platform/
├── api/
│   ├── dependencies.py    # FastAPI dependencies
│   └── routes/            # API route handlers
│       ├── health.py
│       ├── sources.py
│       ├── datasets.py
│       └── fetch_logs.py
├── infrastructure/
│   ├── database.py        # Database manager
│   └── cache.py           # In-memory cache
├── scheduler/
│   ├── continuous_fetcher.py  # Main scheduler
│   └── source_worker.py       # Per-source workers
├── sources/
│   ├── base/              # Base classes
│   ├── eurostat/          # Eurostat integration
│   ├── fred/              # FRED integration
│   └── nbs/               # NBS China integration
├── config.py              # Configuration
└── main.py                # FastAPI application
```

## Development

### Running Tests

```bash
uv run pytest                    # run all tests
uv run pytest --cov              # with coverage
uv run pytest tests/unit/        # unit tests only
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
podman build -t ecox-data-platform -f Containerfile .

# Run container
podman run -d \
  -p 8000:8000 \
  -e ECOX_DATABASE_URL=postgresql+asyncpg://ecox:ecox@host:5432/ecox_platform \
  ecox-data-platform
```
