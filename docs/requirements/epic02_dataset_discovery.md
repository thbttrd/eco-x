# Epic 2: Dataset Discovery & Browsing

## Overview

Enable users to discover, browse, search, and filter datasets across all data sources.

**Package:** ecox-data-platform, ecox-client
**Feature File:** `epic02_dataset_discovery.feature`

---

## User Stories

### US-2.1: Browse All Datasets

**As a** user
**I want to** browse all downloaded datasets in a unified view
**So that** I can find data across multiple sources

**Acceptance Criteria:**
- Display datasets in a paginated table (20 per page)
- Show columns: Source, Code, Name, Status, Last Fetched
- Support pagination navigation (previous/next)
- Allow filtering by source
- Click row to view dataset details

---

### US-2.2: View Dataset Details

**As a** user
**I want to** view detailed information about a dataset
**So that** I can understand what data it contains

**Acceptance Criteria:**
- Display dataset metadata (code, name, source)
- Show rich description from source metadata
- Display fetch history (last 5 operations)
- Show fetch status, duration, and record counts
- Link to original source metadata page
- Close modal with Escape key or click outside

---

### US-2.3: Identify Dataset Status

**As a** user
**I want to** see the status of each dataset
**So that** I know if data is downloaded or just available

**Acceptance Criteria:**
- "Downloaded" badge for locally stored datasets
- "Available" badge for datasets not yet fetched
- Visual distinction between statuses (colors/badges)

---

### US-2.4: Search Datasets

**As a** user
**I want to** search datasets by name or code
**So that** I can quickly find specific datasets

**Acceptance Criteria:**
- Text input field for search query in the Datasets tab header
- Search filters datasets by code (exact or partial match, case-insensitive)
- Search filters datasets by name (partial match, case-insensitive)
- Results update in real-time as user types (debounced 300ms)
- Display "No datasets found" message when search returns empty
- Clear search button (X icon) to reset search
- Search persists when changing pages (pagination)
- htmx request to `/api/datasets/{source}?search={query}` for server-side filtering

---

### US-2.5: Filter Datasets by Status

**As a** user
**I want to** filter datasets by their status
**So that** I can focus on downloaded or available datasets

**Acceptance Criteria:**
- Button group for status filter in Datasets tab header
- Filter options: "All", "Downloaded", "Available"
- Default filter is "All" (show all datasets)
- Filter updates table immediately via htmx request
- Filter persists when changing pages (pagination)
- Combine with search filter (both filters apply together)
- htmx request to `/api/datasets/{source}?status={status}` for server-side filtering
- Visual indication of active filter state (highlighted button)
- **Cross-source filtering**: All status filters work with "All Sources" view:
  - "All" shows downloaded datasets first, then available datasets from all sources
  - "Downloaded" shows only locally stored datasets from all sources
  - "Available" queries TOCs from all sources (Eurostat + FRED) in parallel and excludes downloaded
- Available datasets display "Never" in Last Fetched column

---

### US-2.6: Filter Datasets by Source

**As a** user
**I want to** filter datasets by data source
**So that** I can view datasets from a specific provider

**Acceptance Criteria:**
- Dropdown for source filter in Datasets tab header
- Options include: "All Sources", "Eurostat", "FRED"
- Default filter is "All Sources"
- Filter updates table immediately via htmx request
- Filter persists when changing pages (pagination)
- Combine with search and status filters (all filters apply together)
- htmx request to `/api/datasets/{source}` for server-side filtering
- **"All Sources" aggregates data from all providers**:
  - Queries downloaded datasets from database
  - Queries available datasets from all TOCs (cached, fetched in parallel)
  - Combined total shows all datasets across sources (e.g., "11,258 datasets")
  - Source column displays which provider each dataset comes from (EUROSTAT/FRED badge)

---

### US-2.7: Combined Filtering

**As a** user
**I want to** use multiple filters simultaneously
**So that** I can narrow down datasets precisely

**Acceptance Criteria:**
- Search, status, and source filters work together
- URL query params reflect all active filters (e.g., `?search=gdp&status=downloaded&source=eurostat`)
- Reset all filters button clears search, status, and source filters
- Pagination resets to page 1 when any filter changes
- Display active filter summary (e.g., "Showing 5 of 100 datasets")
- Preserve filter state across navigation with URL parameters

---

### US-2.8: Download Dataset from Detail Modal

**As a** user
**I want to** download a dataset directly from its detail modal
**So that** I can immediately fetch data for datasets I discover while browsing

**Acceptance Criteria:**
- Display "Download dataset" button in the dataset detail modal for available (not yet downloaded) datasets
- Button triggers immediate background download via POST to `/api/datasets/{source}/{code}/download`
- Download runs asynchronously without blocking the UI
- Dataset is automatically enabled for auto-fetch at application startup
- Modal refreshes to show updated state after download is initiated
- Show success toast notification when download completes via SSE
- Download button shows loading state while initiating download
- Display descriptive text explaining "Downloads now and updates at each startup"

---

### US-2.9: Purge Dataset Data

**As a** user
**I want to** remove downloaded data for a dataset
**So that** I can free up storage or stop tracking datasets I no longer need

**Acceptance Criteria:**
- Display "Purge data" button in the dataset detail modal for downloaded datasets
- Button triggers data removal via DELETE to `/api/datasets/{source}/{code}/purge`
- Purge deletes all DataValue records associated with the dataset
- Purge resets the dataset's last_fetched timestamp
- Purge disables auto-fetch selection for the dataset
- Modal refreshes to show "Available" status after purge completes
- Show confirmation or success indication after purge
- Dataset remains in the browse list as "Available" after purge

---

### US-2.10: View Original Source Link

**As a** user
**I want to** see a link to the original dataset page on the source website
**So that** I can access additional documentation, metadata, and context about the data

**Acceptance Criteria:**
- Display "Original Source" section in dataset detail modal with clickable URL
- Link opens in new browser tab (target="_blank")
- URL redirects to the correct dataset page on each source:
  - FRED: `https://fred.stlouisfed.org/series/{code}`
  - OECD: `https://sdmx.oecd.org/public/rest/dataflow/{agency}/{dataflow}/{version}` (SDMX metadata API - Data Explorer lacks deep linking)
  - ONS: `https://www.ons.gov.uk/datasets/{code}`
  - NBS: Display message "Dataset URLs are not available for NBS data source" (no reliable browser URLs)
  - Eurostat: `https://ec.europa.eu/eurostat/databrowser/view/{code}/default/table`
- URL is stored in database as `source_url` field for datasets with data
- For datasets without stored URL, compute URL dynamically from source and code
- Display external link icon next to the URL text
