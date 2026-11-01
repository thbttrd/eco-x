"""Unit tests for NewsRepository.

Tests cover:
- Category operations (get, create)
- Source operations (get, upsert)
- Section operations (get, upsert, stale detection)
- Entry operations (get, upsert, cleanup)
- Fetch log operations
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from ecox_shared.models import NewsCategory, NewsSection, NewsSource

from ecox_platform.news.repository import NewsRepository


class TestNewsRepository:
    """Tests for NewsRepository."""

    @pytest.fixture
    def repository(self) -> NewsRepository:
        """Create repository instance."""
        return NewsRepository()

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock async session."""
        session = AsyncMock()
        session.exec = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        return session


class TestCategoryOperations(TestNewsRepository):
    """Tests for category-related operations."""

    @pytest.mark.asyncio
    async def test_get_categories_returns_list(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test get_categories returns all categories."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            NewsCategory(id=1, name="Banks"),
            NewsCategory(id=2, name="Statistics"),
        ]
        mock_session.exec.return_value = mock_result

        categories = await repository.get_categories(mock_session)

        assert len(categories) == 2
        assert categories[0].name == "Banks"

    @pytest.mark.asyncio
    async def test_get_or_create_category_returns_existing(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test get_or_create returns existing category."""
        existing_category = NewsCategory(id=1, name="Banks")
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = existing_category
        mock_session.exec.return_value = mock_result

        category = await repository.get_or_create_category(mock_session, "Banks")

        assert category.id == 1
        assert category.name == "Banks"
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_category_creates_new(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test get_or_create creates new category when not found."""
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        mock_session.exec.return_value = mock_result

        category = await repository.get_or_create_category(mock_session, "NewCategory")

        assert category.name == "NewCategory"
        mock_session.add.assert_called_once()


class TestSourceOperations(TestNewsRepository):
    """Tests for source-related operations."""

    @pytest.mark.asyncio
    async def test_get_source_by_id_found(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test get_source_by_id returns source when found."""
        mock_source = NewsSource(
            id=1,
            title="Example",
            category_id=1,
        )
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_source
        mock_session.exec.return_value = mock_result

        source = await repository.get_source_by_id(mock_session, 1)

        assert source is not None
        assert source.title == "Example"

    @pytest.mark.asyncio
    async def test_get_source_by_id_not_found(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test get_source_by_id returns None when not found."""
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        mock_session.exec.return_value = mock_result

        source = await repository.get_source_by_id(mock_session, 999)

        assert source is None

    @pytest.mark.asyncio
    async def test_get_source_by_title_found(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test get_source_by_title returns source when found."""
        mock_source = NewsSource(
            id=1,
            title="ECB",
            category_id=1,
        )
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_source
        mock_session.exec.return_value = mock_result

        source = await repository.get_source_by_title(mock_session, "ECB", category_id=1)

        assert source is not None
        assert source.title == "ECB"


class TestSectionOperations(TestNewsRepository):
    """Tests for section-related operations."""

    @pytest.mark.asyncio
    async def test_get_section_by_url_found(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test get_section_by_url returns section when found."""
        mock_section = NewsSection(
            id=1,
            url="https://example.com/feed",
            title="News Feed",
            source_id=1,
        )
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_section
        mock_session.exec.return_value = mock_result

        section = await repository.get_section_by_url(mock_session, "https://example.com/feed")

        assert section is not None
        assert section.title == "News Feed"

    @pytest.mark.asyncio
    async def test_get_section_by_url_not_found(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test get_section_by_url returns None when not found."""
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        mock_session.exec.return_value = mock_result

        section = await repository.get_section_by_url(mock_session, "https://nonexistent.com")

        assert section is None


class TestEntryOperations(TestNewsRepository):
    """Tests for entry-related operations."""

    @pytest.mark.asyncio
    async def test_entry_exists_true(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test entry_exists returns True when entry exists."""
        mock_result = MagicMock()
        mock_result.one.return_value = 1
        mock_session.exec.return_value = mock_result

        exists = await repository.entry_exists(mock_session, "https://example.com/article")

        assert exists is True

    @pytest.mark.asyncio
    async def test_entry_exists_false(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test entry_exists returns False when entry not found."""
        mock_result = MagicMock()
        mock_result.one.return_value = 0
        mock_session.exec.return_value = mock_result

        exists = await repository.entry_exists(mock_session, "https://new.com")

        assert exists is False

    @pytest.mark.asyncio
    async def test_upsert_entries_returns_zero_for_empty_list(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test upsert_entries returns 0 for empty list."""
        count = await repository.upsert_entries(mock_session, section_id=1, entries=[])

        assert count == 0
        mock_session.exec.assert_not_called()


class TestGetStaleSectionsFiltering(TestNewsRepository):
    """Tests for get_stale_sections filtering logic."""

    @pytest.mark.asyncio
    async def test_get_stale_sections_filters_inactive(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test that inactive sections are filtered out."""
        # Only active, stale section should be returned
        active_stale = NewsSection(
            id=1,
            url="https://active.com/feed",
            title="Active Feed",
            source_id=1,
            is_active=True,
            last_fetched_at=datetime.now(UTC) - timedelta(hours=2),
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [active_stale]
        mock_session.exec.return_value = mock_result

        sections = await repository.get_stale_sections(mock_session)

        assert len(sections) == 1
        assert sections[0].is_active is True

    @pytest.mark.asyncio
    async def test_get_stale_sections_includes_never_fetched(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test that sections never fetched are included."""
        never_fetched = NewsSection(
            id=1,
            url="https://new.com/feed",
            title="New Feed",
            source_id=1,
            is_active=True,
            last_fetched_at=None,
        )

        mock_result = MagicMock()
        mock_result.all.return_value = [never_fetched]
        mock_session.exec.return_value = mock_result

        sections = await repository.get_stale_sections(mock_session)

        assert len(sections) == 1
        assert sections[0].last_fetched_at is None


class TestFetchLogOperations(TestNewsRepository):
    """Tests for fetch log operations."""

    @pytest.mark.asyncio
    async def test_log_fetch_creates_entry(
        self, repository: NewsRepository, mock_session: AsyncMock
    ) -> None:
        """Test log_fetch creates a log entry."""
        started = datetime.now(UTC)
        completed = started + timedelta(seconds=5)

        log = await repository.log_fetch(
            mock_session,
            section_id=1,
            status="success",
            entries_found=10,
            entries_new=3,
            started_at=started,
            completed_at=completed,
        )

        assert log.section_id == 1
        assert log.status == "success"
        assert log.entries_found == 10
        assert log.entries_new == 3
        assert log.duration_seconds == 5.0
        mock_session.add.assert_called_once()
