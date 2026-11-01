# Epic 6: Data Source Fetching

## Overview

Enable fetching and storing economic data from any supported data source. The platform supports a plugin-like architecture where new data sources can be added following a common pattern.

**Package:** ecox-data-platform
**Feature Files:** `epic06_eurostat_fetching.feature`, `epic07_fred_fetching.feature`

---

## User Stories

### US-6.1: Fetch Dataset from Any Source

**As a** user
**I want to** fetch economic data from any supported source
**So that** I can analyze economic indicators from different providers

**Acceptance Criteria:**
- Support pluggable data source architecture
- Each source implements common Repository/Service pattern
- Apply source-specific filters (geographic area, time period, unit)
- Parse source-specific data formats (JSON-stat, JSON, XML)
- Store data values with standardized dimensions (geo, time, indicator)
- Log fetch operation with status and duration

---

### US-6.2: Browse Source Table of Contents

**As a** user
**I want to** see all available datasets from a source
**So that** I can discover what data is accessible

**Acceptance Criteria:**
- Fetch and cache source TOC (configurable cache duration)
- Display dataset codes and names
- Show total count of available datasets
- Background refresh when cache is stale
- Store `source_last_update` from TOC metadata for smart refresh

---

### US-6.3: Source Authentication

**As a** system
**I want to** authenticate with data sources that require it
**So that** I can access protected APIs

**Acceptance Criteria:**
- Support API key authentication (FRED, etc.)
- Support public APIs without authentication (Eurostat, ONS)
- Store credentials securely in environment variables
- Handle authentication errors gracefully

---

## Supported Data Sources

| Source | Type | Authentication | API Format |
|--------|------|----------------|------------|
| **Eurostat** | EU statistics | Public API | JSON-stat 2.0 |
| **FRED** | US Federal Reserve | API key | JSON |
| **ONS** | UK statistics | Public API | JSON |
| **NBS China** | China statistics | Public API | JSON |

---

## Data Source Implementation Pattern

Each data source follows this pattern:

```
sources/{source_name}/
├── __init__.py
├── repository.py    # API client, TOC fetching
├── service.py       # Business logic, storage
└── models.py        # Pydantic models (optional)
```

### Repository Responsibilities
- API client configuration
- Rate limiting
- TOC fetching and caching
- Dataset metadata retrieval
- Data observations fetching

### Service Responsibilities
- Fetch orchestration
- Data transformation to common format
- Database storage via `store_dataset()` and `store_with_change_detection()`
- Fetch logging
- Smart refresh support via `source_last_update`
