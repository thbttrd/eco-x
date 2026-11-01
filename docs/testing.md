# Testing Guide

*Last updated: 2025-12-16*

This document describes the testing strategy and conventions used in the eco-x project.

## Overview

The project uses a **hybrid testing approach**:
- **BDD (Behavior-Driven Development)** for acceptance tests using pytest-bdd
- **Unit tests** for isolated component testing (where applicable)

All tests are written in Python using pytest and its extensions.

## Test Structure

Each package has its own test directory:

```
ecox-data-platform/tests/
├── bdd/                    # BDD test modules (bind feature files)
│   ├── __init__.py
│   ├── test_epic01.py
│   ├── test_epic02.py
│   └── ...
├── features/               # Gherkin feature files
│   ├── epic01_data_source_browsing.feature
│   ├── epic02_dataset_discovery.feature
│   └── ...
├── step_defs/             # Step definition modules
│   ├── __init__.py
│   ├── api_steps.py
│   ├── common_steps.py
│   ├── dataset_steps.py
│   └── ...
└── conftest.py            # Shared fixtures

ecox-client/tests/
├── bdd/
├── features/
├── step_defs/
└── conftest.py

ecox-shared/tests/
├── bdd/
├── features/
├── step_defs/
└── conftest.py
```

## Running Tests

### Run All Tests

```bash
# From project root
cd ecox-data-platform && uv run pytest tests/bdd/
cd ecox-client && uv run pytest tests/bdd/
cd ecox-shared && uv run pytest tests/bdd/
```

### Run Tests by Epic

```bash
# Run all tests for Epic 1 (Data Source Browsing)
uv run pytest -m "epic_1"

# Run all tests for Epic 2 (Dataset Discovery)
uv run pytest -m "epic_2"
```

### Run Tests by Type

```bash
# API tests only
uv run pytest -m "api"

# UI tests only
uv run pytest -m "ui"
```

### Verbose Output

```bash
# With Gherkin scenario names
uv run pytest tests/bdd/ -v

# With full Gherkin output
uv run pytest tests/bdd/ --gherkin-terminal-reporter -v
```

## Test Organization

### Epic Mapping

| Epic | Description | Package | Feature Files |
|------|-------------|---------|---------------|
| 1 | Data Source Browsing | platform, client | `epic01_*.feature` |
| 2 | Dataset Discovery | platform, client | `epic02_*.feature` |
| 3 | Real-Time Updates | platform | `epic03_*.feature` |
| 4 | Auto Refresh | platform | `epic04_*.feature` |
| 5 | News Aggregation | client | `epic05_*.feature` |
| 6 | Eurostat Fetching | platform | `epic06_*.feature` |
| 7 | FRED Fetching | platform | `epic07_*.feature` |
| 8 | Application Information | client | `epic08_*.feature` |
| 9 | Storage & History | platform | `epic09_*.feature` |
| 10 | Source Management | platform | `epic10_*.feature` |
| 11 | Internationalization | client | `epic11_*.feature` |
| 12 | Performance | platform | `epic12_*.feature` |
| 13 | Migrations & Factories | shared | `epic13_*.feature` |

### Tag Conventions

Feature files use tags for filtering:

- `@epic_N` - Epic number (e.g., `@epic_1`, `@epic_2`)
- `@us-N.M` - User story reference (e.g., `@us-1.1`, `@us-2.3`)
- `@api` - API/backend tests
- `@ui` - UI/frontend tests
- `@wip` - Work in progress
- `@slow` - Long-running tests

### Example Feature File

```gherkin
@epic_1 @api
Feature: Data Source Browsing
  As a user
  I want to browse available data sources
  So that I can discover what economic data is available

  Background:
    Given the database is initialized

  @us-1.1
  Scenario: List all available data sources with no data
    Given the database is empty
    When I request the list of data sources
    Then the response status should be 200
    And the response should be empty

  @us-1.2
  Scenario: List data sources with downloaded datasets
    Given the database is empty
    And a dataset "nama_10_gdp" exists from "eurostat"
    When I request the list of data sources
    Then the response status should be 200
    And the response should have 1 items
```

## Writing Tests

### Step Definition Pattern

```python
# tests/step_defs/api_steps.py
from pytest_bdd import given, when, then, parsers

@when("I request the list of data sources")
def request_sources(api_client, api_response):
    response = api_client.get("/api/sources")
    api_response["status_code"] = response.status_code
    api_response["json"] = response.json()

@then(parsers.parse("the response status should be {status:d}"))
def check_status(api_response, status):
    assert api_response.get("status_code") == status
```

### Test Binding Pattern

```python
# tests/bdd/test_epic01.py
from pytest_bdd import scenarios

# Import step definitions (wildcard imports required)
from tests.step_defs.api_steps import *  # noqa: F401, F403
from tests.step_defs.common_steps import *  # noqa: F401, F403

# Bind all scenarios from the feature file
scenarios("../features/epic01_data_source_browsing.feature")
```

### Key Fixtures

**scenario_context** - Mutable dict for passing data between steps:
```python
@pytest.fixture
def scenario_context() -> dict:
    return {}
```

**api_response** - Store HTTP response for assertions:
```python
@pytest.fixture
def api_response() -> dict:
    return {}  # Contains: status_code, json, text, headers
```

**test_db_session** - Async database session:
```python
@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    # In-memory SQLite with all tables created
    ...
```

**api_client** - FastAPI TestClient:
```python
@pytest.fixture
def api_client(app: FastAPI) -> TestClient:
    return TestClient(app)
```

## Test Coverage

Current test coverage:

| Package | Tests | Coverage |
|---------|-------|----------|
| ecox-data-platform | 45 | ~31% |
| ecox-client | 17 | ~62% |
| ecox-shared | 6 | ~29% |
| **Total** | **68** | - |

## Troubleshooting

### Step Definition Not Found

If you see `StepDefinitionNotFoundError`:

1. Check that the step text matches exactly
2. For parameterized steps, use `parsers.parse()`:
   ```python
   # Wrong
   @given('a dataset "{code}" exists from "{source}"')

   # Correct
   @given(parsers.parse('a dataset "{code}" exists from "{source}"'))
   ```

3. Ensure step definitions are imported in the test file:
   ```python
   from tests.step_defs.api_steps import *  # noqa: F401, F403
   ```

### Async Step Issues

For async step definitions, use the test database session:
```python
async def add_dataset(test_db_session, scenario_context, code, source):
    dataset = Dataset(code=code, source=source)
    test_db_session.add(dataset)
    await test_db_session.commit()
```

### Database Table Not Found

If tests fail with "no such table", ensure:
1. Models are imported in conftest.py to register with SQLModel metadata
2. Tables are created before the test session

```python
# In conftest.py
from ecox_shared.models import Dataset, DataValue  # Register models

async with engine.begin() as conn:
    await conn.run_sync(SQLModel.metadata.create_all)
```

## CI/CD Integration

Tests run automatically on:
- Pull requests
- Push to main branch

Failed tests block merging to main.
