"""Tests for cache models."""

from datetime import datetime, timedelta

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_client.models.cache import ApiCacheEntry


class TestApiCacheEntry:
    """Tests for ApiCacheEntry model."""

    def test_cache_entry_creation(self) -> None:
        """Test creating a cache entry."""
        entry = ApiCacheEntry(
            cache_key="sources:list",
            endpoint="/api/sources",
            response_data='{"items": []}',
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert entry.cache_key == "sources:list"
        assert entry.endpoint == "/api/sources"
        assert entry.response_data == '{"items": []}'

    def test_cache_entry_not_expired(self) -> None:
        """Test cache entry is not expired when future expiry."""
        entry = ApiCacheEntry(
            cache_key="test",
            endpoint="/test",
            response_data="{}",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        assert entry.is_expired is False

    def test_cache_entry_expired(self) -> None:
        """Test cache entry is expired when past expiry."""
        entry = ApiCacheEntry(
            cache_key="test",
            endpoint="/test",
            response_data="{}",
            expires_at=datetime.now() - timedelta(hours=1),
        )
        assert entry.is_expired is True

    def test_cache_entry_defaults(self) -> None:
        """Test cache entry has default created_at."""
        before = datetime.now()
        entry = ApiCacheEntry(
            cache_key="test",
            endpoint="/test",
            response_data="{}",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        after = datetime.now()
        assert before <= entry.created_at <= after


class TestApiCacheEntryDatabase:
    """Tests for ApiCacheEntry with database."""

    async def test_save_cache_entry(self, test_db_session: AsyncSession) -> None:
        """Test saving a cache entry to database."""
        entry = ApiCacheEntry(
            cache_key="sources:list",
            endpoint="/api/sources",
            response_data='{"items": [{"code": "eurostat"}]}',
            expires_at=datetime.now() + timedelta(hours=1),
        )
        test_db_session.add(entry)
        await test_db_session.commit()

        assert entry.id is not None

    async def test_retrieve_cache_entry(self, test_db_session: AsyncSession) -> None:
        """Test retrieving a cache entry by key."""
        from sqlmodel import select

        entry = ApiCacheEntry(
            cache_key="datasets:eurostat",
            endpoint="/api/datasets",
            response_data='{"total": 10}',
            expires_at=datetime.now() + timedelta(hours=1),
        )
        test_db_session.add(entry)
        await test_db_session.commit()

        result = await test_db_session.execute(
            select(ApiCacheEntry).where(ApiCacheEntry.cache_key == "datasets:eurostat")
        )
        retrieved = result.scalar_one()

        assert retrieved.cache_key == "datasets:eurostat"
        assert retrieved.response_data == '{"total": 10}'

    async def test_unique_cache_key(self, test_db_session: AsyncSession) -> None:
        """Test cache_key is unique."""
        from sqlalchemy.exc import IntegrityError

        entry1 = ApiCacheEntry(
            cache_key="duplicate",
            endpoint="/test",
            response_data="{}",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        test_db_session.add(entry1)
        await test_db_session.commit()

        entry2 = ApiCacheEntry(
            cache_key="duplicate",
            endpoint="/test2",
            response_data="{}",
            expires_at=datetime.now() + timedelta(hours=1),
        )
        test_db_session.add(entry2)

        with pytest.raises(IntegrityError):
            await test_db_session.commit()
