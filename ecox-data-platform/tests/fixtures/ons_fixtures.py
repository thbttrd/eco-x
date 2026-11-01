"""ONS-specific test fixtures.

This module contains sample data structures that mirror the ONS API responses
for use in unit and integration tests.
"""

import pytest

# ==============================================================================
# Sample ONS API Responses
# ==============================================================================


@pytest.fixture
def sample_ons_datasets_response() -> dict:
    """Sample ONS /datasets API response with multiple datasets."""
    return {
        "items": [
            {
                "id": "trade",
                "title": "UK Trade",
                "description": "UK trade data with imports and exports",
                "keywords": ["trade", "exports", "imports"],
                "national_statistic": True,
                "release_frequency": "Monthly",
                "unit_of_measure": "GBP millions",
                "last_updated": "2024-01-15T10:00:00Z",
            },
            {
                "id": "regional-gdp-by-year",
                "title": "Regional GDP by year",
                "description": "Gross domestic product by region annually",
                "keywords": ["gdp", "regional", "economy"],
                "national_statistic": True,
                "release_frequency": "Annual",
                "unit_of_measure": "GBP millions",
                "last_updated": "2024-01-10T10:00:00Z",
            },
            {
                "id": "employment-by-industry",
                "title": "Employment by Industry",
                "description": "Employment statistics by industry sector",
                "keywords": ["employment", "jobs", "industry"],
                "national_statistic": False,
                "release_frequency": "Quarterly",
                "unit_of_measure": "Thousands",
                "last_updated": "2024-01-12T10:00:00Z",
            },
        ],
        "count": 3,
        "offset": 0,
        "limit": 100,
        "total_count": 3,
    }


@pytest.fixture
def sample_ons_editions_response() -> dict:
    """Sample ONS /datasets/{id}/editions API response."""
    return {
        "items": [
            {
                "edition": "time-series",
                "id": "time-series",
                "links": {
                    "latest_version": {
                        "href": "/datasets/trade/editions/time-series/versions/1",
                        "id": "1",
                    }
                },
                "state": "published",
            }
        ],
        "count": 1,
        "offset": 0,
        "limit": 100,
        "total_count": 1,
    }


@pytest.fixture
def sample_ons_version_response() -> dict:
    """Sample ONS dataset version metadata with dimensions."""
    return {
        "id": "1",
        "edition": "time-series",
        "version": 1,
        "dimensions": [
            {"name": "geography", "label": "Geography", "description": "Geographic region"},
            {"name": "time", "label": "Time", "description": "Time period"},
            {"name": "tradetype", "label": "Trade Type", "description": "Type of trade"},
        ],
        "downloads": {
            "csv": {"href": "/datasets/trade/downloads/csv", "size": "1024"},
            "xlsx": {"href": "/datasets/trade/downloads/xlsx", "size": "2048"},
        },
        "last_updated": "2024-01-15T10:00:00Z",
        "release_date": "2024-01-15",
        "state": "published",
        "unit_of_measure": "GBP millions",
    }


@pytest.fixture
def sample_ons_observations_response() -> dict:
    """Sample ONS observations API response with UK trade data."""
    return {
        "observations": [
            {
                "observation": "12345.6",
                "dimensions": {
                    "geography": {"id": "K02000001", "label": "United Kingdom"},
                    "time": {"id": "2023-Q1", "label": "2023 Q1"},
                    "tradetype": {"id": "total", "label": "Total Trade"},
                },
            },
            {
                "observation": "13456.7",
                "dimensions": {
                    "geography": {"id": "K02000001", "label": "United Kingdom"},
                    "time": {"id": "2023-Q2", "label": "2023 Q2"},
                    "tradetype": {"id": "total", "label": "Total Trade"},
                },
            },
            {
                "observation": "14567.8",
                "dimensions": {
                    "geography": {"id": "K02000001", "label": "United Kingdom"},
                    "time": {"id": "2023-Q3", "label": "2023 Q3"},
                    "tradetype": {"id": "total", "label": "Total Trade"},
                },
            },
            {
                "observation": "15678.9",
                "dimensions": {
                    "geography": {"id": "K02000001", "label": "United Kingdom"},
                    "time": {"id": "2023-Q4", "label": "2023 Q4"},
                    "tradetype": {"id": "total", "label": "Total Trade"},
                },
            },
        ],
        "dimensions": {
            "geography": {"option": {"id": "K02000001", "label": "United Kingdom"}},
            "tradetype": {"option": {"id": "total", "label": "Total Trade"}},
        },
        "total_observations": 4,
        "unit_of_measure": "GBP millions",
    }


# ==============================================================================
# Sample Observations for Transform Tests
# ==============================================================================


@pytest.fixture
def ons_observations_basic() -> list[dict]:
    """Basic ONS observations with geography and time dimensions."""
    return [
        {
            "observation": "12345.6",
            "dimensions": {
                "geography": {"id": "K02000001", "label": "United Kingdom"},
                "time": {"id": "2023-Q1", "label": "2023 Q1"},
            },
        },
        {
            "observation": "13456.7",
            "dimensions": {
                "geography": {"id": "K02000001", "label": "United Kingdom"},
                "time": {"id": "2023-Q2", "label": "2023 Q2"},
            },
        },
    ]


@pytest.fixture
def ons_observations_with_extra_dimensions() -> list[dict]:
    """ONS observations with additional non-time/geo dimensions."""
    return [
        {
            "observation": "100.0",
            "dimensions": {
                "geography": {"id": "K02000001", "label": "United Kingdom"},
                "time": {"id": "2023", "label": "2023"},
                "industry": {"id": "A", "label": "Agriculture"},
            },
        },
        {
            "observation": "200.0",
            "dimensions": {
                "geography": {"id": "K02000001", "label": "United Kingdom"},
                "time": {"id": "2023", "label": "2023"},
                "industry": {"id": "B", "label": "Mining"},
            },
        },
    ]


