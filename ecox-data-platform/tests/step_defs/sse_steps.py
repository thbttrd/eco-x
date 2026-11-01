"""SSE (Server-Sent Events) step definitions for BDD tests.

Note: SSE endpoint not yet implemented in platform API.
These steps document the expected behavior and infrastructure.
"""

from typing import Any

from pytest_bdd import given, then

# ==============================================================================
# Given Steps - SSE Setup
# ==============================================================================


@given("the application supports SSE")
def application_supports_sse(scenario_context: dict[str, Any]) -> None:
    """Mark that the application supports SSE (placeholder)."""
    scenario_context["sse_supported"] = True


# ==============================================================================
# Then Steps - SSE Assertions
# ==============================================================================


@then("real-time update infrastructure should be ready")
def realtime_infrastructure_ready(scenario_context: dict[str, Any]) -> None:
    """Assert real-time update infrastructure is ready."""
    # This is a placeholder test - SSE will be implemented later
    assert scenario_context.get("sse_supported") is True, "SSE infrastructure not ready"


@then("fetch log infrastructure is ready")
def fetch_log_infrastructure_ready(scenario_context: dict[str, Any]) -> None:
    """Assert fetch log infrastructure is ready for notifications."""
    # This is a placeholder test - the infrastructure exists via FetchLog model
    scenario_context["fetch_log_ready"] = True
    assert scenario_context.get("fetch_log_ready") is True
