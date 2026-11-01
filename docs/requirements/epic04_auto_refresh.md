# Epic 4: Automatic Data Refresh

## Overview

Enable automatic, configurable refresh of datasets to keep data up-to-date with minimal manual intervention.

**Package:** ecox-data-platform
**Feature File:** `epic04_auto_refresh.feature`

---

## User Stories

### US-4.1: Configure Dataset Refresh

**As an** administrator
**I want to** configure which datasets refresh automatically
**So that** critical data stays up-to-date

**Acceptance Criteria:**
- YAML configuration file for dataset settings
- Per-dataset enable/disable toggle
- Per-dataset freshness threshold (max_age_hours)
- Support for dataset-specific filters (geo, time, unit)

---

### US-4.2: Startup Refresh

**As a** user
**I want** stale datasets to refresh when the app starts
**So that** I always have reasonably fresh data

**Acceptance Criteria:**
- Check dataset freshness on startup
- Fetch stale datasets in background (non-blocking)
- Respect configured freshness thresholds
- Limit concurrent fetches (configurable)

---

### US-4.3: Smart Refresh Using Source Metadata

**As a** system
**I want to** compare the source's last update timestamp before fetching
**So that** I skip unnecessary API calls when source data hasn't changed

**Acceptance Criteria:**
- Store `source_last_update` from source metadata (TOC) in the Dataset record
- Compare stored `source_last_update` with current TOC metadata before fetching
- Skip fetch if `source_last_update` hasn't changed (source unchanged)
- Prioritize new datasets (never fetched) over stale datasets (source updated)
- Log smart refresh statistics (new, stale, unchanged counts) per refresh cycle
- Works for all sources: Eurostat, FRED
