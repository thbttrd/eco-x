"""Tests for FetchLog model."""

from datetime import datetime, timedelta

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_shared.models import FetchLog


class TestFetchLog:
    """Tests for FetchLog model."""

    def test_fetchlog_creation(self) -> None:
        """Test creating a FetchLog instance."""
        log = FetchLog(
            dataset_code="nama_10_gdp",
            source="eurostat",
            status="success",
        )
        assert log.dataset_code == "nama_10_gdp"
        assert log.source == "eurostat"
        assert log.status == "success"
        assert log.id is None
        assert log.records_fetched is None
        assert log.error_message is None
        assert log.started_at is not None

    def test_fetchlog_success(self) -> None:
        """Test creating a successful fetch log."""
        started = datetime.now()
        completed = started + timedelta(seconds=5.5)

        log = FetchLog(
            dataset_code="nama_10_gdp",
            source="eurostat",
            status="success",
            records_fetched=1500,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.5,
        )
        assert log.status == "success"
        assert log.records_fetched == 1500
        assert log.error_message is None
        assert log.duration_seconds == 5.5

    def test_fetchlog_error(self) -> None:
        """Test creating a failed fetch log."""
        log = FetchLog(
            dataset_code="invalid_dataset",
            source="eurostat",
            status="error",
            records_fetched=0,
            error_message="Dataset not found: 404",
        )
        assert log.status == "error"
        assert log.records_fetched == 0
        assert log.error_message == "Dataset not found: 404"

    def test_fetchlog_partial(self) -> None:
        """Test creating a partial success fetch log."""
        log = FetchLog(
            dataset_code="large_dataset",
            source="eurostat",
            status="partial",
            records_fetched=500,
            error_message="Rate limited after 500 records",
        )
        assert log.status == "partial"
        assert log.records_fetched == 500
        assert log.error_message is not None

    def test_fetchlog_with_filters(self) -> None:
        """Test fetch log with filters."""
        log = FetchLog(
            dataset_code="nama_10_gdp",
            source="eurostat",
            status="success",
            records_fetched=100,
            filters='{"geo": "EU27_2020", "time": "2022"}',
        )
        assert log.filters == '{"geo": "EU27_2020", "time": "2022"}'

    def test_fetchlog_status_values(self) -> None:
        """Test that status accepts valid values."""
        for status in ["success", "error", "partial"]:
            log = FetchLog(
                dataset_code="test",
                source="eurostat",
                status=status,
            )
            assert log.status == status

    def test_fetchlog_started_at_default(self) -> None:
        """Test that started_at has a default value."""
        before = datetime.now()
        log = FetchLog(
            dataset_code="test",
            source="eurostat",
            status="success",
        )
        after = datetime.now()

        assert before <= log.started_at <= after

    @pytest.mark.asyncio
    async def test_fetchlog_persistence(self, test_db_session: AsyncSession) -> None:
        """Test persisting a FetchLog to the database."""
        log = FetchLog(
            dataset_code="test_dataset",
            source="eurostat",
            status="success",
            records_fetched=100,
        )
        test_db_session.add(log)
        await test_db_session.commit()
        await test_db_session.refresh(log)

        assert log.id is not None
        assert log.id > 0

    @pytest.mark.asyncio
    async def test_fetchlog_query_by_source(self, test_db_session: AsyncSession) -> None:
        """Test querying fetch logs by source."""
        from sqlmodel import select

        # Create logs for different sources
        log1 = FetchLog(
            dataset_code="dataset1",
            source="eurostat",
            status="success",
        )
        log2 = FetchLog(
            dataset_code="dataset2",
            source="fred",
            status="success",
        )
        log3 = FetchLog(
            dataset_code="dataset3",
            source="eurostat",
            status="error",
        )
        test_db_session.add_all([log1, log2, log3])
        await test_db_session.commit()

        # Query by source
        statement = select(FetchLog).where(FetchLog.source == "eurostat")
        result = await test_db_session.exec(statement)
        eurostat_logs = result.all()

        assert len(eurostat_logs) == 2
        assert all(log.source == "eurostat" for log in eurostat_logs)
