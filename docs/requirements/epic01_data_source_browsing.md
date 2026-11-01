# Epic 1: Data Source Browsing

## Overview

Enable users to browse and understand available data sources at a glance.

**Package:** ecox-data-platform, ecox-client
**Feature File:** `epic01_data_source_browsing.feature`

---

## User Stories

### US-1.1: View Available Data Sources

**As a** user
**I want to** see all available data sources at a glance
**So that** I can understand what economic data is accessible

**Acceptance Criteria:**
- Display source cards showing source name and icon
- Show count of downloaded datasets vs available datasets
- Display last activity timestamp for each source
- Click source card to view its datasets
- Responsive grid layout (1/2/3 columns based on screen size)

---

### US-1.2: View Source Statistics

**As a** user
**I want to** see statistics for each data source
**So that** I can understand my local data coverage

**Acceptance Criteria:**
- Show number of datasets downloaded locally
- Show total datasets available from source
- Display when data was last fetched
- Update statistics in real-time when data changes
