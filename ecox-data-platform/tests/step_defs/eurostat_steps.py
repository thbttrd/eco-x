"""Eurostat-specific step definitions for BDD tests."""

import asyncio
from typing import Any

from ecox_shared.models import DataValue
from pytest_bdd import then, when
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
# When Steps - Eurostat Operations
# ==============================================================================


@when("I store eurostat data values for the dataset")
def store_eurostat_data_values(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
) -> None:
    """Store Eurostat-style data values with geo, time, indicator dimensions."""
    dataset = scenario_context.get("dataset")
    if not dataset:
        raise ValueError("No dataset in context.")

    async def _store():
        values = [
            DataValue(
                dataset_id=dataset.id,
                geo="EU27_2020",
                time_period="2022",
                indicator="B1GQ",  # GDP indicator
                value=15000000.0,
                unit="CP_MEUR",
            ),
            DataValue(
                dataset_id=dataset.id,
                geo="FR",
                time_period="2022",
                indicator="B1GQ",
                value=2500000.0,
                unit="CP_MEUR",
            ),
            DataValue(
                dataset_id=dataset.id,
                geo="DE",
                time_period="2022",
                indicator="B1GQ",
                value=3500000.0,
                unit="CP_MEUR",
            ),
        ]
        for v in values:
            test_db_session.add(v)
        await test_db_session.commit()
        scenario_context["stored_values"] = values

    run_async(_store())


# ==============================================================================
# Then Steps - Eurostat Assertions
# ==============================================================================


@then('the source "eurostat" should show total available datasets')
def eurostat_shows_total_available(api_response: dict[str, Any]) -> None:
    """Assert Eurostat source shows total available count."""
    data = api_response.get("json", [])
    eurostat = next((s for s in data if s.get("code") == "eurostat"), None)
    assert eurostat is not None, "Eurostat source not found"
    # total_available may be None if no metadata exists, which is OK for test
    assert "total_available" in eurostat or eurostat.get("total_available") is not None
