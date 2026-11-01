"""Source-related step definitions for BDD tests."""

import asyncio
from typing import Any

from ecox_shared.models import SourceMetadata
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
        import nest_asyncio

        nest_asyncio.apply()
        return asyncio.get_event_loop().run_until_complete(coro)
    else:
        return asyncio.get_event_loop().run_until_complete(coro)


# ==============================================================================
# Given Steps - Source Setup
# ==============================================================================


@given(parsers.parse('source "{source}" has {total:d} total available datasets'))
def source_has_total_available(
    test_db_session: AsyncSession,
    source: str,
    total: int,
) -> None:
    """Set up source metadata with total available count."""

    async def _create():
        metadata = SourceMetadata(
            source=source,
            total_datasets=total,
            api_base_url=f"https://api.{source}.example.com",
            documentation_url=f"https://docs.{source}.example.com",
        )
        test_db_session.add(metadata)
        await test_db_session.commit()

    run_async(_create())


@given(parsers.parse('source "{source}" is active'))
def source_is_active(
    test_db_session: AsyncSession,
    source: str,
) -> None:
    """Ensure source is marked as active."""
    # Sources are active by default, but we could add SourceActivation model here
    pass


# ==============================================================================
# Then Steps - Source Assertions
# ==============================================================================


@then(parsers.parse('the source "{source}" should show {downloaded:d} of {available:d} datasets'))
def source_shows_counts(
    api_response: dict[str, Any],
    source: str,
    downloaded: int,
    available: int,
) -> None:
    """Assert source shows correct downloaded/available counts."""
    data = api_response.get("json", [])
    if isinstance(data, list):
        source_data = next((s for s in data if s.get("code") == source), None)
    else:
        source_data = data if data.get("code") == source else None

    assert source_data is not None, f"Source {source} not found"
    assert source_data.get("dataset_count") == downloaded, (
        f"Expected {downloaded} downloaded, got {source_data.get('dataset_count')}"
    )
    assert source_data.get("total_available") == available, (
        f"Expected {available} available, got {source_data.get('total_available')}"
    )


@then(parsers.parse('the source "{source}" should be in the response'))
def source_in_response(api_response: dict[str, Any], source: str) -> None:
    """Assert a specific source is in the response."""
    data = api_response.get("json", [])
    if isinstance(data, dict) and "sources" in data:
        data = data["sources"]

    codes = [s.get("code") for s in data if isinstance(s, dict)]
    assert source in codes, f"Source {source} not found in response. Found: {codes}"


@then(parsers.parse("there should be {count:d} sources in the response"))
def source_count_in_response(api_response: dict[str, Any], count: int) -> None:
    """Assert the number of sources in the response."""
    data = api_response.get("json", [])
    if isinstance(data, dict) and "sources" in data:
        data = data["sources"]

    assert len(data) == count, f"Expected {count} sources, got {len(data)}"
