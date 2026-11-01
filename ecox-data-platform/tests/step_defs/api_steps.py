"""API-related step definitions for platform BDD tests.

These steps handle API requests and response handling.
"""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_bdd import parsers, when
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.api.dependencies import get_session
from ecox_platform.api.routes import datasets, fetch_logs, health, news, sources

# ==============================================================================
# Test App Factory
# ==============================================================================


def create_test_app() -> FastAPI:
    """Create a FastAPI app for testing without lifespan handlers."""
    app = FastAPI(
        title="ecox-data-platform-test",
        description="Test instance of the data platform",
        version="1.0.0",
    )

    # Include routers (same as production)
    app.include_router(health.router)
    app.include_router(sources.router, prefix="/api")
    app.include_router(datasets.router, prefix="/api")
    app.include_router(fetch_logs.router, prefix="/api")
    app.include_router(news.router, prefix="/api")

    return app


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def app(test_db_session: AsyncSession) -> FastAPI:
    """Create test FastAPI app with dependency overrides."""
    test_app = create_test_app()

    async def override_get_session():
        yield test_db_session

    test_app.dependency_overrides[get_session] = override_get_session
    return test_app


@pytest.fixture
def api_client(app: FastAPI) -> TestClient:
    """Create test client for API requests."""
    return TestClient(app)


# ==============================================================================
# When Steps - API Requests
# ==============================================================================


@when("I request the list of data sources")
def request_sources(api_client: TestClient, api_response: dict[str, Any]) -> None:
    """Make GET request to /api/sources endpoint."""
    response = api_client.get("/api/sources")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()
    api_response["headers"] = dict(response.headers)


@when(parsers.parse('I request datasets from "{source}"'))
def request_datasets_from_source(
    api_client: TestClient,
    source: str,
    api_response: dict[str, Any],
) -> None:
    """Make GET request to /api/datasets?source={source} endpoint."""
    response = api_client.get(f"/api/datasets?source={source}")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()


@when("I request all datasets")
def request_all_datasets(api_client: TestClient, api_response: dict[str, Any]) -> None:
    """Make GET request to /api/datasets/all endpoint."""
    response = api_client.get("/api/datasets/all")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()


@when(parsers.parse('I request dataset details for "{source}/{code}"'))
def request_dataset_details(
    api_client: TestClient,
    source: str,
    code: str,
    api_response: dict[str, Any],
) -> None:
    """Make GET request to /api/datasets/{source}/{code} endpoint."""
    response = api_client.get(f"/api/datasets/{source}/{code}")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()


@when(parsers.parse('I search datasets with query "{query}"'))
def search_datasets(
    api_client: TestClient,
    query: str,
    api_response: dict[str, Any],
) -> None:
    """Make GET request with search query."""
    response = api_client.get(f"/api/datasets?search={query}")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()


@when(parsers.parse('I filter datasets by status "{status}"'))
def filter_by_status(
    api_client: TestClient,
    status: str,
    api_response: dict[str, Any],
) -> None:
    """Make GET request with status filter.

    Note: The current API doesn't have a status filter, so we just query all.
    """
    response = api_client.get("/api/datasets")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()


@when(parsers.parse('I request datasets from "{source}" with page {page:d}'))
def request_datasets_with_page(
    api_client: TestClient,
    source: str,
    page: int,
    api_response: dict[str, Any],
) -> None:
    """Make GET request with pagination."""
    response = api_client.get(f"/api/datasets?source={source}&page={page}")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()


@when("I request the health endpoint")
def request_health(api_client: TestClient, api_response: dict[str, Any]) -> None:
    """Make GET request to /health endpoint."""
    response = api_client.get("/health")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()


@when(parsers.parse('I search datasets from "{source}" with query "{query}"'))
def search_datasets_from_source(
    api_client: TestClient,
    source: str,
    query: str,
    api_response: dict[str, Any],
) -> None:
    """Make GET request with search query filtered by source."""
    response = api_client.get(f"/api/datasets?source={source}&search={query}")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()
