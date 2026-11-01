"""FastAPI dependencies for the platform API.

Provides dependency injection for database sessions and other resources.
"""

from collections.abc import AsyncGenerator

from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.infrastructure.database import get_db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session.

    Yields:
        AsyncSession for database operations
    """
    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        yield session
