"""FRED-specific step definitions for BDD tests."""

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
# When Steps - FRED Operations
# ==============================================================================


@when("I store fred data values for the dataset")
def store_fred_data_values(
    test_db_session: AsyncSession,
    scenario_context: dict[str, Any],
) -> None:
    """Store FRED-style data values (time series observations)."""
    dataset = scenario_context.get("dataset")
    if not dataset:
        raise ValueError("No dataset in context.")

    async def _store():
        # FRED data has dates and values (simpler than Eurostat)
        values = [
            DataValue(
                dataset_id=dataset.id,
                geo="US",  # FRED is US data
                time_period="2022-01-01",
                indicator=dataset.code,
                value=25000.0,
                unit="Billions of Dollars",
            ),
            DataValue(
                dataset_id=dataset.id,
                geo="US",
                time_period="2022-04-01",
                indicator=dataset.code,
                value=25500.0,
                unit="Billions of Dollars",
            ),
            DataValue(
                dataset_id=dataset.id,
                geo="US",
                time_period="2022-07-01",
                indicator=dataset.code,
                value=26000.0,
                unit="Billions of Dollars",
            ),
        ]
        for v in values:
            test_db_session.add(v)
        await test_db_session.commit()
        scenario_context["stored_values"] = values

    run_async(_store())


# ==============================================================================
# Then Steps - FRED Assertions
# ==============================================================================


@then("the data values should include time and value")
def data_values_have_time_and_value(scenario_context: dict[str, Any]) -> None:
    """Assert data values have time_period and value fields."""
    values = scenario_context.get("stored_values", [])
    assert len(values) > 0, "No stored values in context"

    for value in values:
        assert value.time_period is not None, "Data value missing time_period"
        assert value.value is not None, "Data value missing value"
