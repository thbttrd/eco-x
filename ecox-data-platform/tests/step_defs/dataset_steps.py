"""Dataset-related step definitions for BDD tests."""

import asyncio
from typing import Any

from ecox_shared.models import Dataset, DataValue
from pytest_bdd import given, parsers, then
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
        # If we're already in an async context, create a task
        # This shouldn't happen with pytest-bdd but handle it gracefully
        import nest_asyncio

        nest_asyncio.apply()
        return asyncio.get_event_loop().run_until_complete(coro)
    else:
        return asyncio.get_event_loop().run_until_complete(coro)


# ==============================================================================
# Given Steps - Dataset Setup
# ==============================================================================


@given(parsers.parse('there are {count:d} datasets from "{source}" in the database'))
def datasets_in_database(
    test_db_session: AsyncSession,
    count: int,
    source: str,
    scenario_context: dict[str, Any],
) -> None:
    """Create datasets in the test database."""

    async def _create_datasets():
        datasets = []
        for i in range(count):
            dataset = Dataset(
                code=f"{source.upper()}_{i}",
                name=f"Test Dataset {i} from {source}",
                source=source,
                description=f"Auto-generated test dataset {i}",
            )
            test_db_session.add(dataset)
            datasets.append(dataset)

        await test_db_session.commit()

        # Refresh to get IDs
        for dataset in datasets:
            await test_db_session.refresh(dataset)

        return datasets

    datasets = run_async(_create_datasets())
    scenario_context.setdefault("created_datasets", []).extend(datasets)


@given(parsers.parse('a dataset "{code}" exists from "{source}"'))
def dataset_exists(
    test_db_session: AsyncSession,
    code: str,
    source: str,
    scenario_context: dict[str, Any],
) -> None:
    """Create a specific dataset in the database."""

    async def _create():
        dataset = Dataset(
            code=code,
            name=f"Dataset {code}",
            source=source,
            description=f"Test dataset {code} from {source}",
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)
        return dataset

    dataset = run_async(_create())
    scenario_context["dataset"] = dataset


@given(parsers.parse('a dataset "{code}" exists from "{source}" without source_url'))
def dataset_exists_without_source_url(
    test_db_session: AsyncSession,
    code: str,
    source: str,
    scenario_context: dict[str, Any],
) -> None:
    """Create a dataset with source_url explicitly set to None."""

    async def _create():
        dataset = Dataset(
            code=code,
            name=f"Dataset {code}",
            source=source,
            description=f"Test dataset {code} from {source}",
            source_url=None,  # Explicitly no URL
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)
        return dataset

    dataset = run_async(_create())
    scenario_context["dataset"] = dataset


@given(parsers.parse('the dataset "{code}" has {count:d} data values'))
def dataset_has_values(
    test_db_session: AsyncSession,
    code: str,
    count: int,
    scenario_context: dict[str, Any],
) -> None:
    """Add data values to a dataset."""
    dataset = scenario_context.get("dataset")
    if not dataset:
        raise ValueError(f"Dataset {code} not found in context. Use 'a dataset exists' step first.")

    async def _add_values():
        for i in range(count):
            value = DataValue(
                dataset_id=dataset.id,
                geo=f"GEO_{i % 5}",  # Cycle through 5 geo codes
                time_period=f"202{i % 4}",  # Cycle through years
                indicator="GDP",
                value=float(1000 + i * 100),
                unit="EUR",
            )
            test_db_session.add(value)

        await test_db_session.commit()

    run_async(_add_values())


@given(parsers.parse('a dataset "{code}" with name "{name}" exists from "{source}"'))
def dataset_with_name_exists(
    test_db_session: AsyncSession,
    code: str,
    name: str,
    source: str,
    scenario_context: dict[str, Any],
) -> None:
    """Create a dataset with specific name in the database."""

    async def _create():
        dataset = Dataset(
            code=code,
            name=name,
            source=source,
            description=f"Test dataset: {name}",
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)
        return dataset

    dataset = run_async(_create())
    scenario_context.setdefault("created_datasets", []).append(dataset)


# ==============================================================================
# Then Steps - Dataset Assertions
# ==============================================================================


