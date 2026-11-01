# ecox-shared

Shared library for the eco-x economic data platform.

## Overview

This package provides common components shared between `ecox-data-platform` and `ecox-client`:

- **Models**: SQLModel database models for datasets, values, fetch logs, and metadata
- **Schemas**: Pydantic schemas for API request/response validation
- **HTTP Client**: Resilient HTTP client with retry logic and rate limiting

## Installation

```bash
# As a dependency in another package
uv add ecox-shared --editable ../ecox-shared

# For development
cd ecox-shared
uv sync
```

## Components

### Models

Database models using SQLModel (SQLAlchemy + Pydantic):

```python
from ecox_shared.models import Dataset, DataValue, FetchLog, SourceMetadata

# Create a dataset
dataset = Dataset(
    code="nama_10_gdp",
    name="GDP and main components",
    source="eurostat",
)

# Add data values
value = DataValue(
    dataset_id=1,
    geo="FR",
    time_period="2023",
    indicator="B1GQ",
    value=2800000.5,
    unit="CP_MEUR",
)
```

### Schemas

API schemas for request/response validation:

```python
from ecox_shared.schemas import (
    DatasetResponse,
    DatasetListResponse,
    SourceResponse,
    FetchLogResponse,
)

# Response models with proper typing
response = DatasetListResponse(
    items=[...],
    total=100,
    page=1,
    page_size=20,
    total_pages=5,
)
```

### Resilient HTTP Client

HTTP client with automatic retries and rate limiting:

```python
from ecox_shared.http import ResilientHttpClient

async with ResilientHttpClient(
    base_url="https://api.example.com",
    rate_limit=2.0,  # requests per second
    timeout=30,      # seconds
) as client:
    response = await client.get("/endpoint")
    data = await client.get_json("/data")
```

Features:
- Automatic retry on network errors, timeouts, and 5xx responses (3 attempts)
- Exponential backoff: 1s → 2s → 4s → 8s (via tenacity)
- Rate limiting (via aiolimiter)
- Configurable timeouts
- Structured logging

Note: Retries are hardcoded to 3 attempts. This cannot be changed as Python decorators are evaluated at class definition time.

## Development

### Running Tests

```bash
uv run pytest
uv run pytest --cov  # with coverage
```

### Code Quality

```bash
uv run ruff format   # format
uv run ruff check    # lint
uv run mypy src      # type check
```

## Dependencies

- `sqlmodel>=0.0.24` - Database models
- `pydantic>=2.0.0` - Schema validation
- `httpx>=0.27.0` - Async HTTP client
- `tenacity>=8.0.0` - Retry logic
- `aiolimiter>=1.1.0` - Rate limiting
- `structlog>=24.0.0` - Structured logging
