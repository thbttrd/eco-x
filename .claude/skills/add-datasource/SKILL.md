---
name: add-datasource
description: Add a new data source with complete implementation (API discovery to full integration)
allowed-tools: WebFetch, Bash(curl*), Read, Write, Edit, Grep, Glob, Task
user-invocable: true
---

You are tasked with adding a new data source to the eco-x project. This command ensures **complete implementation** with no missing integration points.

## Arguments

The user should provide: `$ARGUMENTS` (URL of the data source or API documentation)

## Phase 1: API Discovery & Documentation

### 1.1 Fetch API Documentation

If a documentation URL was provided, fetch and analyze it using **WebFetch** or **curl**:

```bash
# Use curl to test API endpoints
curl -s "https://api.example.com/docs" | head -200
```

Or use the WebFetch tool to fetch and analyze web documentation pages.

Extract and document:
- [ ] **Base URL** for the API
- [ ] **Authentication** requirements (API key, OAuth, none)
- [ ] **Available endpoints** (list datasets, get data, get metadata)
- [ ] **Request format** (query params, path params)
- [ ] **Response format** (JSON structure, pagination)
- [ ] **Rate limits** or usage guidelines
- [ ] **Data format** (time series, dimensions, attributes)

### 1.2 Explore the API (if documentation is incomplete)

Use curl to explore API endpoints and discover the structure:

```bash
# Test common API patterns
curl -s "https://api.example.com/datasets" | head -100
curl -s "https://api.example.com/v1/data" | head -100
curl -s "https://api.example.com/api/catalog" | head -100
```

Use WebFetch to read API documentation pages and extract endpoint information.

### 1.3 Test API Endpoints

Verify the API works:

```bash
# Test list datasets endpoint
curl -s "https://api.example.com/datasets" | head -100

# Test get single dataset
curl -s "https://api.example.com/data/SAMPLE_CODE" | head -100

# Test metadata endpoint
curl -s "https://api.example.com/metadata/SAMPLE_CODE" | head -100
```

### 1.4 Create API Summary

Write a summary document with all findings before proceeding.

---

## Phase 1.5: Requirements Validation

After completing API discovery, validate that the data source API meets platform requirements. This early validation prevents wasted effort on incompatible APIs.

### 1.5.1 Requirements Checklist

Based on your Phase 1 findings, evaluate each requirement below. Mark with:
- **[Y]** = Yes, API provides this
- **[P]** = Partial, possible with workaround (explain in notes)
- **[N]** = No, not available

#### CRITICAL Requirements (All Required)

These capabilities are **mandatory**. If any critical requirement is missing without a viable workaround, show a **prominent warning** before proceeding.

| # | Capability | Status | API Evidence | Notes |
|---|------------|--------|--------------|-------|
| C1 | **Dataset Listing (TOC)** | [ ] | | Endpoint that returns available datasets. Without this, users cannot discover data. |
| C2 | **Data Fetching** | [ ] | | Endpoint to fetch actual observations/values for a dataset. Core functionality. |
| C3 | **Time Series Data** | [ ] | | Response includes time dimension (dates, periods, years). Maps to `time_period`. |
| C4 | **Numeric Values** | [ ] | | Response includes numeric observation values. Maps to `value` (float). |

**Critical Workarounds:**
```
C1 = [N]: Workaround: Hardcode dataset list in config/datasets.yaml (acceptable for <50 datasets)
C2 = [N]: NO WORKAROUND - Cannot proceed without data fetching capability
C3 = [N]: NO WORKAROUND - Platform requires time series data
C4 = [N]: NO WORKAROUND - Platform requires numeric values
```

#### IMPORTANT Requirements (Strongly Recommended)

Missing these will degrade functionality. Document workarounds if marking [P] or [N].

| # | Capability | Status | API Evidence | Notes |
|---|------------|--------|--------------|-------|
| I1 | **Dataset Metadata** | [ ] | | Endpoint for dataset name, description, dimensions. |
| I2 | **Geographic Dimension** | [ ] | | Data includes geographic codes (e.g., 'US', 'EU27', 'FR'). |
| I3 | **Indicator Dimension** | [ ] | | Data identifies what is measured (e.g., 'GDP', 'CPI'). |
| I4 | **Unit Information** | [ ] | | Unit of measurement in response (e.g., 'EUR', 'PC'). |

