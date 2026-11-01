"""Common step definitions for ecox-client BDD tests."""

from typing import Any

from pytest_bdd import given, parsers, then

# ==============================================================================
# Given Steps - Common Setup
# ==============================================================================


@given("the client app is running")
def client_app_running(scenario_context: dict[str, Any]) -> None:
    """Mark that the client app is running (setup in fixtures)."""
    scenario_context["app_running"] = True


# ==============================================================================
# Then Steps - Response Assertions
# ==============================================================================


@then("the response should be HTML")
def response_is_html(scenario_context: dict[str, Any]) -> None:
    """Assert response is HTML content."""
    response = scenario_context.get("response")
    assert response is not None, "No response in context"
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type, f"Expected HTML, got {content_type}"


@then(parsers.parse('the response should contain "{text}"'))
def response_contains_text(scenario_context: dict[str, Any], text: str) -> None:
    """Assert response body contains text."""
    response = scenario_context.get("response")
    assert response is not None, "No response in context"
    assert text in response.text, f"Expected '{text}' in response"


@then(parsers.parse('the response should not contain "{text}"'))
def response_not_contains_text(scenario_context: dict[str, Any], text: str) -> None:
    """Assert response body does not contain text."""
    response = scenario_context.get("response")
    assert response is not None, "No response in context"
    assert text not in response.text, f"Did not expect '{text}' in response"


@then(parsers.parse("the response status should be {status:d}"))
def response_status_is(scenario_context: dict[str, Any], status: int) -> None:
    """Assert response status code."""
    response = scenario_context.get("response")
    assert response is not None, "No response in context"
    assert response.status_code == status, f"Expected status {status}, got {response.status_code}"
