---
paths: podman-compose.yaml, Dockerfile*, .env, ecox-*/Dockerfile*
---

# Deployment with Podman

## Project Structure (Monorepo)

```
eco-x/
├── ecox-shared/              # Shared models and utilities
├── ecox-data-platform/       # Main platform service (FastAPI)
├── ecox-client/              # Web UI client
├── podman-compose.yaml       # Container orchestration
├── .env                      # Environment variables
└── alembic/                  # Database migrations (root level)
```

## Container Runtime: Podman (NOT Docker)

This project uses **podman** and **podman-compose**, NOT docker.

## Key Commands

```bash
# Start all services
podman-compose up -d

# CRITICAL: After rebuild, use --force-recreate or changes won't take effect!
podman-compose build platform
podman-compose up -d --force-recreate platform

# Rebuild client with version (required for UI header)
ECOX_VERSION=`grep '^version' pyproject.toml | head -1 | cut -d'"' -f2`
ECOX_VERSION=$ECOX_VERSION podman-compose build client
podman-compose up -d --force-recreate client

# View logs
podman-compose logs -f platform

# Stop services
podman-compose down
podman-compose down -v  # Also removes volumes (DELETES DATA)
```

## Services

| Service | Container | Port | Health Check |
|---------|-----------|------|--------------|
| PostgreSQL | ecox-postgres | 5432 | `pg_isready -U ecox -d ecox_platform` |
| Platform | ecox-platform | 8000 | `curl http://localhost:8000/health` |
| Client | ecox-client | 8080 | `curl http://localhost:8080/health` |

## Hot Reload for Frontend Development

For faster frontend iteration without rebuilding containers:

```bash
# Start client with hot reload (templates, static files, locales)
podman-compose -f podman-compose.yaml -f podman-compose.dev.yaml up -d client

# Changes to these files update immediately (just refresh browser):
# - ecox-client/templates/**  (Jinja2 templates)
# - ecox-client/static/**     (JS, CSS)
# - ecox-client/locales/**    (i18n YAML files)

# Python code changes still need a restart:
podman-compose restart client
```

## Environment Variables

**File:** `.env` in project root

```bash
DATABASE_URL=postgresql+asyncpg://ecox:ecox@localhost:5432/ecox_platform
ECOX_FRED_API_KEY=your_fred_api_key
# For containers: ECOX_DATABASE_URL uses postgres:5432 (container hostname)
```
