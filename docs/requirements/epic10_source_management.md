# Epic 10: Data Source Management

## Overview

Enable users to manage data sources from a catalog, including adding, activating, and deactivating sources.

**Package:** ecox-data-platform
**Feature File:** `epic10_source_management.feature`

---

## User Stories

### US-10.1: Add Data Source from Catalog

**As a** user
**I want to** add a new data source to my instance from a catalog
**So that** I can expand the economic data available for analysis

**Acceptance Criteria:**
- Display "Add Data Source" button in the Sources tab header
- Click button opens a modal with available data sources from the catalog
- Catalog displays data sources not yet added to the instance
- Each catalog entry shows: source name, description, dataset count estimate
- Click catalog entry to add source to instance
- Show success toast notification when source is added
- Refresh sources grid to display newly added source
- Close modal after successful addition

---

### US-10.2: Browse Data Source Catalog

**As a** user
**I want to** browse the catalog of available data sources
**So that** I can discover new economic data providers

**Acceptance Criteria:**
- Modal displays catalog entries in a scrollable list or grid
- Each entry shows source name, icon, and brief description
- Show estimated number of datasets available from each source
- Visual indication for sources already added to instance (disabled/grayed out)
- Support search/filter within catalog (optional, for future)
- Close modal via X button, Escape key, or click outside

---

### US-10.3: Data Source Catalog API

**As a** system
**I want to** provide a catalog of available data sources
**So that** users can discover and add new sources

**Acceptance Criteria:**
- Return list of all supported data sources (initially faked/hardcoded)
- Each source includes: code, name, description, icon, base_url, auth_required flag
- Indicate which sources are already configured in the instance
- Catalog can be extended via configuration file (future)
- API endpoint: `GET /api/catalog/sources`

---

### US-10.4: Activate/Deactivate Data Sources

**As a** user
**I want to** activate or deactivate data sources from the catalog
**So that** I can control which sources appear in the app and are included in auto-fetch

**Acceptance Criteria:**
- Each source in the catalog has an activation toggle (switch control)
- Default activation state defined in `config/catalog.yaml` (activated: true/false)
- UI toggle overrides config default (stored in database as `SourceActivation` record)
- Activation toggle updates immediately via htmx POST to `/api/sources/{code}/activate`
- Activation toggle targets `#modal-content` to replace entire modal (not body only)
- Modal displays single header, body, and footer after toggle (no duplicate elements)
- Deactivated sources appear dimmed/grayed in the catalog modal
- Deactivated sources hidden from the Sources tab grid
- Deactivated sources' datasets hidden from the Datasets tab (all views)
- Auto-fetch on startup skips deactivated sources even if configured in datasets.yaml
- "Add" button only visible for activated sources (not yet configured)
- "Deactivated" badge shown for deactivated sources in catalog

---

### US-10.5: Effective Activation State

**As a** system
**I want to** determine the effective activation state from config and DB
**So that** UI overrides take precedence over config defaults

**Acceptance Criteria:**
- Check database `SourceActivation` table for UI overrides first
- Fall back to `catalog.yaml` activated field if no DB override exists
- Provide `get_effective_activation(source_code, session)` async function
- Provide `get_activated_sources(session)` to get all effectively activated sources
- Provide `set_source_activation(source_code, activated, session)` to store UI override
- New sources default to `activated: true` for backward compatibility if field missing