@pytest.fixture
def ons_observations_with_invalid_values() -> list[dict]:
    """ONS observations with some invalid values that should be skipped."""
    return [
        {
            "observation": "12345.6",
            "dimensions": {"time": {"id": "2023"}},
        },
        {
            "observation": None,  # Invalid - null value
            "dimensions": {"time": {"id": "2024"}},
        },
        {
            "observation": "not_a_number",  # Invalid - non-numeric
            "dimensions": {"time": {"id": "2025"}},
        },
        {
            "observation": "",  # Invalid - empty string
            "dimensions": {"time": {"id": "2026"}},
        },
        {
            "observation": "98765.4",  # Valid
            "dimensions": {"time": {"id": "2027"}},
        },
    ]


@pytest.fixture
def ons_observations_capital_time_key() -> list[dict]:
    """ONS observations using capital 'Time' instead of lowercase."""
    return [
        {
            "observation": "100.0",
            "dimensions": {
                "Time": {"id": "2023", "label": "2023"},
                "geography": {"id": "UK"},
            },
        },
    ]


@pytest.fixture
def ons_observations_label_only_time() -> list[dict]:
    """ONS observations with only label (no id) for time dimension."""
    return [
        {
            "observation": "100.0",
            "dimensions": {
                "time": {"label": "2023 Q1"},  # No id, only label
                "geography": {"id": "UK"},
            },
        },
    ]


@pytest.fixture
def ons_observations_no_geography() -> list[dict]:
    """ONS observations without geography dimension."""
    return [
        {
            "observation": "100.0",
            "dimensions": {
                "time": {"id": "2023"},
            },
        },
    ]


# ==============================================================================
# Sample Raw Data with Fixed Dimensions
# ==============================================================================


@pytest.fixture
def ons_raw_data_with_fixed_dimensions() -> dict:
    """Sample raw API response with fixed (non-varying) dimensions."""
    return {
        "dimensions": {
            "geography": {"option": {"id": "K02000001", "label": "United Kingdom"}},
            "sector": {"option": {"id": "total", "label": "Total"}},
        }
    }


@pytest.fixture
def ons_raw_data_empty_dimensions() -> dict:
    """Sample raw API response with no fixed dimensions."""
    return {"dimensions": {}}


# ==============================================================================
# Sample Metadata
# ==============================================================================


@pytest.fixture
def ons_metadata_with_unit() -> dict:
    """ONS metadata with unit of measure."""
    return {"unit_of_measure": "GBP millions"}


@pytest.fixture
def ons_metadata_empty() -> dict:
    """Empty ONS metadata."""
    return {}


# ==============================================================================
# Pagination Test Data
# ==============================================================================


@pytest.fixture
def ons_paginated_datasets_page1() -> dict:
    """First page of paginated ONS datasets (100 items, 150 total)."""
    return {
        "items": [{"id": f"ds{i}", "title": f"Dataset {i}"} for i in range(100)],
        "count": 100,
        "offset": 0,
        "limit": 100,
        "total_count": 150,
    }


@pytest.fixture
def ons_paginated_datasets_page2() -> dict:
    """Second page of paginated ONS datasets (50 items, 150 total)."""
    return {
        "items": [{"id": f"ds{i}", "title": f"Dataset {i}"} for i in range(100, 150)],
        "count": 50,
        "offset": 100,
        "limit": 100,
        "total_count": 150,
    }


@pytest.fixture
def ons_empty_response() -> dict:
    """Empty ONS API response."""
    return {
        "items": [],
        "count": 0,
        "offset": 0,
        "limit": 100,
        "total_count": 0,
    }


# ==============================================================================
# Dimension Options Test Data
# ==============================================================================


@pytest.fixture
def ons_dimension_options_with_negative() -> dict:
    """ONS dimension options with negative values (like -8 "Does not apply").

    Negative values are metadata codes that cause 500 errors when used in
    observation queries and should be skipped.
    """
    return {
        "items": [
            {
                "label": "Does not apply",
                "dimension": "sexual_orientation_9a",
                "option": "-8",
            },
            {
                "label": "Not stated",
                "dimension": "sexual_orientation_9a",
                "option": "-7",
            },
            {
                "label": "Straight or Heterosexual",
                "dimension": "sexual_orientation_9a",
                "option": "1",
            },
            {
                "label": "Gay or Lesbian",
                "dimension": "sexual_orientation_9a",
                "option": "2",
            },
        ],
        "count": 4,
        "offset": 0,
        "limit": 20,
        "total_count": 4,
    }


@pytest.fixture
def ons_dimension_options_all_negative() -> dict:
    """ONS dimension options with only negative values (edge case)."""
    return {
        "items": [
            {"dimension": "some_dim", "option": "-8", "label": "Does not apply"},
            {"dimension": "some_dim", "option": "-7", "label": "Not stated"},
        ],
        "count": 2,
        "offset": 0,
        "limit": 20,
        "total_count": 2,
    }


@pytest.fixture
def ons_dimension_options_non_numeric() -> dict:
    """ONS dimension options with non-numeric values (geography codes)."""
    return {
        "items": [
            {"dimension": "geography", "option": "K02000001", "label": "United Kingdom"},
            {"dimension": "geography", "option": "E92000001", "label": "England"},
            {"dimension": "geography", "option": "W92000004", "label": "Wales"},
        ],
        "count": 3,
        "offset": 0,
        "limit": 20,
        "total_count": 3,
    }
