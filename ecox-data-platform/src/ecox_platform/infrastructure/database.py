"""PostgreSQL database manager for the data platform.

This module provides async database connectivity with:
- Connection pooling for efficient resource usage
- Session management with context managers
- Database initialization and health checks
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.config import settings

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database connections and sessions.

    Features:
    - Async connection pooling
    - Context manager for sessions
    - Health checks
    """

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize the database manager.

        Args:
            database_url: PostgreSQL connection URL. Defaults to settings.
        """
        self.database_url = database_url or settings.database_url

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

        # Session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        logger.info("Database manager initialized", database_url=self._mask_url(self.database_url))

    def _mask_url(self, url: str) -> str:
        """Mask password in database URL for logging."""
        if "@" in url and ":" in url:
            # postgresql+asyncpg://user:password@host:port/db
            prefix = url.split("://")[0] + "://"
            rest = url.split("://")[1]
            if "@" in rest:
                user_pass = rest.split("@")[0]
                host_db = rest.split("@")[1]
                if ":" in user_pass:
                    user = user_pass.split(":")[0]
                    return f"{prefix}{user}:***@{host_db}"
        return url

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session.

        Usage:
            async with db_manager.get_session() as session:
                result = await session.exec(query)
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
        """Create all database tables.

        This is mainly for development/testing. In production,
        use Alembic migrations.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database tables created")

    async def drop_all_tables(self) -> None:
        """Drop all database tables.

        WARNING: This will delete all data!
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        logger.warning("Database tables dropped")

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
        logger.info("Database connection pool closed")


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance.

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database manager not initialized
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


# For testing with NullPool (no connection pooling)
class TestDatabaseManager(DatabaseManager):
    """Database manager for testing with NullPool."""

    def __init__(self, database_url: str) -> None:
        """Initialize test database manager without connection pooling."""
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            echo=False,
            poolclass=NullPool,
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
