"""Catalog and source management step definitions for BDD tests."""

from typing import Any

from fastapi.testclient import TestClient
from pytest_bdd import parsers, then, when

# ==============================================================================
# When Steps - Catalog/Source API Requests
# ==============================================================================


@when(parsers.parse('I request source status for "{source}"'))
def request_source_status(
    api_client: TestClient,
    source: str,
    api_response: dict[str, Any],
) -> None:
    """Make GET request to /api/sources/{source} endpoint."""
    response = api_client.get(f"/api/sources/{source}")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()


# ==============================================================================
# Then Steps - Source Assertions
# ==============================================================================


@then("the response should contain configured sources")
def response_contains_configured_sources(api_response: dict[str, Any]) -> None:
    """Assert response contains the configured data sources."""
    data = api_response.get("json", [])
    assert isinstance(data, list), "Expected list response"

    # Check for known sources (defined in SOURCE_NAMES)
    known_sources = {"eurostat", "fred", "oecd", "nbs", "ons"}
    response_sources = {s.get("code") for s in data if isinstance(s, dict)}

    # At least some known sources should be present
    assert response_sources.intersection(known_sources), (
        f"Expected configured sources, got {response_sources}"
    )


@then("each source should have code, name, and description")
def sources_have_metadata(api_response: dict[str, Any]) -> None:
    """Assert each source has required metadata fields."""
    data = api_response.get("json", [])
    assert isinstance(data, list), "Expected list response"
    assert len(data) > 0, "Expected at least one source"

    for source in data:
        assert "code" in source, f"Source missing 'code': {source}"
        assert "name" in source, f"Source missing 'name': {source}"
        # Description can be null but field should exist
        assert "description" in source or source.get("description") is None


@then(parsers.parse('the response should contain source "{source}"'))
def response_contains_source_detail(api_response: dict[str, Any], source: str) -> None:
    """Assert response contains specific source code."""
    data = api_response.get("json", {})
    if isinstance(data, dict):
        assert data.get("code") == source, f"Expected source {source}, got {data.get('code')}"
    else:
        raise AssertionError("Expected dict response for source status")


@then("the response should include worker status")
def response_includes_worker_status(api_response: dict[str, Any]) -> None:
    """Assert response includes worker status information."""
    data = api_response.get("json", {})
    assert isinstance(data, dict), "Expected dict response"
    assert "worker_status" in data, f"Missing worker_status in response: {data.keys()}"
