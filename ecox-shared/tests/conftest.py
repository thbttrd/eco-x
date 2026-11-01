"""Pytest configuration and fixtures for ecox-shared tests."""

import asyncio
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Import models to register them with SQLModel metadata


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_session() -> AsyncSession:
    """Create a test database session with in-memory SQLite."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Yield session for test
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def scenario_context() -> dict:
    """Shared mutable context for BDD scenarios."""
    return {}


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    # ecox-shared/tests/conftest.py -> eco-x/
    return Path(__file__).parent.parent.parent


@pytest.fixture
def alembic_dir(project_root: Path) -> Path:
    """Get the alembic directory path."""
    return project_root / "alembic"
