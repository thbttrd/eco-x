"""Tests for the DatabaseManager."""

from unittest.mock import AsyncMock, patch

import pytest

from ecox_client.infrastructure.database import DatabaseManager


class TestDatabaseManagerInit:
    """Tests for DatabaseManager initialization."""

    def test_init_default_settings(self) -> None:
        """Test database manager uses default settings."""
        with patch("ecox_client.infrastructure.database.settings") as mock_settings:
            mock_settings.database_url = "sqlite+aiosqlite:///./test.db"

            manager = DatabaseManager()

            assert manager.database_url == "sqlite+aiosqlite:///./test.db"

    def test_init_custom_url(self) -> None:
        """Test database manager with custom URL."""
        with patch("ecox_client.infrastructure.database.settings") as mock_settings:
            mock_settings.database_url = "sqlite+aiosqlite:///./default.db"

            manager = DatabaseManager(database_url="sqlite+aiosqlite:///./custom.db")

            assert manager.database_url == "sqlite+aiosqlite:///./custom.db"

    def test_init_in_memory(self) -> None:
        """Test database manager with in-memory database."""
        manager = DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")

        assert manager.database_url == "sqlite+aiosqlite:///:memory:"
        assert manager.engine is not None
        assert manager.async_session is not None


class TestDatabaseManagerSession:
    """Tests for DatabaseManager session management."""

    @pytest.fixture
    def db_manager(self) -> DatabaseManager:
        """Create a test database manager with in-memory SQLite."""
        return DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")

    async def test_get_session(self, db_manager: DatabaseManager) -> None:
        """Test getting a database session."""
        async with db_manager.get_session() as session:
            assert session is not None

    async def test_session_commit_on_success(self, db_manager: DatabaseManager) -> None:
        """Test session commits on successful context exit."""
        await db_manager.create_all_tables()

        from ecox_client.models.preferences import UserPreference

        async with db_manager.get_session() as session:
            pref = UserPreference(key="test", value="value")
            session.add(pref)

        # Verify the data was committed
        async with db_manager.get_session() as session:
            from sqlmodel import select

            result = await session.execute(
                select(UserPreference).where(UserPreference.key == "test")
            )
            saved = result.scalar_one()
            assert saved.value == "value"

    async def test_session_rollback_on_error(self, db_manager: DatabaseManager) -> None:
        """Test session rolls back on error."""
        await db_manager.create_all_tables()

        from ecox_client.models.preferences import UserPreference

        try:
            async with db_manager.get_session() as session:
                pref = UserPreference(key="rollback_test", value="value")
                session.add(pref)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify the data was not committed
        async with db_manager.get_session() as session:
            from sqlmodel import select

            result = await session.execute(
                select(UserPreference).where(UserPreference.key == "rollback_test")
            )
            assert result.scalar_one_or_none() is None


class TestDatabaseManagerTables:
    """Tests for DatabaseManager table operations."""

    @pytest.fixture
    def db_manager(self) -> DatabaseManager:
        """Create a test database manager with in-memory SQLite."""
        return DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")

    async def test_create_all_tables(self, db_manager: DatabaseManager) -> None:
        """Test creating all tables."""
        await db_manager.create_all_tables()

        # Verify tables exist by inserting data
        from datetime import datetime, timedelta

        from ecox_client.models.cache import ApiCacheEntry
        from ecox_client.models.preferences import FavoriteDataset, UserPreference

        async with db_manager.get_session() as session:
            # Insert into all tables
            session.add(UserPreference(key="test", value="val"))
            session.add(FavoriteDataset(source="eurostat", dataset_code="test"))
            session.add(
                ApiCacheEntry(
                    cache_key="test",
                    endpoint="/test",
                    response_data="{}",
                    expires_at=datetime.now() + timedelta(hours=1),
                )
            )


class TestDatabaseManagerHealthCheck:
    """Tests for DatabaseManager health check."""

    @pytest.fixture
    def db_manager(self) -> DatabaseManager:
        """Create a test database manager with in-memory SQLite."""
        return DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")

    async def test_health_check_healthy(self, db_manager: DatabaseManager) -> None:
        """Test health check returns healthy status."""
        result = await db_manager.health_check()

        assert result["status"] == "healthy"
        assert result["database"] == "connected"

    async def test_health_check_unhealthy(self) -> None:
        """Test health check returns unhealthy on error."""
        with patch("ecox_client.infrastructure.database.settings") as mock_settings:
            mock_settings.database_url = "sqlite+aiosqlite:///:memory:"

            manager = DatabaseManager()
            # Force an error by disposing engine and trying health check
            await manager.engine.dispose()

            # Mock get_session to raise
            async def failing_session():
                raise Exception("Connection failed")
                yield  # type: ignore[misc]

            manager.get_session = failing_session  # type: ignore[method-assign]

            result = await manager.health_check()

            assert result["status"] == "unhealthy"
            assert result["database"] == "disconnected"
            assert "error" in result


class TestDatabaseManagerClose:
    """Tests for DatabaseManager close."""

    async def test_close(self) -> None:
        """Test closing the database manager."""
        manager = DatabaseManager(database_url="sqlite+aiosqlite:///:memory:")

        await manager.close()

        # Engine should be disposed


class TestGlobalDatabaseFunctions:
    """Tests for global database functions."""

    def test_get_db_manager_creates_singleton(self) -> None:
        """Test get_db_manager creates a singleton."""
        from ecox_client.infrastructure import database

        # Reset global
        database._db_manager = None

        with patch.object(database, "DatabaseManager") as mock_cls:
            manager1 = database.get_db_manager()
            manager2 = database.get_db_manager()

            assert manager1 is manager2
            mock_cls.assert_called_once()

        # Cleanup
        database._db_manager = None

    def test_init_db_manager(self) -> None:
        """Test init_db_manager creates new instance."""
        from ecox_client.infrastructure import database

        # Reset global
        database._db_manager = None

        manager = database.init_db_manager(database_url="sqlite+aiosqlite:///:memory:")

        assert manager is not None
        assert database._db_manager is manager

        # Cleanup
        database._db_manager = None

    async def test_close_db_manager(self) -> None:
        """Test close_db_manager closes and clears singleton."""
        from ecox_client.infrastructure import database

        mock_manager = AsyncMock()
        database._db_manager = mock_manager

        await database.close_db_manager()

        mock_manager.close.assert_called_once()
        assert database._db_manager is None
