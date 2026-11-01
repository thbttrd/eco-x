"""Database infrastructure for ecox-agents."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

logger = structlog.get_logger(__name__)

# For local development and container deployment, use a configurable URL
AGENTS_DATABASE_URL = os.environ.get(
    "ECOX_AGENTS_DATABASE_URL",
    "postgresql+asyncpg://ecox:ecox@localhost:5432/ecox_platform",
)


class DatabaseManager:
    """Manages database connections for agents service."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or AGENTS_DATABASE_URL

        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )

        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        session = self.async_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_tables(self) -> None:
        """Create tables for agents service."""
        async with self.engine.begin() as conn:
            # Import models to register them
            from ecox_agents.models import (
                summary,  # noqa: F401  # pyright: ignore[reportUnusedImport]
            )

            await conn.run_sync(SQLModel.metadata.create_all)

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()


# Global instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_db_manager(database_url: str | None = None) -> DatabaseManager:
    """Initialize the global database manager."""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    return _db_manager


async def close_db_manager() -> None:
    """Close the global database manager."""
    global _db_manager
    if _db_manager is not None:
        await _db_manager.close()
        _db_manager = None
