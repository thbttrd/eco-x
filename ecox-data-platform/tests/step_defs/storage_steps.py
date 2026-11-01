"""Storage and history-related step definitions for BDD tests."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from ecox_shared.models import DatasetMetadata, DataValue, FetchLog
from pytest_bdd import parsers, then, when
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# ==============================================================================
# Helper for running async code in sync step definitions
# ==============================================================================


def run_async(coro):
    """Run async coroutine in sync context for pytest-bdd compatibility."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import nest_asyncio

        nest_asyncio.apply()
        return asyncio.get_event_loop().run_until_complete(coro)
    else:
        return asyncio.get_event_loop().run_until_complete(coro)


# ==============================================================================
# When Steps - Storage Operations
# ==============================================================================


@when("I store data values for the dataset")
def store_data_values(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
) -> None:
    """Store data values for a dataset."""
    dataset = scenario_context.get("dataset")
    if not dataset:
        raise ValueError("No dataset in context. Use 'a dataset exists' step first.")

    async def _store():
        values = [
            DataValue(
                dataset_id=dataset.id,
                geo="EU27",
                time_period="2023",
                indicator="GDP",
                value=15000000.0,
                unit="EUR",
            ),
            DataValue(
                dataset_id=dataset.id,
                geo="FR",
                time_period="2023",
                indicator="GDP",
                value=2500000.0,
                unit="EUR",
            ),
        ]
        for v in values:
            test_db_session.add(v)
        await test_db_session.commit()

        # Store for later assertions
        scenario_context["stored_values"] = values

    run_async(_store())


@when("I update the dataset metadata")
def update_dataset_metadata(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
) -> None:
    """Update dataset metadata using key-value pattern."""
    dataset = scenario_context.get("dataset")
    if not dataset:
        raise ValueError("No dataset in context.")

    async def _update():
        # Store last_updated timestamp as metadata key-value
        now = datetime.now(UTC)
        metadata = DatasetMetadata(
            dataset_id=dataset.id,
            key="last_updated",
            value=json.dumps({"timestamp": now.isoformat(), "row_count": 1000}),
        )
        test_db_session.add(metadata)
        await test_db_session.commit()
        await test_db_session.refresh(metadata)
        scenario_context["metadata"] = metadata

    run_async(_update())


@when("a successful fetch is logged for the dataset")
def log_successful_fetch(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
) -> None:
    """Log a successful fetch operation."""
    dataset = scenario_context.get("dataset")
    if not dataset:
        raise ValueError("No dataset in context.")

    async def _log():
        fetch_log = FetchLog(
            dataset_code=dataset.code,
            source=dataset.source,
            status="success",
            records_fetched=500,
            duration_seconds=1.5,
            started_at=datetime.now(UTC),
        )
        test_db_session.add(fetch_log)
        await test_db_session.commit()
        await test_db_session.refresh(fetch_log)
        scenario_context["fetch_log"] = fetch_log

    run_async(_log())


@when(parsers.parse('a failed fetch is logged for the dataset with error "{error}"'))
def log_failed_fetch(
    test_db_session: AsyncSession,
    error: str,
    scenario_context: dict[str, Any],
) -> None:
    """Log a failed fetch operation."""
    dataset = scenario_context.get("dataset")
    if not dataset:
        raise ValueError("No dataset in context.")

    async def _log():
        fetch_log = FetchLog(
            dataset_code=dataset.code,
            source=dataset.source,
            status="error",
            records_fetched=0,
            duration_seconds=5.0,
            error_message=error,
            started_at=datetime.now(UTC),
        )
        test_db_session.add(fetch_log)
        await test_db_session.commit()
        await test_db_session.refresh(fetch_log)
        scenario_context["fetch_log"] = fetch_log

    run_async(_log())


@when(parsers.parse("a fetch is logged with duration {duration:f} seconds"))
def log_fetch_with_duration(
    test_db_session: AsyncSession,
    duration: float,
    scenario_context: dict[str, Any],
) -> None:
    """Log a fetch with specific duration."""
    dataset = scenario_context.get("dataset")
    if not dataset:
        raise ValueError("No dataset in context.")

    async def _log():
        fetch_log = FetchLog(
            dataset_code=dataset.code,
            source=dataset.source,
            status="success",
            records_fetched=100,
            duration_seconds=duration,
            started_at=datetime.now(UTC),
        )
        test_db_session.add(fetch_log)
        await test_db_session.commit()
        await test_db_session.refresh(fetch_log)
        scenario_context["fetch_log"] = fetch_log

    run_async(_log())


