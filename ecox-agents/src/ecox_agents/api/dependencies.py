"""FastAPI dependencies for agents service."""

from collections.abc import AsyncGenerator

from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_agents.infrastructure.database import get_db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session."""
    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        yield session