**Important Workarounds:**
```
I1 = [N]: Use dataset code as name, leave description null (poor UX)
I2 = [N]: Use default value like 'TOTAL' or source country code (e.g., 'US' for FRED)
I3 = [N]: Use dataset_code as indicator (reduced granularity)
I4 = [N]: Leave unit as null (users won't know units)
```

#### OPTIONAL Requirements (Nice-to-Have)

These enhance functionality but are not required.

| # | Capability | Status | API Evidence | Notes |
|---|------------|--------|--------------|-------|
| O1 | **Dataset Search** | [ ] | | Search endpoint for keywords (used in UI search). |
| O2 | **Pagination** | [ ] | | For large dataset listings. Prevents memory issues. |
| O3 | **Last Updated Metadata** | [ ] | | Enables smart refresh optimization (skip unchanged datasets). |
| O4 | **Filter Parameters** | [ ] | | Filter by geo, time, unit in requests. Reduces data transfer. |
| O5 | **Quality Flags** | [ ] | | Data quality markers (estimated, provisional). Maps to `flags`. |
| O6 | **Category/Hierarchy** | [ ] | | Dataset categorization for organized browsing. |

**Optional Impact Notes:**
```
O1 = [N]: Implement client-side search over cached TOC (slower for large catalogs)
O2 = [N]: May timeout for sources with >10,000 datasets
O3 = [N]: Will always re-fetch data, no smart refresh optimization
O4 = [N]: Must fetch all data, filter client-side
O5 = [N]: Leave flags as null
O6 = [N]: Flat listing in UI
```

### 1.5.2 Data Mapping Verification

Verify how API response fields map to platform data model:

| Platform Field | Type | API Field | Transformation Needed |
|----------------|------|-----------|----------------------|
| `DataValue.geo` | string | | |
| `DataValue.time_period` | string | | |
| `DataValue.indicator` | string | | |
| `DataValue.value` | float | | |
| `DataValue.unit` | string? | | |
| `DataValue.flags` | string? | | |
| `Dataset.name` | string | | |
| `Dataset.description` | string? | | |
| `Dataset.source_last_update` | datetime? | | |

**Example transformation (FRED):**
```python
DataValue(
    geo="US",  # FRED is US-only, hardcoded
    time_period=obs["date"],  # "2024-01-01" -> "2024-01-01"
    indicator=series_id,  # "GDP" from request
    value=float(obs["value"]),  # "1234.5" -> 1234.5
    unit=series_info["units"],  # From series metadata
    flags=None,  # FRED doesn't provide flags
)
```

### 1.5.3 Compatibility Score

Calculate compatibility score based on requirements met:

| Category | Scoring | Your Score |
|----------|---------|------------|
| Critical (C1-C4) | 20 points each | ___ / 80 |
| Important (I1-I4) | 3 points each | ___ / 12 |
| Optional (O1-O6) | 1 point each (max 8) | ___ / 8 |
| **TOTAL** | | **___ / 100** |

**Score Interpretation:**
- **80-100**: Excellent - Proceed with full implementation
- **60-79**: Good - Proceed with documented limitations
- **40-59**: Limited - Significant workarounds needed, discuss with user
- **< 40**: Poor - Fundamental gaps, recommend NOT proceeding

### 1.5.4 Validation Summary

Document your findings before proceeding:

```markdown
## Requirements Validation Summary

**Source:** {source_name}
**API Documentation:** {url}
**Validation Date:** {date}
**Compatibility Score:** {score}/100

### Critical Requirements
- C1 Dataset Listing: {Y/P/N} - {brief note}
- C2 Data Fetching: {Y/P/N} - {brief note}
- C3 Time Series: {Y/P/N} - {brief note}
- C4 Numeric Values: {Y/P/N} - {brief note}

### Warnings
{List any [N] critical/important requirements and their impact}

### Workarounds Required
{List any [P] requirements and their workarounds}

### Implementation Notes
- Geographic handling: {how geo will be derived}
- Indicator handling: {how indicator will be derived}
- Smart refresh: {enabled/disabled based on O3}

### Recommendation
{PROCEED / PROCEED WITH LIMITATIONS / NOT RECOMMENDED}
```

### 1.5.5 Decision Gate

**Before proceeding to Phase 2, get explicit confirmation:**

Present the validation summary to the user with:
1. Compatibility score and interpretation
2. Any critical/important gaps with warnings
3. Required workarounds
4. Recommendation

