"""Tests for preference models."""

from datetime import datetime

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_client.models.preferences import FavoriteDataset, UserPreference


class TestUserPreference:
    """Tests for UserPreference model."""

    def test_preference_creation(self) -> None:
        """Test creating a user preference."""
        pref = UserPreference(key="language", value="fr")
        assert pref.key == "language"
        assert pref.value == "fr"

    def test_preference_defaults(self) -> None:
        """Test preference has default updated_at."""
        before = datetime.now()
        pref = UserPreference(key="theme", value="dark")
        after = datetime.now()
        assert before <= pref.updated_at <= after


class TestUserPreferenceDatabase:
    """Tests for UserPreference with database."""

    async def test_save_preference(self, test_db_session: AsyncSession) -> None:
        """Test saving a preference to database."""
        pref = UserPreference(key="language", value="en")
        test_db_session.add(pref)
        await test_db_session.commit()

        assert pref.id is not None

    async def test_retrieve_preference(self, test_db_session: AsyncSession) -> None:
        """Test retrieving a preference by key."""
        pref = UserPreference(key="theme", value="dark")
        test_db_session.add(pref)
        await test_db_session.commit()

        result = await test_db_session.execute(
            select(UserPreference).where(UserPreference.key == "theme")
        )
        retrieved = result.scalar_one()

        assert retrieved.key == "theme"
        assert retrieved.value == "dark"

    async def test_unique_key(self, test_db_session: AsyncSession) -> None:
        """Test preference key is unique."""
        from sqlalchemy.exc import IntegrityError

        pref1 = UserPreference(key="unique_key", value="value1")
        test_db_session.add(pref1)
        await test_db_session.commit()

        pref2 = UserPreference(key="unique_key", value="value2")
        test_db_session.add(pref2)

        with pytest.raises(IntegrityError):
            await test_db_session.commit()

    async def test_update_preference(self, test_db_session: AsyncSession) -> None:
        """Test updating a preference value."""
        pref = UserPreference(key="language", value="en")
        test_db_session.add(pref)
        await test_db_session.commit()

        # Update the value
        pref.value = "fr"
        pref.updated_at = datetime.now()
        await test_db_session.commit()

        result = await test_db_session.execute(
            select(UserPreference).where(UserPreference.key == "language")
        )
        updated = result.scalar_one()

        assert updated.value == "fr"


class TestFavoriteDataset:
    """Tests for FavoriteDataset model."""

    def test_favorite_creation(self) -> None:
        """Test creating a favorite dataset."""
        fav = FavoriteDataset(
            source="eurostat",
            dataset_code="nama_10_gdp",
            display_name="GDP",
        )
        assert fav.source == "eurostat"
        assert fav.dataset_code == "nama_10_gdp"
        assert fav.display_name == "GDP"

    def test_favorite_without_display_name(self) -> None:
        """Test favorite without custom display name."""
        fav = FavoriteDataset(source="fred", dataset_code="GDP")
        assert fav.display_name is None

    def test_favorite_defaults(self) -> None:
        """Test favorite has default created_at."""
        before = datetime.now()
        fav = FavoriteDataset(source="eurostat", dataset_code="test")
        after = datetime.now()
        assert before <= fav.created_at <= after


class TestFavoriteDatasetDatabase:
    """Tests for FavoriteDataset with database."""

    async def test_save_favorite(self, test_db_session: AsyncSession) -> None:
        """Test saving a favorite to database."""
        fav = FavoriteDataset(
            source="eurostat",
            dataset_code="nama_10_gdp",
        )
        test_db_session.add(fav)
        await test_db_session.commit()

        assert fav.id is not None

    async def test_retrieve_favorites_by_source(self, test_db_session: AsyncSession) -> None:
        """Test retrieving favorites by source."""
        fav1 = FavoriteDataset(source="eurostat", dataset_code="ds1")
        fav2 = FavoriteDataset(source="eurostat", dataset_code="ds2")
        fav3 = FavoriteDataset(source="fred", dataset_code="GDP")

        test_db_session.add_all([fav1, fav2, fav3])
        await test_db_session.commit()

        result = await test_db_session.execute(
            select(FavoriteDataset).where(FavoriteDataset.source == "eurostat")
        )
        eurostat_favs = result.scalars().all()

        assert len(eurostat_favs) == 2
        assert all(f.source == "eurostat" for f in eurostat_favs)

    async def test_delete_favorite(self, test_db_session: AsyncSession) -> None:
        """Test deleting a favorite."""
        fav = FavoriteDataset(source="eurostat", dataset_code="to_delete")
        test_db_session.add(fav)
        await test_db_session.commit()

        fav_id = fav.id
        await test_db_session.delete(fav)
        await test_db_session.commit()

        result = await test_db_session.execute(
            select(FavoriteDataset).where(FavoriteDataset.id == fav_id)
        )
        assert result.scalar_one_or_none() is None
