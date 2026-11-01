---
name: deploy-after-dev
description: Deploy the current branch to local containers with database migrations. Use after completing feature implementation, bug fixes, or when the user mentions deploying, testing locally, or wants to see their changes running. Auto-trigger when development work is complete and user hasn't declined deployment.
allowed-tools: Bash(podman*), Bash(podman-compose*), Bash(uv run alembic*), Bash(curl*), Bash(grep*), Bash(ss*), Bash(pwd), Bash(chmod*), Read, Glob
user-invocable: true
---

# Deploy After Development

Safely deploy the current branch to local Podman containers, handling database migrations and service startup.

## When Claude Should Use This Skill

Automatically use this skill when:
- User says "deploy", "deploy my changes", "run it locally", "start the services"
- User completes a feature and wants to test it
- User asks to "see the changes running" or "test the implementation"
- After completing significant code changes (new feature, bug fix, refactoring)
- User mentions "containers", "podman", or "services"

Do NOT auto-trigger when:
- User explicitly says they don't want to deploy yet
- User is only asking questions or exploring code
- User is in the middle of implementation (not yet complete)

## Project Structure (Monorepo)

```
eco-x/
├── ecox-shared/              # Shared models and utilities
│   └── Containerfile
├── ecox-data-platform/       # Main platform service (FastAPI)
│   └── Containerfile
├── ecox-client/              # Web UI client
│   └── Containerfile
├── podman-compose.yaml       # Container orchestration (NOT docker-compose)
├── .env                      # Environment variables (includes ECOX_SUFFIX for multi-instance)
└── alembic/                  # Database migrations (root level)
```

## Shell Compatibility (IMPORTANT)

Claude Code uses **zsh**, which can fail on complex command substitutions with `$()` syntax.

**Always use backticks** for command substitution in bash commands:
```bash
# GOOD - works in zsh:
ECOX_VERSION=`grep '^version' pyproject.toml | head -1 | cut -d'"' -f2`

# BAD - causes "parse error near ')'" in zsh:
ECOX_VERSION=$(grep '^version' pyproject.toml | head -1 | cut -d'"' -f2)
```

## Container Runtime: Podman (NOT Docker)

This project uses **podman** and **podman-compose**, NOT docker:

```bash
podman ps                      # Check running containers
podman logs ecox-platform      # View platform logs
podman logs ecox-postgres      # View database logs
```

## Multi-Instance Deployment

This project supports parallel development with multiple folder copies. Each instance has:
- **Unique container names** via `ECOX_SUFFIX` (e.g., `-1`, `-2`)
- **Unique ports** to avoid conflicts
- **Dedicated database volumes**

| Instance | ECOX_SUFFIX | PostgreSQL | Platform | Client |
|----------|-------------|------------|----------|--------|
| eco-x    | (empty)     | 5432       | 8000     | 8080   |
| eco-x-1  | -1          | 5433       | 8001     | 8081   |
| eco-x-2  | -2          | 5434       | 8002     | 8082   |

Always detect the current instance from `.env` before operating on containers.

## Deployment Steps

### Step 1: Detect Instance Configuration

First, detect if this is a multi-instance deployment by checking for `ECOX_SUFFIX` in `.env`:

```bash
# Show current working directory (which instance are we in?)
pwd

# Check for instance-specific configuration
grep -E "^ECOX_SUFFIX|^ECOX_.*_PORT" .env 2>/dev/null || echo "Main instance (no suffix)"
```

**Set shell variables for container names:**
```bash
# Read ECOX_SUFFIX from .env (empty string if not set or main instance)
# NOTE: Use backticks instead of $() to avoid zsh parse errors in Claude Code
SUFFIX=`grep '^ECOX_SUFFIX=' .env 2>/dev/null | cut -d= -f2 | tr -d '"'`
echo "Instance suffix: '${SUFFIX:-<main>}'"
```

### Step 2: Start Database with Podman

```bash
# Start postgres with podman-compose
podman-compose up -d postgres

# Wait for database to be ready (container name includes suffix)
for i in {1..30}; do
    podman exec ecox-postgres${SUFFIX} pg_isready -U ecox -d ecox_platform && break
    echo "Waiting for postgres... ($i/30)"
    sleep 1
done
```

### Step 3: Check Database Constraints

The `datavalue` table requires a **UNIQUE CONSTRAINT** for UPSERT operations:

```bash
# Check if constraint exists
podman exec ecox-postgres${SUFFIX} psql -U ecox -d ecox_platform -c "
SELECT conname FROM pg_constraint
WHERE conrelid = 'datavalue'::regclass AND contype = 'u';
"

# Add constraint if missing
podman exec ecox-postgres${SUFFIX} psql -U ecox -d ecox_platform -c "
ALTER TABLE datavalue ADD CONSTRAINT uq_datavalue_dataset_geo_time_indicator
    UNIQUE (dataset_id, geo, time_period, indicator);
"
```

**Common Issue:** If constraint creation fails due to duplicates:
```bash
# Option 1: Truncate (loses data)
podman exec ecox-postgres${SUFFIX} psql -U ecox -d ecox_platform -c "TRUNCATE TABLE datavalue CASCADE;"

# Then add constraint
```

### Step 4: Run Migrations

```bash
# Ensure DATABASE_URL in .env points to correct port
# Check current migration status
uv run alembic current

# Run migrations
uv run alembic upgrade head
```

**If migration fails:**
- Check `podman logs ecox-postgres${SUFFIX}` for database errors
- Rollback with: `uv run alembic downgrade -1`

### Step 5: Build and Start Services

