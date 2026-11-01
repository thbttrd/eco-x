"""Tests for SourceMetadata model."""

from datetime import datetime

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_shared.models import SourceMetadata


class TestSourceMetadata:
    """Tests for SourceMetadata model."""

    def test_source_metadata_creation(self) -> None:
        """Test creating a SourceMetadata instance."""
        source = SourceMetadata(
            source="eurostat",
            total_datasets=5000,
        )
        assert source.source == "eurostat"
        assert source.total_datasets == 5000
        assert source.cached_toc is None
        assert source.id is None

    def test_source_metadata_with_toc(self) -> None:
        """Test SourceMetadata with cached TOC."""
        toc_data = '[{"code": "nama_10_gdp", "name": "GDP"}]'
        source = SourceMetadata(
            source="eurostat",
            total_datasets=1,
            cached_toc=toc_data,
        )
        assert source.cached_toc == toc_data

    def test_source_metadata_defaults(self) -> None:
        """Test default values for SourceMetadata."""
        source = SourceMetadata(source="fred")
        assert source.total_datasets == 0  # Default value
        assert source.cached_toc is None
        assert source.last_updated is not None

    def test_source_metadata_last_updated_default(self) -> None:
        """Test that last_updated has a default value."""
        before = datetime.now()
        source = SourceMetadata(source="eurostat")
        after = datetime.now()

        assert before <= source.last_updated <= after

    @pytest.mark.asyncio
    async def test_source_metadata_persistence(self, test_db_session: AsyncSession) -> None:
        """Test persisting SourceMetadata to the database."""
        source = SourceMetadata(
            source="eurostat",
            total_datasets=5000,
        )
        test_db_session.add(source)
        await test_db_session.commit()
        await test_db_session.refresh(source)

        assert source.id is not None
        assert source.id > 0

    @pytest.mark.asyncio
    async def test_source_metadata_unique_constraint(self, test_db_session: AsyncSession) -> None:
        """Test that source field is unique."""
        from sqlalchemy.exc import IntegrityError

        source1 = SourceMetadata(
            source="eurostat",
            total_datasets=5000,
        )
        test_db_session.add(source1)
        await test_db_session.commit()

        # Try to create another with same source
        source2 = SourceMetadata(
            source="eurostat",
            total_datasets=6000,
        )
        test_db_session.add(source2)

        with pytest.raises(IntegrityError):
            await test_db_session.commit()

    @pytest.mark.asyncio
    async def test_source_metadata_update(self, test_db_session: AsyncSession) -> None:
        """Test updating SourceMetadata."""
        source = SourceMetadata(
            source="eurostat",
            total_datasets=5000,
        )
        test_db_session.add(source)
        await test_db_session.commit()

        # Update
        source.total_datasets = 5500
        source.last_updated = datetime.now()
        await test_db_session.commit()
        await test_db_session.refresh(source)

        assert source.total_datasets == 5500
