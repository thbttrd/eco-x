"""UI step definitions for ecox-client BDD tests."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

from pytest_bdd import given, parsers, when

# ==============================================================================
# Given Steps - Platform Mock Setup
# ==============================================================================


@given("the platform returns no sources")
def platform_returns_no_sources(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure platform client to return no sources."""
    mock_platform_client.list_sources.return_value = []
    scenario_context["sources_configured"] = True


@given("the platform returns sources with datasets")
def platform_returns_sources_with_datasets(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure platform client to return sources with dataset counts."""
    mock_platform_client.list_sources.return_value = [
        {
            "code": "eurostat",
            "name": "Eurostat",
            "dataset_count": 10,
            "total_available": 100,
            "last_activity": None,
        },
        {
            "code": "fred",
            "name": "FRED",
            "dataset_count": 5,
            "total_available": 50,
            "last_activity": None,
        },
    ]
    scenario_context["sources_configured"] = True


@given("the platform returns multiple sources")
def platform_returns_multiple_sources(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure platform client to return multiple sources including ONS."""
    mock_platform_client.list_sources.return_value = [
        {
            "code": "eurostat",
            "name": "Eurostat",
            "dataset_count": 10,
            "total_available": 100,
            "last_activity": None,
        },
        {
            "code": "fred",
            "name": "FRED",
            "dataset_count": 5,
            "total_available": 50,
            "last_activity": None,
        },
        {
            "code": "ons",
            "name": "ONS",
            "dataset_count": 3,
            "total_available": 30,
            "last_activity": None,
        },
    ]
    scenario_context["sources_configured"] = True


@given("the platform returns sources with last activity")
def platform_returns_sources_with_activity(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure platform client to return sources with last activity timestamps."""
    mock_platform_client.list_sources.return_value = [
        {
            "code": "eurostat",
            "name": "Eurostat",
            "dataset_count": 10,
            "total_available": 100,
            "last_activity": datetime.now().isoformat(),
        },
    ]
    scenario_context["sources_configured"] = True


@given("the platform returns datasets")
def platform_returns_datasets(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure platform client to return datasets."""
    mock_platform_client.list_datasets.return_value = {
        "items": [
            {
                "id": 1,
                "code": "nama_10_gdp",
                "name": "GDP and main components",
                "source": "eurostat",
                "last_fetched": datetime.now().isoformat(),
            },
            {
                "id": 2,
                "code": "GDP",
                "name": "Gross Domestic Product",
                "source": "fred",
                "last_fetched": datetime.now().isoformat(),
            },
        ],
        "total": 2,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }
    mock_platform_client.list_sources.return_value = [
        {"code": "eurostat", "name": "Eurostat"},
        {"code": "fred", "name": "FRED"},
    ]
    scenario_context["datasets_configured"] = True


@given("the platform returns no datasets")
def platform_returns_no_datasets(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure platform client to return no datasets."""
    mock_platform_client.list_datasets.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
        "total_pages": 0,
    }
    mock_platform_client.list_sources.return_value = []
    scenario_context["datasets_configured"] = True


@given("the platform returns a dataset detail")
def platform_returns_dataset_detail(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure platform client to return dataset details."""
    mock_platform_client.get_dataset.return_value = {
        "id": 1,
        "code": "nama_10_gdp",
        "name": "GDP and main components",
        "source": "eurostat",
        "description": "Gross domestic product data",
        "last_fetched": datetime.now().isoformat(),
    }
    mock_platform_client.list_fetch_logs.return_value = {
        "items": [
            {
                "started_at": datetime.now().isoformat(),
                "status": "success",
                "records_fetched": 100,
            }
        ]
    }
    scenario_context["dataset_detail_configured"] = True


@given("the platform returns a dataset detail with source_url")
def platform_returns_dataset_detail_with_source_url(
    scenario_context: dict[str, Any],
    mock_platform_client: AsyncMock,
) -> None:
    """Configure platform client to return dataset details with source_url."""
    mock_platform_client.get_dataset.return_value = {
        "id": 1,
        "code": "nama_10_gdp",
        "name": "GDP and main components",
        "source": "eurostat",
        "description": "Gross domestic product data",
        "last_fetched": datetime.now().isoformat(),
        "source_url": "https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table",
    }
    mock_platform_client.list_fetch_logs.return_value = {
        "items": [
            {
                "started_at": datetime.now().isoformat(),
                "status": "success",
                "records_fetched": 100,
            }
        ]
    }
    scenario_context["dataset_detail_configured"] = True


@given(parsers.parse('the source "{source}" is deactivated'))
def source_is_deactivated(
    scenario_context: dict[str, Any],
    mock_db_manager: Any,
    source: str,
) -> None:
    """Mark a source as deactivated in the database."""
    import asyncio

    from ecox_client.models import SourceActivation

    async def _deactivate():
        async with mock_db_manager.get_session() as session:
            activation = SourceActivation(
                source_code=source,
                activated=False,
                updated_at=datetime.now(),
            )
            session.add(activation)
            await session.commit()

    # Use asyncio.run() for Python 3.10+ compatibility
    asyncio.run(_deactivate())

    scenario_context["deactivated_sources"] = scenario_context.get("deactivated_sources", [])
    scenario_context["deactivated_sources"].append(source)


# ==============================================================================
# When Steps - UI Requests
# ==============================================================================


@when("I request the sources grid")
def request_sources_grid(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Request the sources grid HTML fragment."""
    response = api_client.get("/api/sources")
    scenario_context["response"] = response


@when("I request the datasets table")
def request_datasets_table(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Request the datasets table HTML fragment."""
    source = scenario_context.get("current_source", "all")
    response = api_client.get(f"/api/datasets/{source}")
    scenario_context["response"] = response


@when("I request the datasets page")
def request_datasets_page(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Request the main page with datasets tab active."""
    response = api_client.get("/?tab=datasets")
    scenario_context["response"] = response


@when(parsers.parse('I request datasets for source "{source}"'))
def request_datasets_for_source(
    scenario_context: dict[str, Any],
    api_client: Any,
    source: str,
) -> None:
    """Request datasets for a specific source."""
    scenario_context["current_source"] = source
    response = api_client.get(f"/api/datasets/{source}")
    scenario_context["response"] = response


@when(parsers.parse('I search datasets with query "{query}"'))
def search_datasets(
    scenario_context: dict[str, Any],
    api_client: Any,
    query: str,
) -> None:
    """Search datasets with a query string."""
    source = scenario_context.get("current_source", "all")
    response = api_client.get(f"/api/datasets/{source}?search={query}")
    scenario_context["response"] = response


@when(parsers.parse('I request dataset detail for "{source}/{code}"'))
def request_dataset_detail(
    scenario_context: dict[str, Any],
    api_client: Any,
    source: str,
    code: str,
) -> None:
    """Request dataset detail modal."""
    response = api_client.get(f"/api/datasets/{source}/{code}")
    scenario_context["response"] = response


@when("I request the news list")
def request_news_list(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Request the news list HTML fragment."""
    response = api_client.get("/api/news")
    scenario_context["response"] = response


@when("I request the catalog modal")
def request_catalog_modal(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Request the catalog modal HTML fragment."""
    response = api_client.get("/api/catalog/sources")
    scenario_context["response"] = response
