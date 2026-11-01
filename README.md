# eco-x

**Economic Data Platform - Monorepo**

A distributed economic data platform for fetching, storing, and analyzing data from multiple sources (Eurostat, FRED, NBS China, OECD, ONS) with a REST API and web UI.

## Architecture Overview

```
                    ┌─────────────────────────────────┐
                    │           ecox-client           │
                    │  (Web UI - htmx/Alpine/Jinja)   │
                    │         Port: 8080              │
                    └──────────────┬──────────────────┘
                                   │ HTTP
                    ┌──────────────▼──────────────────┐
                    │       ecox-data-platform        │
                    │  (REST API - FastAPI + Workers) │
                    │         Port: 8000              │
                    └──────────────┬──────────────────┘
                                   │
    ┌──────────────────────────────┼──────────────────────────────┐
    │                              │                               │
┌───▼───┐  ┌───────┐  ┌───────┐  ┌▼────────┐  ┌───────┐  ┌───────┐
│Eurostat│  │ FRED  │  │  NBS  │  │PostgreSQL│  │ OECD │  │  ONS  │
└────────┘  └───────┘  └───────┘  └──────────┘  └───────┘  └───────┘
    │           │           │           │           │           │
    └───────────┴───────────┴───────────┴───────────┴───────────┘
                              Data Sources
```

## Monorepo Structure

```
eco-x/
├── ecox-shared/           # Shared library (models, schemas, HTTP client)
├── ecox-data-platform/    # Data platform (API + scheduler + workers)
├── ecox-client/           # Web client (UI + caching)
├── docs/                  # Documentation
├── config/                # Configuration files
└── podman-compose.yaml    # Container orchestration
```

### Packages

| Package | Description | Port |
|---------|-------------|------|
| [ecox-shared](ecox-shared/README.md) | Shared models, schemas, and HTTP client | - |
| [ecox-data-platform](ecox-data-platform/README.md) | REST API and data fetching workers | 8000 |
| [ecox-client](ecox-client/README.md) | Web UI with htmx and Alpine.js | 8080 |

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [Podman](https://podman.io/) - Container runtime (or Docker)

### Option 1: Run with Containers (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/eco-x.git
cd eco-x

# Start all services
podman-compose up -d

# View logs
podman-compose logs -f

# Stop services
podman-compose down
```

Services will be available at:
- **Client UI**: http://localhost:8080
- **Platform API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Option 2: Run Locally for Development

```bash
# Install dependencies for all packages
cd ecox-shared && uv sync && cd ..
cd ecox-data-platform && uv sync && cd ..
cd ecox-client && uv sync && cd ..

# Start PostgreSQL (required for platform)
podman run -d --name ecox-postgres \
  -e POSTGRES_USER=ecox \
  -e POSTGRES_PASSWORD=ecox \
  -e POSTGRES_DB=ecox_platform \
  -p 5432:5432 postgres:16

# Terminal 1: Start the data platform
cd ecox-data-platform
uv run uvicorn ecox_platform.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start the client
cd ecox-client
uv run uvicorn ecox_client.main:app --host 0.0.0.0 --port 8080 --reload
```

## Data Sources

| Source | Description | Data Types | Rate Limit |
|--------|-------------|------------|------------|
| **Eurostat** | EU Statistical Office | GDP, inflation, employment | 2 req/s |
| **FRED** | Federal Reserve Economic Data | US macroeconomic data | 2 req/s |
| **NBS China** | National Bureau of Statistics | China GDP, CPI, population | 2 req/s |
| **OECD** | OECD Statistics | International comparisons | 1 req/s |
| **ONS** | UK Office for National Statistics | UK economic data | 2 req/s |

### Configuring Data Sources

```yaml
# config/datasets.yaml
eurostat:
  - dataset_code: nama_10_gdp
    enabled: true
    filters:
      geo: [EU27_2020, FR, DE]

fred:
  - dataset_code: GDP
    enabled: true
    # Requires FRED_API_KEY in environment

nbs:
  - dataset_code: A020101  # GDP
    enabled: true
```

## API Endpoints

The platform exposes a RESTful API:

```bash
# Health check
curl http://localhost:8000/health

# List sources
curl http://localhost:8000/api/sources

# List datasets
curl http://localhost:8000/api/datasets

# Get specific dataset
curl http://localhost:8000/api/datasets/eurostat/nama_10_gdp

# Get data values
curl "http://localhost:8000/api/datasets/eurostat/nama_10_gdp/values?geo=FR"

# Fetch logs
curl http://localhost:8000/api/fetch-logs/summary
```

Full API documentation available at http://localhost:8000/docs

## Development

### Running Tests

```bash
# Run tests for all packages
cd ecox-shared && uv run pytest && cd ..
cd ecox-data-platform && uv run pytest && cd ..
cd ecox-client && uv run pytest && cd ..

# Or run with coverage
uv run pytest --cov
```

### Code Quality

Pre-commit hooks are configured for all packages:

```bash
# Install hooks (run once)
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

Checks include:
- Code formatting (ruff)
- Linting (ruff)
- Type checking (mypy)
- Security scanning (bandit)
- Docstring coverage

### Adding a New Data Source

1. Create a new source module in `ecox-data-platform/src/ecox_platform/sources/`
2. Implement `BaseService` from ecox-shared
3. Register the worker in the scheduler
4. Add configuration to `config.py`
5. Add tests

See [docs/adding-sources.md](docs/adding-sources.md) for detailed guide.

## Configuration

Environment variables (can be set in `.env`):

```bash
# Platform
ECOX_DATABASE_URL=postgresql+asyncpg://ecox:ecox@localhost:5432/ecox_platform
ECOX_LOG_LEVEL=INFO

# Data source API keys
FRED_API_KEY=your_fred_api_key

# Client
ECOX_CLIENT_PLATFORM_URL=http://localhost:8000
ECOX_CLIENT_DATABASE_URL=sqlite+aiosqlite:///./ecox_client.db
```

## Project Status

### Implemented
- Eurostat data source with full JSON-stat parsing
- FRED integration with API key support
- NBS China data source
- Continuous fetch scheduler with configurable intervals
- REST API with FastAPI
- Web UI with htmx/Alpine.js/Tailwind
- Container deployment with Podman

### Planned
- OECD and ONS integrations
- Real-time SSE updates in UI
- Data visualization charts
- Export to CSV/Excel
- Email notifications

## Contributing

1. Fork the repository
2. Create a feature branch
3. Install pre-commit hooks: `uv run pre-commit install`
4. Make changes and add tests
5. Submit a pull request

## License

MIT License

## Acknowledgments

- Data provided by [Eurostat](https://ec.europa.eu/eurostat), [FRED](https://fred.stlouisfed.org/), [NBS China](http://www.stats.gov.cn/english/)
- Built with FastAPI, SQLModel, htmx, Alpine.js
