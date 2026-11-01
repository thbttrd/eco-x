# ECO-X: Product Requirements Document

## Executive Summary

**ECO-X** (branded as "EconoScope" in the UI) is an economic data platform that enables users to fetch, browse, monitor, and analyze economic data from multiple international sources. The application provides both a web interface for accessing data from Eurostat, FRED, and other economic data providers.

**Version:** 0.1.0
**Architecture:** Async FastAPI backend with SQLite storage and hypermedia-driven frontend (htmx + Jinja2 + Alpine.js)

---

## Product Vision

Provide researchers, analysts, and developers with a unified platform to access, store, and monitor economic data from multiple authoritative sources, with automatic refresh capabilities and real-time update notifications.

---

## Core Features

### 1. Multi-Source Data Integration

| Source | Description | Authentication |
|--------|-------------|----------------|
| **Eurostat** | EU economic statistics (GDP, inflation, prices) | Public API |
| **FRED** | US Federal Reserve economic data | API key required |
| **ONS** | UK Office for National Statistics (GDP, inflation, employment) | Public API |

### 2. Web Dashboard

- **Sources Tab**: Browse available data sources with dataset counts and activity timestamps
- **Datasets Tab**: Paginated table of all datasets with status indicators and detail modals
  - Search datasets by name or code
  - Filter by status (All/Downloaded/Available)
  - Filter by source (All Sources/Eurostat/FRED)
  - **Cross-source discovery**: "All Sources" view aggregates datasets from all providers, including available datasets not yet downloaded (~11,000+ datasets)
- **News Tab**: Curated economic news sources organized by category

### 3. Real-Time Updates

Server-Sent Events (SSE) for live notifications when datasets are fetched or updated.

### 4. Automatic Data Refresh

YAML-configurable automatic fetching of stale datasets on application startup.

### 5. Local Storage

SQLite database for offline access to downloaded economic data with full fetch history.

### 6. Data Source Management

Add new data sources to your instance from a catalog of available providers (Eurostat, FRED, ONS, and future sources). Activate or deactivate sources to control visibility in the UI and inclusion in auto-fetch.

### 7. Internationalization (i18n)

Multi-language support with language switching (EN/FR). Extensible YAML-based translation system for easy addition of new languages.

---

## Epics Overview

| Epic | Name | Package | Feature File(s) |
|------|------|---------|-----------------|
| [Epic 1](epic01_data_source_browsing.md) | Data Source Browsing | data-platform, client | `epic01_data_source_browsing.feature` |
| [Epic 2](epic02_dataset_discovery.md) | Dataset Discovery & Browsing | data-platform, client | `epic02_dataset_discovery.feature` |
| [Epic 3](epic03_realtime_updates.md) | Real-Time Updates | data-platform | `epic03_realtime_updates.feature` |
| [Epic 4](epic04_auto_refresh.md) | Automatic Data Refresh | data-platform | `epic04_auto_refresh.feature` |
| [Epic 5](epic05_news_aggregation.md) | Economic News Aggregation | client | `epic05_news_aggregation.feature` |
| [Epic 6](epic06_data_fetching.md) | Data Source Fetching | data-platform | `epic06_eurostat_fetching.feature`, `epic07_fred_fetching.feature` |
| [Epic 8](epic08_application_info.md) | Application Information | client | `epic08_application_info.feature` |
| [Epic 9](epic09_storage_history.md) | Data Storage & History | data-platform | `epic09_storage_history.feature` |
| [Epic 10](epic10_source_management.md) | Data Source Management | data-platform | `epic10_source_management.feature` |
| [Epic 11](epic11_internationalization.md) | Internationalization (i18n) | client | `epic11_internationalization.feature` |
| [Epic 12](epic12_performance.md) | Performance & Reliability | data-platform | `epic12_performance.feature` |
| [Epic 13](epic13_migrations.md) | Database Migration & Test Data | shared | `epic13_migrations.feature` |
| [Epic 15](epic15_vertical_navigation.md) | Vertical Navigation Panel | client | `epic15_vertical_navigation.feature` |

> **Note:** Epic 7 (FRED fetching) has been consolidated into Epic 6 (Data Source Fetching) to support a scalable, source-agnostic architecture.
> **Note:** Epic 14 (Agentic Features) is planned and will add an "Ask" item to the navigation.

---

## Additional Documentation

- [Appendix](appendix.md) - Non-functional requirements, API endpoints, database schema, configuration files, tech stack, and glossary
