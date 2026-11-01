"""Auto-refresh step definitions for BDD tests."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from ecox_shared.models import Dataset
from pytest_bdd import given, parsers, then, when
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.config import Settings, SourceConfig

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
# Given Steps - Configuration Setup
# ==============================================================================


@given(parsers.parse('a source configuration for "{source}"'))
def source_config_for(scenario_context: dict[str, Any], source: str) -> None:
    """Get source configuration."""
    settings = Settings()
    config = settings.get_source_config(source)
    scenario_context["source_config"] = config
    scenario_context["source"] = source


@given(parsers.parse('a source configuration for "{source}" with refresh_hours {hours:d}'))
def source_config_with_refresh_hours(
    scenario_context: dict[str, Any],
    source: str,
    hours: int,
) -> None:
    """Create source configuration with specific refresh_hours."""
    config = SourceConfig(refresh_hours=hours)
    scenario_context[f"{source}_config"] = config


@given(parsers.parse('a source configuration for "{source}" with enabled {enabled}'))
def source_config_with_enabled(
    scenario_context: dict[str, Any],
    source: str,
    enabled: str,
) -> None:
    """Create source configuration with specific enabled state."""
    is_enabled = enabled.lower() == "true"
    config = SourceConfig(enabled=is_enabled)
    scenario_context[f"{source}_config"] = config


@given(
    parsers.parse('a dataset "{code}" from "{source}" exists with last_fetched {hours:d} hours ago')
)
def dataset_exists_with_last_fetched(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
    code: str,
    source: str,
    hours: int,
) -> None:
    """Create a dataset with a specific last_fetched time."""
    last_fetched = datetime.now() - timedelta(hours=hours)

    async def _create():
        dataset = Dataset(
            code=code,
            name=f"Test {code}",
            source=source,
            last_fetched=last_fetched,
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)
        scenario_context["dataset"] = dataset

    run_async(_create())


# ==============================================================================
# When Steps - Refresh Checks
# ==============================================================================


@when(parsers.parse("I check if the dataset needs refresh with max_age {hours:d} hours"))
def check_dataset_needs_refresh(
    scenario_context: dict[str, Any],
    hours: int,
) -> None:
    """Check if dataset needs refresh based on max_age."""
    dataset = scenario_context.get("dataset")
    if not dataset:
        raise ValueError("No dataset in context")

    max_age = timedelta(hours=hours)
    now = datetime.now()

    if dataset.last_fetched is None:
        # Never fetched - needs refresh
        scenario_context["needs_refresh"] = True
    else:
        age = now - dataset.last_fetched
        scenario_context["needs_refresh"] = age > max_age


# ==============================================================================
# Then Steps - Configuration Assertions
# ==============================================================================


@then("the source config should have a refresh_hours setting")
def config_has_refresh_hours(scenario_context: dict[str, Any]) -> None:
    """Assert source config has refresh_hours."""
    config = scenario_context.get("source_config")
    assert config is not None, "No source_config in context"
    assert hasattr(config, "refresh_hours"), "Config missing refresh_hours"
    assert config.refresh_hours > 0, "refresh_hours should be positive"


@then("the source config should have an enabled setting")
def config_has_enabled(scenario_context: dict[str, Any]) -> None:
    """Assert source config has enabled."""
    config = scenario_context.get("source_config")
    assert config is not None, "No source_config in context"
    assert hasattr(config, "enabled"), "Config missing enabled"
    assert isinstance(config.enabled, bool), "enabled should be boolean"


@then("the source config should have a rate_limit setting")
def config_has_rate_limit(scenario_context: dict[str, Any]) -> None:
    """Assert source config has rate_limit."""
    config = scenario_context.get("source_config")
    assert config is not None, "No source_config in context"
    assert hasattr(config, "rate_limit"), "Config missing rate_limit"
    assert config.rate_limit > 0, "rate_limit should be positive"


@then(parsers.parse("the eurostat refresh interval should be {hours:d} hours"))
def eurostat_refresh_interval(scenario_context: dict[str, Any], hours: int) -> None:
    """Assert eurostat refresh interval."""
    config = scenario_context.get("eurostat_config")
    assert config is not None, "No eurostat_config in context"
    assert config.refresh_hours == hours, f"Expected {hours}, got {config.refresh_hours}"


@then(parsers.parse("the fred refresh interval should be {hours:d} hours"))
def fred_refresh_interval(scenario_context: dict[str, Any], hours: int) -> None:
    """Assert fred refresh interval."""
    config = scenario_context.get("fred_config")
    assert config is not None, "No fred_config in context"
    assert config.refresh_hours == hours, f"Expected {hours}, got {config.refresh_hours}"


@then("the eurostat source should be disabled")
def eurostat_source_disabled(scenario_context: dict[str, Any]) -> None:
    """Assert eurostat source is disabled."""
    config = scenario_context.get("eurostat_config")
    assert config is not None, "No eurostat_config in context"
    assert config.enabled is False, "eurostat should be disabled"


# ==============================================================================
# Then Steps - Freshness Assertions
# ==============================================================================


@then("the dataset should be marked as stale")
def dataset_is_stale(scenario_context: dict[str, Any]) -> None:
    """Assert dataset needs refresh."""
    needs_refresh = scenario_context.get("needs_refresh")
    assert needs_refresh is True, "Dataset should be marked as stale"


@then("the dataset should be marked as fresh")
def dataset_is_fresh(scenario_context: dict[str, Any]) -> None:
    """Assert dataset does not need refresh."""
    needs_refresh = scenario_context.get("needs_refresh")
    assert needs_refresh is False, "Dataset should be marked as fresh"


# ==============================================================================
# US-4.3: Smart Refresh Using Source Metadata
# ==============================================================================


@given(
    parsers.parse(
        'a dataset "{code}" from "{source}" exists with source_last_update "{last_update}"'
    )
)
def dataset_exists_with_source_last_update(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
    code: str,
    source: str,
    last_update: str,
) -> None:
    """Create a dataset with a specific source_last_update value."""

    async def _create():
        dataset = Dataset(
            code=code,
            name=f"Test {code}",
            source=source,
            source_last_update=last_update,
            last_fetched=datetime.now() - timedelta(hours=1),  # Recently fetched
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)
        scenario_context.setdefault("datasets", {})[code] = dataset

    run_async(_create())


@given(parsers.parse('the TOC metadata shows last_update "{last_update}" for dataset "{code}"'))
def toc_metadata_last_update(
    scenario_context: dict[str, Any],
    last_update: str,
    code: str,
) -> None:
    """Set TOC metadata for a dataset."""
    toc_metadata = scenario_context.setdefault("toc_metadata", {})
    toc_metadata[code] = {"code": code, "last_update": last_update}


@given(
    parsers.parse('the TOC metadata shows a new dataset "{code}" with last_update "{last_update}"')
)
def toc_metadata_new_dataset(
    scenario_context: dict[str, Any],
    code: str,
    last_update: str,
) -> None:
    """Add a new dataset to TOC metadata (not in database)."""
    toc_metadata = scenario_context.setdefault("toc_metadata", {})
    toc_metadata[code] = {"code": code, "last_update": last_update, "is_new": True}


@when(parsers.parse('the smart refresh check runs for "{source}"'))
def smart_refresh_check_runs(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
    source: str,
) -> None:
    """Run smart refresh check comparing TOC metadata with stored datasets."""
    toc_metadata = scenario_context.get("toc_metadata", {})
    datasets = scenario_context.get("datasets", {})

    # Initialize result tracking
    new_datasets: list[str] = []
    stale_datasets: list[str] = []
    unchanged_datasets: list[str] = []
    fetch_queue: list[str] = []

    for code, toc_entry in toc_metadata.items():
        source_last_update = toc_entry.get("last_update")

        if toc_entry.get("is_new") or code not in datasets:
            # New dataset - never fetched
            new_datasets.append(code)
            fetch_queue.append(code)  # New datasets first
        else:
            # Existing dataset - compare source_last_update
            existing = datasets.get(code)
            if existing and existing.source_last_update != source_last_update:
                # Source has been updated
                stale_datasets.append(code)
            else:
                # Source unchanged - skip
                unchanged_datasets.append(code)

    # Stale datasets come after new datasets in the queue
    fetch_queue.extend(stale_datasets)

    scenario_context["smart_refresh_results"] = {
        "new": new_datasets,
        "stale": stale_datasets,
        "unchanged": unchanged_datasets,
        "fetch_queue": fetch_queue,
    }


@then(parsers.parse('the dataset "{code}" should be marked as unchanged'))
def dataset_marked_unchanged(scenario_context: dict[str, Any], code: str) -> None:
    """Assert dataset is marked as unchanged (source hasn't updated)."""
    results = scenario_context.get("smart_refresh_results", {})
    unchanged = results.get("unchanged", [])
    assert code in unchanged, f"Dataset {code} should be unchanged, got results: {results}"


@then(parsers.parse('the dataset "{code}" should be marked as stale'))
def dataset_marked_stale(scenario_context: dict[str, Any], code: str) -> None:
    """Assert dataset is marked as stale (source has updated)."""
    results = scenario_context.get("smart_refresh_results", {})
    stale = results.get("stale", [])
    assert code in stale, f"Dataset {code} should be stale, got results: {results}"


@then(parsers.parse('the dataset "{code}" should not be queued for fetch'))
def dataset_not_queued(scenario_context: dict[str, Any], code: str) -> None:
    """Assert dataset is not in the fetch queue."""
    results = scenario_context.get("smart_refresh_results", {})
    fetch_queue = results.get("fetch_queue", [])
    assert code not in fetch_queue, f"Dataset {code} should not be queued, got queue: {fetch_queue}"


@then(parsers.parse('the dataset "{code}" should be queued for fetch'))
def dataset_queued(scenario_context: dict[str, Any], code: str) -> None:
    """Assert dataset is in the fetch queue."""
    results = scenario_context.get("smart_refresh_results", {})
    fetch_queue = results.get("fetch_queue", [])
    assert code in fetch_queue, f"Dataset {code} should be queued, got queue: {fetch_queue}"


@then(parsers.parse('the dataset "{first}" should be queued before "{second}"'))
def dataset_queued_before(scenario_context: dict[str, Any], first: str, second: str) -> None:
    """Assert first dataset is queued before second dataset (priority)."""
    results = scenario_context.get("smart_refresh_results", {})
    fetch_queue = results.get("fetch_queue", [])

    assert first in fetch_queue, f"Dataset {first} should be in queue"
    assert second in fetch_queue, f"Dataset {second} should be in queue"

    first_idx = fetch_queue.index(first)
    second_idx = fetch_queue.index(second)
    assert first_idx < second_idx, (
        f"Dataset {first} (idx={first_idx}) should come before {second} (idx={second_idx})"
    )