**User Confirmation:**
```
Based on requirements validation, this data source has a compatibility score of {score}/100.

Warnings: {list critical/important gaps or "None"}
Workarounds needed: {list or "None"}
Recommendation: {PROCEED / PROCEED WITH LIMITATIONS / NOT RECOMMENDED}

Do you want to proceed with implementation? [Y/N]
```

**Note:** User can choose to proceed despite warnings. This is a flexible approach that trusts user judgment while ensuring they're fully informed of risks.

---

## Phase 2: Architecture Review

### 2.1 Understand Existing Patterns

Review similar implementations for reference:

```
Read these files to understand the patterns:
- ecox-data-platform/src/ecox_platform/sources/eurostat/repository.py (SDMX/JSON-stat pattern)
- ecox-data-platform/src/ecox_platform/sources/fred/repository.py (simple REST pattern)
- ecox-data-platform/src/ecox_platform/sources/base/repository.py (required interface)
- ecox-data-platform/src/ecox_platform/sources/base/service.py (service pattern)
```

### 2.2 Plan the Implementation

Create a detailed plan covering ALL integration points:

**Core Module** (`ecox-data-platform/src/ecox_platform/sources/{source}/`):
- [ ] `__init__.py` - Exports
- [ ] `models.py` - Pydantic models for API responses
- [ ] `repository.py` - API interaction (extends BaseRepository)
- [ ] `service.py` - Business logic (extends BaseService)

**Configuration**:
- [ ] `config/catalog.yaml` - Source registration
- [ ] `config/datasets.yaml` - Auto-fetch datasets
- [ ] `ecox-data-platform/src/ecox_platform/config.py` - Settings (API key, base URL)

**Integration Points** (CRITICAL - often missed):
- [ ] `ecox-data-platform/src/ecox_platform/scheduler/` - Add to source worker
- [ ] `ecox-data-platform/src/ecox_platform/api/routes/datasets.py` - Add to route handlers

**Tests**:
- [ ] `ecox-data-platform/tests/unit/test_{source}_repository.py`
- [ ] `ecox-data-platform/tests/bdd/` - BDD feature and step definitions

---

## Phase 3: Implementation

### 3.1 Create Core Module

**Step 1: Create directory and __init__.py**

```python
# ecox-data-platform/src/ecox_platform/sources/{source}/__init__.py
from ecox_platform.sources.{source}.repository import {Source}Repository
from ecox_platform.sources.{source}.service import {Source}Service

__all__ = ["{Source}Repository", "{Source}Service"]
```

**Step 2: Create models.py**

Define Pydantic models matching the API response structure.

**Step 3: Create repository.py**

Must implement these methods from BaseRepository:
```python
async def get_dataset(self, dataset_code: str, filters: dict | None = None) -> dict
async def list_datasets(self, category: str | None = None) -> list[dict]
async def search_datasets(self, query: str) -> list[dict]
async def get_dataset_metadata(self, dataset_code: str) -> dict
async def validate_filters(self, dataset_code: str, filters: dict) -> bool
async def close(self) -> None

# For UI discovery (REQUIRED for web interface):
async def list_discoverable_datasets(self, page: int, page_size: int,
                                     query: str | None, session: AsyncSession) -> dict
async def get_dataset_description(self, metadata_url: str) -> str | None
```

**Step 4: Create service.py**

```python
class {Source}Service(BaseService):
    async def fetch_and_store(self, dataset_code: str,
                             filters: dict | None = None,
                             session: AsyncSession | None = None) -> dict
```

### 3.2 Add Configuration

**config/catalog.yaml** - Add source entry:
```yaml
sources:
  - code: {source}
    name: "{Source Name}"
    description: "Description"
    dataset_count_estimate: 1000
    auth_required: true/false
    base_url: "https://..."
    activated: true
```

**config/datasets.yaml** - Add sample datasets:
```yaml
{source}:
  - dataset_code: "SAMPLE_CODE"
    description: "Sample dataset"
    filters: {}
    max_age_hours: 24
    enabled: true
```

**ecox-data-platform/src/ecox_platform/config.py** - Add settings:
```python
{source}_api_key: str = Field(default="", description="API key for {Source}")
{source}_base_url: str = Field(default="https://...", description="Base URL")
```

### 3.3 Integration Points (CRITICAL)

