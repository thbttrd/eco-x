---
paths: alembic/**/*.py
---

# Database Migrations (Alembic)

Migrations are at the **root level** (`alembic/` directory).

## Commands

```bash
uv run alembic current              # Check status
uv run alembic upgrade head         # Apply migrations
uv run alembic downgrade -1         # Rollback one
uv run alembic revision --autogenerate -m "description"  # Generate new
```

## Database Setup

```bash
# Wait for postgres
podman exec ecox-postgres pg_isready -U ecox -d ecox_platform

# Run migrations
uv run alembic upgrade head

# Direct access
podman exec ecox-postgres psql -U ecox -d ecox_platform -c "\dt"
```