# ==============================================================================
# Then Steps - Storage Assertions
# ==============================================================================


@then("the data values should be persisted in the database")
def data_values_persisted(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
) -> None:
    """Assert data values were persisted."""
    dataset = scenario_context.get("dataset")

    async def _check():
        result = await test_db_session.execute(
            select(DataValue).where(DataValue.dataset_id == dataset.id)
        )
        values = result.scalars().all()
        assert len(values) > 0, "No data values found in database"

    run_async(_check())


@then("the data values should include geo, time, and indicator dimensions")
def data_values_have_dimensions(scenario_context: dict[str, Any]) -> None:
    """Assert data values have required dimensions."""
    values = scenario_context.get("stored_values", [])
    assert len(values) > 0, "No stored values in context"

    for value in values:
        assert value.geo is not None, "Data value missing geo dimension"
        assert value.time_period is not None, "Data value missing time dimension"
        assert value.indicator is not None, "Data value missing indicator dimension"


@then("the dataset metadata should be persisted")
def metadata_persisted(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
) -> None:
    """Assert dataset metadata was persisted."""
    dataset = scenario_context.get("dataset")

    async def _check():
        result = await test_db_session.execute(
            select(DatasetMetadata).where(DatasetMetadata.dataset_id == dataset.id)
        )
        metadata = result.scalar_one_or_none()
        assert metadata is not None, "Dataset metadata not found"
        scenario_context["metadata"] = metadata

    run_async(_check())


@then("the metadata should include last updated timestamp")
def metadata_has_timestamp(scenario_context: dict[str, Any]) -> None:
    """Assert metadata has last updated timestamp (stored as JSON in value field)."""
    metadata = scenario_context.get("metadata")
    assert metadata is not None, "No metadata in context"
    assert metadata.key == "last_updated", "Expected 'last_updated' metadata key"
    # Parse JSON value to verify timestamp
    value_data = json.loads(metadata.value)
    assert "timestamp" in value_data, "Metadata value missing timestamp"


@then("a fetch log should be recorded")
def fetch_log_recorded(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
) -> None:
    """Assert a fetch log was recorded."""
    dataset = scenario_context.get("dataset")

    async def _check():
        result = await test_db_session.execute(
            select(FetchLog).where(
                FetchLog.dataset_code == dataset.code,
                FetchLog.source == dataset.source,
            )
        )
        logs = result.scalars().all()
        assert len(logs) > 0, "No fetch logs found"
        scenario_context["fetch_log"] = logs[-1]

    run_async(_check())


@then(parsers.parse('the fetch log status should be "{status}"'))
def fetch_log_status(scenario_context: dict[str, Any], status: str) -> None:
    """Assert fetch log has expected status."""
    fetch_log = scenario_context.get("fetch_log")
    assert fetch_log is not None, "No fetch log in context"
    assert fetch_log.status == status, f"Expected status {status}, got {fetch_log.status}"


@then("the fetch log should include records count")
def fetch_log_has_records_count(scenario_context: dict[str, Any]) -> None:
    """Assert fetch log has records count."""
    fetch_log = scenario_context.get("fetch_log")
    assert fetch_log is not None, "No fetch log in context"
    assert fetch_log.records_fetched is not None, "Fetch log missing records_fetched"
    assert fetch_log.records_fetched >= 0, "records_fetched should be non-negative"


@then(parsers.parse('the fetch log error message should be "{error}"'))
def fetch_log_error_message(scenario_context: dict[str, Any], error: str) -> None:
    """Assert fetch log has expected error message."""
    fetch_log = scenario_context.get("fetch_log")
    assert fetch_log is not None, "No fetch log in context"
    assert fetch_log.error_message == error, (
        f"Expected error '{error}', got '{fetch_log.error_message}'"
    )


@then(parsers.parse("the fetch log should record duration {duration:f} seconds"))
def fetch_log_duration(scenario_context: dict[str, Any], duration: float) -> None:
    """Assert fetch log has expected duration."""
    fetch_log = scenario_context.get("fetch_log")
    assert fetch_log is not None, "No fetch log in context"
    assert abs(fetch_log.duration_seconds - duration) < 0.01, (
        f"Expected duration {duration}, got {fetch_log.duration_seconds}"
    )
