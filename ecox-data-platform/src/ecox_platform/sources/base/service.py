"""Base service class for data fetching orchestration.

This module provides a base class for service layer implementations that
coordinate repository, cache, and database operations.
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any

import structlog
from ecox_shared.models import Dataset, DataValue, FetchLog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.infrastructure.cache import Cache
from ecox_platform.sources.base.repository import BaseRepository

logger = structlog.get_logger(__name__)


class BaseService:
    """Base service class for data fetching operations.

    Implements the common fetch-cache-store pattern used across all data sources.
    Subclasses should implement source-specific data transformation logic.
    """

    def __init__(
        self,
        repository: BaseRepository,
        cache: Cache,
        source_name: str,
    ) -> None:
        """Initialize the base service.

        Args:
            repository: Data source repository
            cache: Cache instance
            source_name: Name of the data source (e.g., "eurostat")
        """
        self.repository = repository
        self.cache = cache
        self.source_name = source_name

        logger.info("Service initialized", source=source_name)

    async def fetch_and_cache(
        self, dataset_code: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch data from source with cache checking.

        Args:
            dataset_code: Dataset identifier
            filters: Optional filters

        Returns:
            Dataset data

        Raises:
            Exception: If fetch fails
        """
        # Check cache first
        cached_data = self.cache.get(self.source_name, dataset_code, filters)
        if cached_data is not None:
            logger.info(
                "Using cached data",
                source=self.source_name,
                dataset_code=dataset_code,
            )
            return dict(cached_data)

        # Fetch from repository
        logger.info(
            "Fetching data from source",
            source=self.source_name,
            dataset_code=dataset_code,
            filters=filters,
        )
        data = await self.repository.get_dataset(dataset_code, filters)

        # Cache the result
        self.cache.set(self.source_name, dataset_code, data, filters)

        return data

    async def store_dataset(
        self,
        session: AsyncSession,
        dataset_code: str,
        dataset_name: str,
        description: str | None = None,
        source_last_update: str | None = None,
        source_url: str | None = None,
    ) -> Dataset:
        """Store or update a dataset record in the database.

        Args:
            session: Database session
            dataset_code: Dataset identifier
            dataset_name: Human-readable name
            description: Optional description
            source_last_update: Source's last update timestamp (from TOC/metadata)
            source_url: URL to the original dataset page on the source website

        Returns:
            Dataset model instance
        """
        # Check if dataset exists
        statement = select(Dataset).where(
            Dataset.code == dataset_code, Dataset.source == self.source_name
        )
        dataset = (await session.exec(statement)).one_or_none()

        if dataset:
            # Update existing dataset
            dataset.name = dataset_name
            dataset.description = description
            dataset.last_fetched = datetime.now()
            dataset.source_last_update = source_last_update
            dataset.source_url = source_url
            logger.debug("Updating existing dataset", dataset_code=dataset_code)
        else:
            # Create new dataset
            dataset = Dataset(
                code=dataset_code,
                name=dataset_name,
                source=self.source_name,
                description=description,
                last_fetched=datetime.now(),
                source_last_update=source_last_update,
                source_url=source_url,
            )
            session.add(dataset)
            logger.debug("Creating new dataset", dataset_code=dataset_code)

        await session.commit()
        await session.refresh(dataset)

        return dataset

    @staticmethod
    def compute_content_hash(values: list[dict[str, Any]]) -> str:
        """Compute SHA256 hash of dataset values for change detection.

        The hash is computed from a deterministic JSON representation of
        the values, sorted by (geo, time_period, indicator) to ensure
        consistent hashing regardless of input order.

        Args:
            values: List of data value dictionaries with keys:
                    geo, time_period, indicator, value, unit, flags

        Returns:
            SHA256 hex digest (64 characters)

        Note:
            The JSON serialization uses ``default=str`` intentionally to handle
            non-JSON-serializable types consistently:

            - ``Decimal`` values from database queries
            - ``numpy`` numeric types (float64, int64, etc.)
            - ``datetime`` objects if present in metadata
            - Any other custom numeric types from data sources

            This ensures the same logical data produces the same hash regardless
            of the Python type used to represent numeric values.
        """
        # Sort by natural key for deterministic ordering
        sorted_values = sorted(
            values,
            key=lambda v: (v.get("geo", ""), v.get("time_period", ""), v.get("indicator", "")),
        )

        # Create deterministic JSON (sorted keys, no extra whitespace)
        # Note: default=str handles Decimal, numpy types, datetime, etc.
        content = json.dumps(sorted_values, sort_keys=True, separators=(",", ":"), default=str)

        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def needs_update(
        self,
        session: AsyncSession,
        dataset_id: int,
        new_hash: str,
    ) -> bool:
        """Check if dataset content has changed and needs updating.

        Compares the provided hash with the stored content_hash.
        Returns True if:
        - Dataset has no stored hash (first fetch or legacy data)
        - Stored hash differs from new hash

        Args:
            session: Database session
            dataset_id: ID of the dataset to check
            new_hash: SHA256 hash of new content

        Returns:
            True if update is needed, False if content is unchanged
        """
        current_hash = (
            await session.exec(select(Dataset.content_hash).where(Dataset.id == dataset_id))
        ).one_or_none()

        if current_hash is None:
            logger.debug(
                "No existing hash, update needed",
                dataset_id=dataset_id,
            )
            return True

        if current_hash != new_hash:
            logger.debug(
                "Content hash changed, update needed",
                dataset_id=dataset_id,
                old_hash=current_hash[:16] + "...",
                new_hash=new_hash[:16] + "...",
            )
            return True

        logger.info(
            "Content unchanged, skipping update",
            dataset_id=dataset_id,
            hash=current_hash[:16] + "...",
        )
        return False

    async def update_content_hash(
        self,
        session: AsyncSession,
        dataset_id: int,
        content_hash: str,
    ) -> None:
        """Update the content_hash for a dataset.

        Args:
            session: Database session
            dataset_id: ID of the dataset
            content_hash: New SHA256 hash to store
        """
        dataset = (
            await session.exec(select(Dataset).where(Dataset.id == dataset_id))
        ).one_or_none()
        if dataset:
            dataset.content_hash = content_hash
            session.add(dataset)
            await session.commit()
            logger.debug(
                "Content hash updated",
                dataset_id=dataset_id,
                hash=content_hash[:16] + "...",
            )

    async def store_with_change_detection(
        self,
        session: AsyncSession,
        dataset: Dataset,
        value_dicts: list[dict[str, Any]],
        filters: dict[str, Any] | None = None,
        started_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Store data values with change detection and upsert.

        Common pattern used by all data source services:
        1. Compute content hash of new values
        2. Check if update needed (hash comparison)
        3. Skip storage if unchanged
        4. Upsert values if changed (preserves existing IDs)
        5. Update content hash
        6. Log fetch operation

        Args:
            session: Database session
            dataset: Dataset model instance (must be already committed)
            value_dicts: List of value dictionaries to store
            filters: Optional filters used in fetch (for logging)
            started_at: When the fetch operation started

        Returns:
            Dictionary with:
            - dataset_code: str
            - source: str
            - records_fetched: int
            - status: "unchanged" | "success"
            - upserted: int (only if status="success")
            - deleted: int (only if status="success")
        """
        dataset_code = dataset.code

        # Compute content hash for change detection
        new_hash = self.compute_content_hash(value_dicts)

        # Ensure dataset has been persisted (has an ID)
        if dataset.id is None:
            raise ValueError("Dataset must be persisted before storing values")
        dataset_id = dataset.id

        # Check if update is needed
        if not await self.needs_update(session, dataset_id, new_hash):
            logger.info(
                "Dataset unchanged, skipping storage",
                source=self.source_name,
                dataset_code=dataset_code,
                value_count=len(value_dicts),
            )

            await self.log_fetch(
                session=session,
                dataset_code=dataset_code,
                status="unchanged",
                records_fetched=len(value_dicts),
                filters=filters,
                started_at=started_at,
            )

            return {
                "dataset_code": dataset_code,
                "source": self.source_name,
                "records_fetched": len(value_dicts),
                "status": "unchanged",
            }

        # Content changed - upsert values (preserves existing IDs)
        upserted, _, deleted = await self.upsert_data_values(
            session=session,
            dataset_id=dataset_id,
            values=value_dicts,
        )

        # Update content hash after successful upsert
        await self.update_content_hash(session, dataset_id, new_hash)

        # Log successful fetch
        await self.log_fetch(
            session=session,
            dataset_code=dataset_code,
            status="success",
            records_fetched=upserted,
            filters=filters,
            started_at=started_at,
        )

        logger.info(
            "Dataset stored successfully",
            source=self.source_name,
            dataset_code=dataset_code,
            upserted=upserted,
            deleted=deleted,
        )

        return {
            "dataset_code": dataset_code,
            "source": self.source_name,
            "records_fetched": len(value_dicts),
            "status": "success",
            "upserted": upserted,
            "deleted": deleted,
        }

    async def store_data_values(
        self,
        session: AsyncSession,
        dataset_id: int,
        values: list[dict[str, Any]],
        batch_size: int = 4000,
    ) -> int:
        """Store data values in batches to avoid blocking the event loop.

        Note: batch_size is limited to 4000 because PostgreSQL/asyncpg has a
        32,767 parameter limit. With 7 fields per row, max is ~4,681 rows.

        Args:
            session: Database session
            dataset_id: ID of the parent dataset
            values: List of data value dictionaries
            batch_size: Number of records per batch (default 4000)

        Returns:
            Number of values stored
        """
        total_stored = 0
        total_batches = (len(values) + batch_size - 1) // batch_size

        for i in range(0, len(values), batch_size):
            batch = values[i : i + batch_size]
            data_values = [
                DataValue(
                    dataset_id=dataset_id,
                    geo=v["geo"],
                    time_period=v["time_period"],
                    indicator=v["indicator"],
                    value=v["value"],
                    unit=v.get("unit"),
                    flags=v.get("flags"),
                )
                for v in batch
            ]
            session.add_all(data_values)
            await session.commit()
            total_stored += len(batch)

            # Yield to event loop between batches
            await asyncio.sleep(0)

            logger.debug(
                "Batch stored",
                dataset_id=dataset_id,
                batch_num=i // batch_size + 1,
                total_batches=total_batches,
                batch_size=len(batch),
                total_stored=total_stored,
            )

        logger.info(
            "Data values stored",
            dataset_id=dataset_id,
            count=total_stored,
            batches=total_batches,
        )

        # Update record_count on the dataset for fast queries
        dataset = (
            await session.exec(select(Dataset).where(Dataset.id == dataset_id))
        ).one_or_none()
        if dataset:
            dataset.record_count = total_stored
            session.add(dataset)
            await session.commit()
            logger.debug(
                "Dataset record_count updated",
                dataset_id=dataset_id,
                record_count=total_stored,
            )

        return total_stored

    async def clear_dataset_values(
        self,
        session: AsyncSession,
        dataset_id: int,
    ) -> int:
        """Clear existing data values for a dataset before re-storing.

        Args:
            session: Database session
            dataset_id: ID of the parent dataset

        Returns:
            Number of values deleted
        """
        from sqlmodel import delete

        statement = delete(DataValue).where(DataValue.dataset_id == dataset_id)  # type: ignore[arg-type]
        result = await session.execute(statement)

        # Reset record_count to 0 since all values are cleared
        dataset = (
            await session.exec(select(Dataset).where(Dataset.id == dataset_id))
        ).one_or_none()
        if dataset:
            dataset.record_count = 0
            session.add(dataset)

        await session.commit()

        deleted_count: int = result.rowcount  # type: ignore[attr-defined]
        logger.info(
            "Data values cleared",
            dataset_id=dataset_id,
            deleted_count=deleted_count,
        )

        return deleted_count

    async def upsert_data_values(
        self,
        session: AsyncSession,
        dataset_id: int,
        values: list[dict[str, Any]],
        batch_size: int = 4000,
    ) -> tuple[int, int, int]:
        """Upsert data values, preserving existing IDs where possible.

        Uses database-specific upsert strategies:
        - PostgreSQL: INSERT ... ON CONFLICT DO UPDATE (efficient, preserves IDs)
        - SQLite/Other: Delete-then-insert strategy (compatible, works in tests)

        Also handles deletion of values no longer in the dataset.

        Note: batch_size is limited to 4000 because PostgreSQL/asyncpg has a
        32,767 parameter limit. With 7 fields per row, max is ~4,681 rows.

        Args:
            session: Database session
            dataset_id: ID of the parent dataset
            values: List of data value dictionaries
            batch_size: Number of records per batch (default 4000)

        Returns:
            Tuple of (upserted_count, updated_count, deleted_count)
            Note: updated_count is always 0 as exact counts aren't available
        """
        # Detect dialect from session's bind
        # Handle both real sessions and mock sessions gracefully
        try:
            bind = session.get_bind()
            dialect_name = bind.dialect.name if bind and hasattr(bind, "dialect") else "sqlite"
        except (AttributeError, TypeError):
            # Fall back to generic for mocks or sessions without bind
            dialect_name = "sqlite"

        logger.debug(
            "Upsert using dialect",
            dialect=dialect_name,
            dataset_id=dataset_id,
            value_count=len(values),
        )

        if dialect_name == "postgresql":
            return await self._upsert_postgresql(session, dataset_id, values, batch_size)
        else:
            return await self._upsert_generic(session, dataset_id, values, batch_size)

    async def _upsert_postgresql(
        self,
        session: AsyncSession,
        dataset_id: int,
        values: list[dict[str, Any]],
        batch_size: int,
    ) -> tuple[int, int, int]:
        """PostgreSQL-specific upsert using ON CONFLICT.

        Uses INSERT ... ON CONFLICT DO UPDATE for efficient upserts that
        preserve existing row IDs. All operations are performed in a single
        transaction with one commit at the end.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlmodel import delete

        if not values:
            # No values to upsert, just delete any existing
            delete_stmt = delete(DataValue).where(DataValue.dataset_id == dataset_id)  # type: ignore[arg-type]
            result = await session.execute(delete_stmt)
            deleted: int = result.rowcount  # type: ignore[attr-defined]
            await self._update_record_count(session, dataset_id, 0)
            await session.commit()
            return 0, 0, deleted

        # Deduplicate values - keep last occurrence for each (geo, time_period, indicator)
        # This prevents "ON CONFLICT DO UPDATE cannot affect row a second time" errors
        seen_keys: dict[tuple[str, str, str], int] = {}
        for idx, v in enumerate(values):
            key = (v["geo"], v["time_period"], v["indicator"])
            seen_keys[key] = idx

        if len(seen_keys) < len(values):
            # Duplicates found - extract unique values
            unique_indices = set(seen_keys.values())
            values = [v for idx, v in enumerate(values) if idx in unique_indices]
            logger.debug(
                "Deduplicated values for upsert",
                dataset_id=dataset_id,
                original_count=len(seen_keys) + (len(values) - len(seen_keys)),
                unique_count=len(values),
            )

        # Track keys we're upserting to identify deletions later
        new_keys: set[tuple[str, str, str]] = set(seen_keys.keys())

        total_batches = (len(values) + batch_size - 1) // batch_size
        total_upserted = 0

        # Phase 1: Upsert in batches (no intermediate commits)
        for i in range(0, len(values), batch_size):
            batch = values[i : i + batch_size]

            # Prepare insert statement with ON CONFLICT
            insert_stmt = pg_insert(DataValue).values(
                [
                    {
                        "dataset_id": dataset_id,
                        "geo": v["geo"],
                        "time_period": v["time_period"],
                        "indicator": v["indicator"],
                        "value": v["value"],
                        "unit": v.get("unit"),
                        "flags": v.get("flags"),
                    }
                    for v in batch
                ]
            )

            # ON CONFLICT update only the changeable fields
            upsert_stmt = insert_stmt.on_conflict_do_update(
                constraint="uq_datavalue_dataset_geo_time_indicator",
                set_={
                    "value": insert_stmt.excluded.value,
                    "unit": insert_stmt.excluded.unit,
                    "flags": insert_stmt.excluded.flags,
                },
            )

            await session.execute(upsert_stmt)
            total_upserted += len(batch)

            # Yield to event loop between batches
            await asyncio.sleep(0)

            logger.debug(
                "Upsert batch completed",
                dataset_id=dataset_id,
                batch_num=i // batch_size + 1,
                total_batches=total_batches,
                batch_size=len(batch),
            )

        # Phase 2: Delete obsolete values (no commit - same transaction)
        deleted_count = await self._delete_obsolete_values_sql(session, dataset_id, new_keys)

        # Phase 3: Update record_count (no commit - same transaction)
        await self._update_record_count(session, dataset_id, len(values))

        # Single commit for entire operation (atomic transaction)
        await session.commit()

        logger.info(
            "Upsert completed (postgresql)",
            dataset_id=dataset_id,
            total_upserted=total_upserted,
            deleted=deleted_count,
            final_count=len(values),
        )

        # Return estimates (exact counts not available with ON CONFLICT)
        return total_upserted, 0, deleted_count

    async def _upsert_generic(
        self,
        session: AsyncSession,
        dataset_id: int,
        values: list[dict[str, Any]],
        batch_size: int,
    ) -> tuple[int, int, int]:
        """Generic upsert for SQLite and other databases.

        Uses delete-then-insert strategy which works across all SQL databases.
        Less efficient than PostgreSQL ON CONFLICT but fully compatible.
        """
        from sqlmodel import delete

        if not values:
            # No values to upsert, just delete any existing
            delete_all_stmt = delete(DataValue).where(DataValue.dataset_id == dataset_id)  # type: ignore[arg-type]
            result = await session.execute(delete_all_stmt)
            deleted: int = result.rowcount  # type: ignore[attr-defined]
            await session.commit()
            return 0, 0, deleted

        # Build set of new keys
        new_keys: set[tuple[str, str, str]] = set()
        for v in values:
            new_keys.add((v["geo"], v["time_period"], v["indicator"]))

        # Count existing values before deletion (for accurate deleted count)
        existing_result = await session.execute(
            select(DataValue.id, DataValue.geo, DataValue.time_period, DataValue.indicator).where(
                DataValue.dataset_id == dataset_id
            )
        )
        existing_rows = existing_result.all()

        # Find rows that will be deleted (not in new values)
        deleted_count = sum(
            1 for row in existing_rows if (row.geo, row.time_period, row.indicator) not in new_keys
        )

        # Delete all existing values for this dataset
        delete_stmt = delete(DataValue).where(DataValue.dataset_id == dataset_id)  # type: ignore[arg-type]
        await session.execute(delete_stmt)

        # Insert all new values using raw SQL to avoid BigInteger/SQLite issues
        # (SQLite doesn't auto-generate IDs for BigInteger columns)
        from sqlalchemy import text

        total_batches = (len(values) + batch_size - 1) // batch_size
        total_inserted = 0

        # Use raw SQL to let SQLite handle ID generation via ROWID
        insert_sql = text("""
            INSERT INTO datavalue (dataset_id, geo, time_period, indicator, value, unit, flags)
            VALUES (:dataset_id, :geo, :time_period, :indicator, :value, :unit, :flags)
        """)

        for i in range(0, len(values), batch_size):
            batch = values[i : i + batch_size]
            # Execute each row individually (SQLite doesn't support multi-row VALUES)
            for v in batch:
                await session.execute(
                    insert_sql,
                    {
                        "dataset_id": dataset_id,
                        "geo": v["geo"],
                        "time_period": v["time_period"],
                        "indicator": v["indicator"],
                        "value": v["value"],
                        "unit": v.get("unit"),
                        "flags": v.get("flags"),
                    },
                )
            total_inserted += len(batch)

            # Yield to event loop between batches
            await asyncio.sleep(0)

            logger.debug(
                "Insert batch completed",
                dataset_id=dataset_id,
                batch_num=i // batch_size + 1,
                total_batches=total_batches,
                batch_size=len(batch),
            )

        # Update record_count (no commit - same transaction)
        await self._update_record_count(session, dataset_id, len(values))

        # Single commit for entire operation (atomic transaction)
        await session.commit()

        logger.info(
            "Upsert completed (generic)",
            dataset_id=dataset_id,
            total_inserted=total_inserted,
            deleted=deleted_count,
            final_count=len(values),
        )

        return total_inserted, 0, deleted_count

    async def _delete_obsolete_values_sql(
        self,
        session: AsyncSession,
        dataset_id: int,
        new_keys: set[tuple[str, str, str]],
        batch_size: int = 1000,
    ) -> int:
        """Delete values not in new_keys using a scalable approach.

        Fetches existing keys, calculates diff in Python, then deletes in batches.
        This avoids "stack depth limit exceeded" errors from huge NOT IN lists.

        Note: This method does NOT commit - the caller is responsible for
        managing the transaction boundary.

        Args:
            session: Database session
            dataset_id: ID of the dataset
            new_keys: Set of (geo, time_period, indicator) tuples to keep
            batch_size: Number of keys to delete per batch

        Returns:
            Number of rows deleted
        """
        from sqlalchemy import tuple_
        from sqlmodel import delete, select

        if not new_keys:
            # Delete all values for this dataset
            delete_all_stmt = delete(DataValue).where(DataValue.dataset_id == dataset_id)  # type: ignore[arg-type]
            del_result = await session.execute(delete_all_stmt)
            count: int = del_result.rowcount  # type: ignore[attr-defined]
            return count

        # Fetch existing keys for this dataset
        select_stmt = select(DataValue.geo, DataValue.time_period, DataValue.indicator).where(
            DataValue.dataset_id == dataset_id
        )
        result = await session.execute(select_stmt)
        existing_keys = {(row.geo, row.time_period, row.indicator) for row in result}

        # Calculate which keys need to be deleted
        keys_to_delete = existing_keys - new_keys

        if not keys_to_delete:
            return 0

        # Delete in batches to avoid stack depth issues
        total_deleted = 0
        keys_list = list(keys_to_delete)

        for i in range(0, len(keys_list), batch_size):
            batch = keys_list[i : i + batch_size]

            batch_delete_stmt = (
                delete(DataValue)
                .where(DataValue.dataset_id == dataset_id)  # type: ignore[arg-type]
                .where(
                    tuple_(
                        DataValue.geo,  # type: ignore[arg-type]
                        DataValue.time_period,  # type: ignore[arg-type]
                        DataValue.indicator,  # type: ignore[arg-type]
                    ).in_(batch)
                )
            )

            batch_result = await session.execute(batch_delete_stmt)
            total_deleted += batch_result.rowcount  # type: ignore[attr-defined]

            # Yield to event loop between batches
            await asyncio.sleep(0)

        if total_deleted > 0:
            logger.debug(
                "Deleted obsolete values",
                dataset_id=dataset_id,
                deleted_count=total_deleted,
            )

        return total_deleted

    async def _update_record_count(
        self,
        session: AsyncSession,
        dataset_id: int,
        count: int,
    ) -> None:
        """Update dataset record_count without committing.

        Note: This method does NOT commit - the caller is responsible for
        managing the transaction boundary.

        Args:
            session: Database session
            dataset_id: ID of the dataset
            count: New record count
        """
        dataset = (
            await session.exec(select(Dataset).where(Dataset.id == dataset_id))
        ).one_or_none()
        if dataset:
            dataset.record_count = count
            session.add(dataset)

    async def log_fetch(
        self,
        session: AsyncSession,
        dataset_code: str,
        status: str,
        records_fetched: int | None = None,
        error_message: str | None = None,
        filters: dict[str, Any] | None = None,
        started_at: datetime | None = None,
    ) -> None:
        """Log a fetch operation.

        Args:
            session: Database session
            dataset_code: Dataset identifier
            status: Status ('success', 'error', 'partial')
            records_fetched: Number of records fetched
            error_message: Error message if failed
            filters: Filters used
            started_at: When the fetch started
        """
        completed_at = datetime.now()
        duration = None
        if started_at:
            duration = (completed_at - started_at).total_seconds()

        fetch_log = FetchLog(
            dataset_code=dataset_code,
            source=self.source_name,
            status=status,
            records_fetched=records_fetched,
            error_message=error_message,
            filters=json.dumps(filters) if filters else None,
            started_at=started_at or completed_at,
            completed_at=completed_at,
            duration_seconds=duration,
        )

        session.add(fetch_log)
        await session.commit()

        logger.info(
            "Fetch operation logged",
            dataset_code=dataset_code,
            status=status,
            records_fetched=records_fetched,
            duration_seconds=duration,
        )

    async def fetch_and_store(
        self,
        dataset_code: str,
        filters: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Fetch data and store it in the database.

        This is the main method to be implemented by subclasses.
        The default implementation provides a template that subclasses
        should override with source-specific logic.

        Args:
            dataset_code: Dataset identifier
            filters: Optional filters
            session: Database session (required for storing)

        Returns:
            Dictionary with fetch results

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement fetch_and_store")
