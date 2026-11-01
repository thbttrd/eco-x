"""SQLite database manager for the client application.

This module provides async database connectivity for caching
API responses and storing user preferences.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

# Import models to ensure they are registered with SQLModel before create_all
# This is necessary for automatic table creation
import ecox_client.models  # noqa: F401
from ecox_client.config import settings

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Manages SQLite database connections and sessions.

    Features:
    - Async session management
    - Context manager for sessions
    - Health checks
    """

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize the database manager.

        Args:
            database_url: SQLite connection URL. Defaults to settings.
        """
        self.database_url = database_url or settings.database_url

        # Create async engine for SQLite
        # Use StaticPool for SQLite to avoid issues with async
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        logger.info("Database manager initialized", database_url=self.database_url)

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session.

        Yields:
            AsyncSession for database operations
        """
        session = self.async_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_all_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database tables created")

    async def health_check(self) -> dict[str, Any]:
        """Check database connectivity.

        Returns:
            Dictionary with health status
        """
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

    async def close(self) -> None:
        """Close the database connection pool."""
        await self.engine.dispose()
        logger.info("Database connection closed")


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance.

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_db_manager(database_url: str | None = None) -> DatabaseManager:
    """Initialize the global database manager.

    Args:
        database_url: Optional database URL override

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    return _db_manager


async def close_db_manager() -> None:
    """Close the global database manager."""
    global _db_manager
    if _db_manager is not None:
        await _db_manager.close()
        _db_manager = None
