# Epic 13: Database Migration & Test Data Management

## Overview

Provide version-controlled database schema migrations and test data generation.

**Package:** ecox-shared
**Feature File:** `epic13_migrations.feature`

---

## User Stories

### US-13.1: Version-Controlled Schema Migrations

**As a** developer
**I want to** track database schema changes with versioned migrations
**So that** I can safely evolve the database schema and rollback if needed

**Acceptance Criteria:**
- Alembic configured with SQLModel metadata for autogenerate support
- Async engine support for SQLite and PostgreSQL compatibility
- Migration files stored in `alembic/versions/` directory
- Initial migration captures all 9 existing tables (dataset, data_value, etc.)
- Generate new migration with `uv run alembic revision --autogenerate -m "description"`
- Apply migrations with `uv run alembic upgrade head`
- Rollback migrations with `uv run alembic downgrade -1`
- Batch mode enabled for SQLite ALTER TABLE support

---

### US-13.2: Migration Status Awareness

**As a** developer
**I want to** check if database migrations are up-to-date
**So that** I can detect pending migrations before running the application

**Acceptance Criteria:**
- `DatabaseManager.check_migrations()` returns tuple of (is_current, current_rev, head_rev)
- Log warning when migrations are pending with current and head revisions
- Log info when migrations are up-to-date with current revision
- Gracefully handle missing alembic.ini file (skip check)
- `DatabaseManager.run_migrations()` available for programmatic migration execution

---

### US-13.3: Test Data Factories

**As a** developer
**I want to** generate realistic test data using factories
**So that** I can write comprehensive tests without manual data setup

**Acceptance Criteria:**
- factory_boy installed as dev dependency
- Factories available for all 9 database models:
  - DatasetFactory, DataValueFactory, DatasetMetadataFactory, DatasetSelectionFactory
  - FetchLogFactory (with `failed` trait for error scenarios)
  - SourceMetadataFactory, SourceActivationFactory
  - NewsCategoryFactory, NewsSourceFactory
- Factories use Faker for realistic random data (names, URLs, dates)
- Factories use Sequence for auto-incrementing unique values
- Factories support trait patterns for common test scenarios
- All factories importable from `tests.factories`

---

### US-13.4: Hybrid Database Initialization

**As a** developer
**I want to** use different database initialization strategies for different contexts
**So that** tests run fast while production uses proper migrations

**Acceptance Criteria:**
- Tests continue using `create_all()` for fast in-memory database setup
- Production/development uses Alembic migrations for audited schema changes
- `init_db()` method preserved for backward compatibility with tests
- Database is stamped at current migration revision after initial setup