```bash
# Extract version from pyproject.toml for client build
# NOTE: Use backticks and cut to avoid escaping issues in Claude Code
ECOX_VERSION=`grep '^version' pyproject.toml | head -1 | cut -d'"' -f2`
echo "Building with version: $ECOX_VERSION"

# Build containers (platform doesn't need version, client does)
podman-compose build platform
podman-compose build client

# Start services with --force-recreate to ensure new images are used
# IMPORTANT: Without --force-recreate, podman-compose may reuse existing containers
podman-compose up -d --force-recreate platform client
```

**IMPORTANT:** The client container requires `ECOX_VERSION` to display the correct version in the UI header. Always export it before building.

### Step 6: Wait for Health Checks

```bash
# Get the correct ports from .env (or use defaults)
# NOTE: Use backticks instead of $() to avoid zsh parse errors in Claude Code
PLATFORM_PORT=`grep '^ECOX_PLATFORM_PORT=' .env 2>/dev/null | cut -d= -f2`
CLIENT_PORT=`grep '^ECOX_CLIENT_PORT=' .env 2>/dev/null | cut -d= -f2`

for i in {1..30}; do
    curl -s http://localhost:${PLATFORM_PORT:-8000}/health && break
    echo "Waiting for platform... ($i/30)"
    sleep 2
done

for i in {1..30}; do
    curl -s http://localhost:${CLIENT_PORT:-8080}/health && break
    echo "Waiting for client... ($i/30)"
    sleep 2
done
```

### Step 7: Verify Deployment

```bash
# Check container status (shows all ecox containers for this instance)
podman ps --filter "name=ecox.*${SUFFIX}$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test health endpoints
curl -s http://localhost:${PLATFORM_PORT:-8000}/health
curl -s http://localhost:${CLIENT_PORT:-8080}/health

# Test API
curl -s http://localhost:${PLATFORM_PORT:-8000}/api/sources | head -c 500

# Check logs for errors
podman logs ecox-platform${SUFFIX} --tail 50
```

### Step 8: Deployment Report

Generate a summary with instance-specific information:

```
## Deployment Complete

### Instance Information
- **Working Directory:** $(pwd)
- **Instance Suffix:** ${SUFFIX:-<main>}
- **Git Branch:** $(git branch --show-current)

### Services Status
| Service    | Container                    | Port  | Status  | Version |
|------------|------------------------------|-------|---------|---------|
| PostgreSQL | ecox-postgres${SUFFIX}       | ${POSTGRES_PORT:-5432} | Running | -       |
| Platform   | ecox-platform${SUFFIX}       | ${PLATFORM_PORT:-8000} | Running | -       |
| Client     | ecox-client${SUFFIX}         | ${CLIENT_PORT:-8080}   | Running | vX.Y.Z  |

### Verification URLs
- Platform health: http://localhost:${PLATFORM_PORT:-8000}/health
- Client health: http://localhost:${CLIENT_PORT:-8080}/health
- API sources: http://localhost:${PLATFORM_PORT:-8000}/api/sources
- Web UI: http://localhost:${CLIENT_PORT:-8080}/
```

## Quick Reference Commands

```bash
# Start all services
podman-compose up -d

# Start only postgres
podman-compose up -d postgres

# Rebuild and restart platform (--force-recreate ensures new image is used)
podman-compose build platform && podman-compose up -d --force-recreate platform

# Rebuild and restart client WITH VERSION (required for UI header)
# NOTE: Use backticks and cut to avoid escaping issues in Claude Code
ECOX_VERSION=`grep '^version' pyproject.toml | head -1 | cut -d'"' -f2`
podman-compose build client && podman-compose up -d --force-recreate client

# View logs (use container name with suffix)
podman-compose logs -f platform
podman-compose logs -f client

# Stop all services
podman-compose down

# Stop and remove volumes (DELETES DATA)
podman-compose down -v

# Direct database access
podman exec ecox-postgres${SUFFIX} psql -U ecox -d ecox_platform
```

## Troubleshooting

**Containers not using new code after rebuild:**
```bash
# CRITICAL: podman-compose up -d does NOT restart existing containers!
# Always use --force-recreate after rebuilding:
podman-compose build platform
podman-compose up -d --force-recreate platform

# Verify container was recreated (should show recent "Up" time):
podman ps --format "{{.Names}}\t{{.Status}}"
# Good: ecox-platform    Up 5 seconds
# Bad:  ecox-platform    Up 3 hours  <- Old container still running!
```

**Platform won't start:**
```bash
podman logs ecox-platform${SUFFIX}
# Common issues:
# - Database not ready
# - Missing unique constraint on datavalue
# - Missing ECOX_FRED_API_KEY in .env
# - Permission denied on source files (chmod 644 the affected files)
```

**Database connection issues:**
```bash
# From host: use localhost:${POSTGRES_PORT} (check .env for port)
# From container: use postgres:5432 (container hostname, always 5432 internally)
```

**Port conflicts between instances:**
```bash
# Check what's using a port
ss -tlnp | grep :8000

# Verify each instance has unique ports in .env:
# eco-x:   ECOX_PLATFORM_PORT=8000, ECOX_CLIENT_PORT=8080
# eco-x-1: ECOX_PLATFORM_PORT=8001, ECOX_CLIENT_PORT=8081
# eco-x-2: ECOX_PLATFORM_PORT=8002, ECOX_CLIENT_PORT=8082
```

**Constraint errors:**
```bash
# Check for missing constraint
podman exec ecox-postgres${SUFFIX} psql -U ecox -d ecox_platform -c "\d datavalue"
```
