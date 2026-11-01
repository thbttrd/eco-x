"""Tests for BaseService.upsert_data_values() functionality.

These tests verify the upsert behavior including:
- Insert new values
- Update existing values
- Delete obsolete values
- Empty input handling
- Large batch handling
- Record count updates

Note: These tests use SQLite with custom table definitions to work around
the BigInteger/auto-increment incompatibility in the production models.
"""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from ecox_shared.models import Dataset
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.infrastructure.cache import Cache
from ecox_platform.sources.base.service import BaseService


class TestUpsertDataValues:
    """Tests for upsert_data_values method."""

    @pytest.fixture
    async def upsert_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Create a test database session with SQLite-compatible table definitions.

        Creates tables using raw SQL to ensure INTEGER PRIMARY KEY for auto-increment.
        This works around the BigInteger limitation in the production DataValue model.
        """
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Create tables with SQLite-compatible DDL (INTEGER PRIMARY KEY for auto-increment)
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS dataset (
                    id INTEGER PRIMARY KEY,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    description TEXT,
                    last_fetched TIMESTAMP,
                    record_count INTEGER DEFAULT 0,
                    content_hash TEXT,
                    extra_metadata TEXT,
                    source_last_update TEXT,
                    source_url TEXT
                )
            """)
            )
            await conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS datavalue (
                    id INTEGER PRIMARY KEY,
                    dataset_id INTEGER NOT NULL REFERENCES dataset(id),
                    geo TEXT NOT NULL,
                    time_period TEXT NOT NULL,
                    indicator TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT,
                    flags TEXT
                )
            """)
            )
            await conn.execute(
                text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_datavalue_dataset_geo_time_indicator
                ON datavalue(dataset_id, geo, time_period, indicator)
            """)
            )

        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

        await engine.dispose()

    @pytest.fixture
    def service(self) -> BaseService:
        """Create a BaseService instance for testing."""
        return BaseService(
            repository=MagicMock(),
            cache=Cache(ttl_seconds=60),
            source_name="test",
        )

    @pytest.fixture
    async def dataset(self, upsert_db_session) -> Dataset:
        """Create a test dataset using raw SQL."""
        await upsert_db_session.execute(
            text("""
            INSERT INTO dataset (code, name, source, record_count)
            VALUES ('TEST_DATASET', 'Test Dataset', 'test', 0)
        """)
        )
        await upsert_db_session.commit()

        # Fetch the created dataset
        result = await upsert_db_session.execute(
            text(
                "SELECT id, code, name, source, record_count FROM dataset WHERE code = 'TEST_DATASET'"
            )
        )
        row = result.fetchone()

        # Create a Dataset object with the fetched data
        dataset = Dataset(
            id=row[0],
            code=row[1],
            name=row[2],
            source=row[3],
            record_count=row[4],
        )
        return dataset

    @pytest.mark.asyncio
    async def test_upsert_insert_new_values(
        self, service: BaseService, upsert_db_session, dataset: Dataset
    ) -> None:
        """Test inserting new values into empty dataset."""
        values = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
            {"geo": "DE", "time_period": "2022", "indicator": "GDP", "value": 2000.0},
        ]

        inserted, updated, deleted = await service.upsert_data_values(
            upsert_db_session, dataset.id, values
        )

        assert inserted == 2
        assert updated == 0
        assert deleted == 0

        # Verify values in database
        result = await upsert_db_session.execute(
            text("SELECT COUNT(*) FROM datavalue WHERE dataset_id = :id"),
            {"id": dataset.id},
        )
        count = result.scalar()
        assert count == 2

    @pytest.mark.asyncio
    async def test_upsert_update_existing_values(
        self, service: BaseService, upsert_db_session, dataset: Dataset
    ) -> None:
        """Test updating existing values changes value field."""
        # Insert initial values using upsert (clean approach)
        initial_values = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
        ]
        await service.upsert_data_values(upsert_db_session, dataset.id, initial_values)

        # Upsert with updated value
        updated_values = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1500.0},
        ]

        inserted, updated, deleted = await service.upsert_data_values(
            upsert_db_session, dataset.id, updated_values
        )

        # In generic (SQLite) mode: deletes old, inserts new
        # So inserted=1, updated=0, deleted=0 (no net deletion since same key)
        assert inserted == 1
        assert deleted == 0

        # Verify value updated
        result = await upsert_db_session.execute(
            text("SELECT value FROM datavalue WHERE dataset_id = :id AND geo = 'FR'"),
            {"id": dataset.id},
        )
        value = result.scalar()
        assert value == 1500.0

    @pytest.mark.asyncio
    async def test_upsert_delete_obsolete_values(
        self, service: BaseService, upsert_db_session, dataset: Dataset
    ) -> None:
        """Test that values not in new data are deleted."""
        # Insert initial values
        initial_values = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
            {"geo": "DE", "time_period": "2022", "indicator": "GDP", "value": 2000.0},
            {"geo": "IT", "time_period": "2022", "indicator": "GDP", "value": 3000.0},
        ]
        await service.upsert_data_values(upsert_db_session, dataset.id, initial_values)

        # Upsert with only FR (should delete DE, IT)
        new_values = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
        ]

        inserted, updated, deleted = await service.upsert_data_values(
            upsert_db_session, dataset.id, new_values
        )

        assert deleted == 2

        # Verify only FR remains
        result = await upsert_db_session.execute(
            text("SELECT geo FROM datavalue WHERE dataset_id = :id"),
            {"id": dataset.id},
        )
        geos = [row[0] for row in result.fetchall()]
        assert geos == ["FR"]

    @pytest.mark.asyncio
    async def test_upsert_mixed_operations(
        self, service: BaseService, upsert_db_session, dataset: Dataset
    ) -> None:
        """Test mixed insert, update, and delete in single upsert."""
        # Insert initial values: FR=1000, DE=2000
        initial_values = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
            {"geo": "DE", "time_period": "2022", "indicator": "GDP", "value": 2000.0},
        ]
        await service.upsert_data_values(upsert_db_session, dataset.id, initial_values)

        # Upsert: Update FR, Add IT, Delete DE
        new_values = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1500.0},  # Update
            {"geo": "IT", "time_period": "2022", "indicator": "GDP", "value": 3000.0},  # Insert
        ]

        inserted, updated, deleted = await service.upsert_data_values(
            upsert_db_session, dataset.id, new_values
        )

        # Generic upsert (SQLite) deletes obsolete then inserts fresh
        assert deleted == 1  # DE deleted
        assert inserted == 2  # FR and IT inserted

        # Verify final state
        result = await upsert_db_session.execute(
            text("SELECT geo, value FROM datavalue WHERE dataset_id = :id ORDER BY geo"),
            {"id": dataset.id},
        )
        rows = result.fetchall()
        values_dict = {row[0]: row[1] for row in rows}

        assert len(values_dict) == 2
        assert values_dict["FR"] == 1500.0
        assert values_dict["IT"] == 3000.0
        assert "DE" not in values_dict

    @pytest.mark.asyncio
    async def test_upsert_empty_input_deletes_all(
        self, service: BaseService, upsert_db_session, dataset: Dataset
    ) -> None:
        """Test that empty values list deletes all existing values."""
        # Insert initial values
        initial_values = [
            {"geo": f"GEO_{i}", "time_period": "2022", "indicator": "GDP", "value": float(i * 1000)}
            for i in range(5)
        ]
        await service.upsert_data_values(upsert_db_session, dataset.id, initial_values)

        # Verify values exist
        result = await upsert_db_session.execute(
            text("SELECT COUNT(*) FROM datavalue WHERE dataset_id = :id"),
            {"id": dataset.id},
        )
        assert result.scalar() == 5

        # Upsert with empty list
        inserted, updated, deleted = await service.upsert_data_values(
            upsert_db_session, dataset.id, []
        )

        assert inserted == 0
        assert deleted == 5

        # Verify all deleted
        result = await upsert_db_session.execute(
            text("SELECT COUNT(*) FROM datavalue WHERE dataset_id = :id"),
            {"id": dataset.id},
        )
        assert result.scalar() == 0

    @pytest.mark.asyncio
    async def test_upsert_large_batch(
        self, service: BaseService, upsert_db_session, dataset: Dataset
    ) -> None:
        """Test upserting more values than batch_size."""
        # Create 150 values (batch_size=50 for test)
        values = [
            {
                "geo": f"GEO_{i}",
                "time_period": "2022",
                "indicator": "GDP",
                "value": float(i * 100),
            }
            for i in range(150)
        ]

        inserted, updated, deleted = await service.upsert_data_values(
            upsert_db_session, dataset.id, values, batch_size=50
        )

        assert inserted == 150

        # Verify all values inserted
        result = await upsert_db_session.execute(
            text("SELECT COUNT(*) FROM datavalue WHERE dataset_id = :id"),
            {"id": dataset.id},
        )
        assert result.scalar() == 150

    @pytest.mark.asyncio
    async def test_upsert_updates_record_count(
        self, service: BaseService, upsert_db_session, dataset: Dataset
    ) -> None:
        """Test that dataset.record_count is updated after upsert."""
        values = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
            {"geo": "DE", "time_period": "2022", "indicator": "GDP", "value": 2000.0},
        ]

        await service.upsert_data_values(upsert_db_session, dataset.id, values)

        # Check record_count directly in database
        result = await upsert_db_session.execute(
            text("SELECT record_count FROM dataset WHERE id = :id"),
            {"id": dataset.id},
        )
        record_count = result.scalar()
        assert record_count == 2

    @pytest.mark.asyncio
    async def test_upsert_with_optional_fields(
        self, service: BaseService, upsert_db_session, dataset: Dataset
    ) -> None:
        """Test upsert with optional unit and flags fields."""
        values = [
            {
                "geo": "FR",
                "time_period": "2022",
                "indicator": "GDP",
                "value": 1000.0,
                "unit": "EUR",
                "flags": "e",
            },
            {
                "geo": "DE",
                "time_period": "2022",
                "indicator": "GDP",
                "value": 2000.0,
                # No unit or flags - should be None
            },
        ]

        await service.upsert_data_values(upsert_db_session, dataset.id, values)

        # Verify values with optional fields
        result = await upsert_db_session.execute(
            text("SELECT geo, unit, flags FROM datavalue WHERE dataset_id = :id ORDER BY geo"),
            {"id": dataset.id},
        )
        rows = result.fetchall()

        # DE (first alphabetically)
        assert rows[0][0] == "DE"
        assert rows[0][1] is None
        assert rows[0][2] is None

        # FR
        assert rows[1][0] == "FR"
        assert rows[1][1] == "EUR"
        assert rows[1][2] == "e"

    @pytest.mark.asyncio
    async def test_upsert_preserves_other_datasets(
        self, service: BaseService, upsert_db_session, dataset: Dataset
    ) -> None:
        """Test that upsert only affects the target dataset."""
        # Create another dataset using raw SQL
        await upsert_db_session.execute(
            text("""
            INSERT INTO dataset (code, name, source, record_count)
            VALUES ('OTHER_DATASET', 'Other Dataset', 'test', 0)
        """)
        )
        await upsert_db_session.commit()

        # Get other dataset id
        result = await upsert_db_session.execute(
            text("SELECT id FROM dataset WHERE code = 'OTHER_DATASET'")
        )
        other_dataset_id = result.scalar()

        # Insert values in both datasets via upsert
        await service.upsert_data_values(
            upsert_db_session,
            dataset.id,
            [{"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0}],
        )
        await service.upsert_data_values(
            upsert_db_session,
            other_dataset_id,
            [{"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 5000.0}],
        )

        # Upsert target dataset with new value
        await service.upsert_data_values(
            upsert_db_session,
            dataset.id,
            [{"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 2000.0}],
        )

        # Verify target dataset updated
        result = await upsert_db_session.execute(
            text("SELECT value FROM datavalue WHERE dataset_id = :id"),
            {"id": dataset.id},
        )
        target_value = result.scalar()
        assert target_value == 2000.0

        # Verify other dataset unchanged
        result = await upsert_db_session.execute(
            text("SELECT value FROM datavalue WHERE dataset_id = :id"),
            {"id": other_dataset_id},
        )
        other_value = result.scalar()
        assert other_value == 5000.0