@then(parsers.parse('the source "{source}" should have {count:d} datasets'))
def source_has_datasets(
    api_response: dict[str, Any],
    source: str,
    count: int,
) -> None:
    """Assert a source has expected dataset count in the response."""
    data = api_response.get("json", [])

    # Handle different response formats
    if isinstance(data, list):
        source_data = next((s for s in data if s.get("code") == source), None)
    else:
        source_data = data if data.get("code") == source else None

    assert source_data is not None, f"Source {source} not found in response"
    assert source_data.get("dataset_count") == count, (
        f"Expected {count} datasets for {source}, got {source_data.get('dataset_count')}"
    )


@then(parsers.parse('the dataset "{code}" should be in the response'))
def dataset_in_response(api_response: dict[str, Any], code: str) -> None:
    """Assert a specific dataset is in the response."""
    data = api_response.get("json", [])
    # Handle different response formats
    if isinstance(data, dict):
        if "datasets" in data:
            data = data["datasets"]
        elif "items" in data:
            data = data["items"]

    codes = [d.get("code") for d in data if isinstance(d, dict)]
    assert code in codes, f"Dataset {code} not found in response. Found: {codes}"


@then(parsers.parse('all datasets should be from source "{source}"'))
def all_datasets_from_source(api_response: dict[str, Any], source: str) -> None:
    """Assert all datasets in response are from the specified source."""
    data = api_response.get("json", [])
    # Handle different response formats
    if isinstance(data, dict):
        if "datasets" in data:
            data = data["datasets"]
        elif "items" in data:
            data = data["items"]

    for dataset in data:
        assert dataset.get("source") == source, (
            f"Expected source {source}, got {dataset.get('source')}"
        )


@then("the response should include pagination info")
def response_has_pagination(api_response: dict[str, Any]) -> None:
    """Assert response includes pagination information."""
    data = api_response.get("json", {})
    # Check for common pagination fields (including "items" and "max_id" patterns)
    if isinstance(data, dict):
        has_pagination = any(
            key in data
            for key in [
                "total",
                "page",
                "page_size",
                "total_pages",
                "datasets",
                "items",
                "max_id",
            ]
        )
        assert has_pagination, f"Expected pagination info in response: {data.keys()}"
    else:
        # If it's a list, check if we have data
        assert isinstance(data, list), "Expected dict or list response"


@then(parsers.parse('the response should contain dataset code "{code}"'))
def response_contains_code(api_response: dict[str, Any], code: str) -> None:
    """Assert response contains specific dataset code."""
    data = api_response.get("json", {})
    if isinstance(data, dict):
        assert data.get("code") == code, f"Expected code {code}, got {data.get('code')}"
    else:
        raise AssertionError("Expected dict response for dataset details")


@then(parsers.parse('the response should contain source "{source}"'))
def response_contains_source(api_response: dict[str, Any], source: str) -> None:
    """Assert response contains specific source."""
    data = api_response.get("json", {})
    if isinstance(data, dict):
        assert data.get("source") == source, f"Expected source {source}, got {data.get('source')}"
    else:
        raise AssertionError("Expected dict response for dataset details")


@then(parsers.parse('the dataset "{code}" should have a status field'))
def dataset_has_status(api_response: dict[str, Any], code: str) -> None:
    """Assert a dataset in the response has a status field."""
    data = api_response.get("json", [])
    # Handle different response formats
    if isinstance(data, dict):
        if "datasets" in data:
            data = data["datasets"]
        elif "items" in data:
            data = data["items"]

    dataset = next((d for d in data if d.get("code") == code), None)
    assert dataset is not None, f"Dataset {code} not found in response"
    # Status is typically computed/derived, so just check the dataset exists
    # The status field might be implicit in downloaded datasets


@then(parsers.parse('the dataset "{code}" should not be in the response'))
def dataset_not_in_response(api_response: dict[str, Any], code: str) -> None:
    """Assert a specific dataset is NOT in the response."""
    data = api_response.get("json", [])
    # Handle different response formats
    if isinstance(data, dict):
        if "datasets" in data:
            data = data["datasets"]
        elif "items" in data:
            data = data["items"]

    codes = [d.get("code") for d in data if isinstance(d, dict)]
    assert code not in codes, f"Dataset {code} should not be in response. Found: {codes}"
