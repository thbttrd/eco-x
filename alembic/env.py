"""Alembic environment configuration for SQLModel + async migrations.

This module configures Alembic to work with:
- SQLModel metadata (all table definitions)
- Async SQLAlchemy engine (SQLite via aiosqlite)
- Environment-based database URL configuration
"""

import asyncio
from logging.config import fileConfig

from ecox_platform.config import settings

# Import all models to ensure they are registered with SQLModel.metadata
# This is critical for autogenerate to detect all tables
from ecox_shared.models import (  # noqa: F401
    Dataset,
    DatasetMetadata,
    DataValue,
    FetchLog,
    NewsCategory,
    NewsEntry,
    NewsFetchLog,
    NewsSection,
    NewsSource,
    SourceMetadata,
)
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from alembic import context

# Alembic Config object - provides access to .ini file values
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLModel metadata - contains all table definitions
target_metadata = SQLModel.metadata

# Database URL from environment/settings (overrides alembic.ini)
DATABASE_URL = settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This generates SQL scripts without connecting to the database.
    Useful for generating migration scripts to run manually.

    Configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    """
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with an active database connection.

    Args:
        connection: Active SQLAlchemy connection
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode.

    Creates an async engine, connects to the database,
    and runs migrations within that connection.
    """
    # Build configuration for async engine
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't use connection pool for migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an async Engine and associates a connection with the context.
    This is the default mode for running migrations.
    """
    asyncio.run(run_async_migrations())


# Determine which mode to run in
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
