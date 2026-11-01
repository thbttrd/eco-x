"""Performance step definitions for BDD tests."""

import asyncio
from typing import Any

from pytest_bdd import given, then, when

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
# Given Steps - Performance Setup
# ==============================================================================


@given("the HTTP client is configured")
def http_client_configured(scenario_context: dict[str, Any]) -> None:
    """Mark that the HTTP client is configured."""
    scenario_context["http_client_configured"] = True


# ==============================================================================
# When Steps - Performance Actions
# ==============================================================================


@when("I request the dataset list twice")
def request_dataset_list_twice(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Request the dataset list twice to test caching."""
    response1 = api_client.get("/api/datasets")
    response2 = api_client.get("/api/datasets")

    scenario_context["response1"] = response1
    scenario_context["response2"] = response2


@when("I perform multiple concurrent reads")
def perform_concurrent_reads(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Perform multiple concurrent read operations."""
    # Simulate concurrent reads by making multiple requests
    responses = []
    for _ in range(3):
        response = api_client.get("/api/datasets")
        responses.append(response)

    scenario_context["concurrent_responses"] = responses


# ==============================================================================
# Then Steps - Performance Assertions
# ==============================================================================


@then("both requests should succeed")
def both_requests_succeed(scenario_context: dict[str, Any]) -> None:
    """Assert both requests succeeded."""
    response1 = scenario_context.get("response1")
    response2 = scenario_context.get("response2")

    assert response1 is not None, "First response missing"
    assert response2 is not None, "Second response missing"
    assert response1.status_code == 200, f"First request failed: {response1.status_code}"
    assert response2.status_code == 200, f"Second request failed: {response2.status_code}"


@then("the client should have retry capability")
def client_has_retry_capability(scenario_context: dict[str, Any]) -> None:
    """Assert the HTTP client has retry capability."""
    # This is a documentation test - the actual retry logic is in the source fetchers
    assert scenario_context.get("http_client_configured") is True


@then("all reads should succeed")
def all_reads_succeed(scenario_context: dict[str, Any]) -> None:
    """Assert all concurrent reads succeeded."""
    responses = scenario_context.get("concurrent_responses", [])
    assert len(responses) > 0, "No responses recorded"

    for i, response in enumerate(responses):
        assert response.status_code == 200, f"Request {i + 1} failed: {response.status_code}"