**ecox-data-platform/src/ecox_platform/scheduler/source_worker.py** - Add source to worker:

```python
elif source == "{source}":
    from ecox_platform.sources.{source}.service import {Source}Service
    service = {Source}Service()
```

**ecox-data-platform/src/ecox_platform/api/routes/datasets.py** - Add to route handlers:

Pattern for dataset routes:
```python
if "{source}" in activated_codes:
    from ecox_platform.sources.{source}.repository import {Source}Repository
    {source}_repo = {Source}Repository()
    repos_to_close.append({source}_repo)
    tasks.append({source}_repo.list_discoverable_datasets(...))
    source_names.append("{source}")
```

**ecox-data-platform/src/ecox_platform/config.py** - Add source settings:

```python
{source}_rate_limit: float = Field(default=2.0)
{source}_max_concurrent: int = Field(default=3)
{source}_refresh_hours: int = Field(default=24)
```

### 3.4 Write Tests

Create unit tests with mocked HTTP client:
```python
# ecox-data-platform/tests/unit/test_{source}_repository.py
@pytest.mark.asyncio
async def test_get_dataset_success():
    ...

@pytest.mark.asyncio
async def test_list_discoverable_datasets():
    ...
```

---

## Phase 4: Verification Checklist

### 4.1 Run Tests
```bash
cd ecox-data-platform && uv run pytest tests/unit/test_{source}*.py -v
cd ecox-data-platform && uv run pytest tests/ -x  # All tests must pass
```

### 4.2 Type Checking
```bash
cd ecox-data-platform && uv run mypy src/ecox_platform/sources/{source}/
```

### 4.3 Start Server and Verify UI

```bash
cd ecox-data-platform && uv run uvicorn ecox_platform.main:app --reload
```

Verify in browser or with curl:
- [ ] Source appears in sources list
- [ ] Can activate/deactivate source
- [ ] Datasets appear in "Available" tab when source is selected
- [ ] Can click on a dataset to see details
- [ ] Can download a dataset
- [ ] Dataset appears in "Downloaded" after fetch
- [ ] SSE updates show progress during fetch
- [ ] No console errors

### 4.4 Verify Startup Auto-fetch

```bash
# Restart server and check logs
cd ecox-data-platform && uv run uvicorn ecox_platform.main:app --reload
# Look for: "Starting dataset refresh for {source}"
```

---

## Phase 5: Documentation

### 5.1 Update CLAUDE.md

Add a section documenting the new data source:

```markdown
### {Source Name}

**Added:** {date}

**Implementation Details:**
- **Source:** {API URL}
- **Authentication:** {API key required / None}
- **Key Components:**
  - `{Source}Repository`: Handles API requests
  - `{Source}Service`: Business logic and storage

**Verification:**
- **Unit Tests:** `cd ecox-data-platform && uv run pytest tests/unit/test_{source}*.py`
- **Web UI:** Auto-fetches configured datasets on startup
```

### 5.2 Commit with Meaningful Message

Use `/commit` to create a well-structured commit.

---

## Summary Checklist

Before marking complete, verify ALL items:

### Requirements Validation (Phase 1.5)
- [ ] Requirements checklist completed (C1-C4, I1-I4, O1-O6)
- [ ] Data mapping table filled out
- [ ] Compatibility score calculated
- [ ] Validation summary documented
- [ ] User confirmation obtained to proceed

### Core Implementation
- [ ] `ecox-data-platform/src/ecox_platform/sources/{source}/__init__.py` created
- [ ] `ecox-data-platform/src/ecox_platform/sources/{source}/models.py` created
- [ ] `ecox-data-platform/src/ecox_platform/sources/{source}/repository.py` created (implements BaseRepository)
- [ ] `ecox-data-platform/src/ecox_platform/sources/{source}/service.py` created (extends BaseService)

### Configuration
- [ ] `config/catalog.yaml` - source entry added
- [ ] `config/datasets.yaml` - sample datasets added
- [ ] `ecox-data-platform/src/ecox_platform/config.py` - settings added

### Integration (CRITICAL)
- [ ] `scheduler/source_worker.py` - source worker updated
- [ ] `api/routes/datasets.py` - route handlers updated

### Testing & Docs
- [ ] Unit tests created and passing
- [ ] UI verification completed
- [ ] CLAUDE.md updated with source documentation

**Only mark as complete when ALL checkboxes are verified!**
