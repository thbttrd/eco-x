"""Common step definitions shared across all BDD tests.

These steps handle database setup, API response handling, and general assertions.
"""

from typing import Any

from pytest_bdd import given, parsers, then
from sqlmodel.ext.asyncio.session import AsyncSession

# ==============================================================================
# Database Steps
# ==============================================================================


@given("the database is initialized")
def database_initialized(test_db_session: AsyncSession) -> None:
    """Ensure database session is available (provided by conftest fixture)."""
    assert test_db_session is not None


@given("the database is empty")
def database_empty(test_db_session: AsyncSession) -> None:
    """Ensure database has no data (fresh in-memory DB per test).

    In-memory SQLite is fresh per test, so this is a no-op
    but explicit for documentation purposes.
    """
    pass


# ==============================================================================
# Response Assertion Steps
# ==============================================================================


@then(parsers.parse("the response status should be {status:d}"))
def check_response_status(api_response: dict[str, Any], status: int) -> None:
    """Assert the HTTP response status code."""
    assert api_response.get("status_code") == status, (
        f"Expected status {status}, got {api_response.get('status_code')}"
    )


@then("the response should be successful")
def response_successful(api_response: dict[str, Any]) -> None:
    """Assert response has 2xx status code."""
    status = api_response.get("status_code", 0)
    assert 200 <= status < 300, f"Expected 2xx status, got {status}"


@then(parsers.parse('the response should contain "{text}"'))
def response_contains_text(api_response: dict[str, Any], text: str) -> None:
    """Assert response contains specific text."""
    response_text = api_response.get("text", "")
    if not response_text:
        response_text = str(api_response.get("json", {}))
    assert text in response_text, f"'{text}' not found in response"


@then(parsers.parse("the response should have {count:d} items"))
def response_item_count(api_response: dict[str, Any], count: int) -> None:
    """Assert response contains expected number of items."""
    data = api_response.get("json", [])
    if isinstance(data, dict):
        if "items" in data:
            data = data["items"]
        elif "datasets" in data:
            data = data["datasets"]
        elif "sources" in data:
            data = data["sources"]
    assert len(data) == count, f"Expected {count} items, got {len(data)}"


@then("the response should be empty")
def response_empty(api_response: dict[str, Any]) -> None:
    """Assert response contains no items."""
    data = api_response.get("json", [])
    if isinstance(data, dict):
        if "items" in data:
            data = data["items"]
        elif "datasets" in data:
            data = data["datasets"]
    assert len(data) == 0, f"Expected empty response, got {len(data)} items"
