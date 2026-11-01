# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- version list -->

## v1.21.0 (2026-01-31)

### Bug Fixes

- **news**: Correct HTMX target for category filter
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

- **news**: Enable independent scrolling for feed and detail panel
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

- **news**: Resolve Alpine.js component not loading in HTMX-swapped content
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

- **tests**: Skip superseded BDD tests and fix asyncio compatibility
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

- **ui**: Use data attributes for toast in HTMX-loaded partial
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

### Documentation

- **news**: Add requirements for chronological feed redesign
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

- **news**: Add US-5.17 requirements, ADR addendum, and implementation plan
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

### Features

- **dev**: Add frontend hot reload support with volume mounts
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

- **news**: Redesign news feed with chronological view and detail panel
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

- **ui**: Add vertical navigation sidebar ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))

- **ui**: Add vertical navigation sidebar and news feed improvements
  ([#39](https://github.com/thbttrd/eco-x/pull/39),
  [`b268c93`](https://github.com/thbttrd/eco-x/commit/b268c93fadd67bcf89e5f2a85c63eca241aef512))


## v1.20.0 (2026-01-10)

### Chores

- Improve dev workflow with modular rules and unified research skill
  ([#38](https://github.com/thbttrd/eco-x/pull/38),
  [`01bb6ae`](https://github.com/thbttrd/eco-x/commit/01bb6ae08e4950363fa757e113d534e6bf2f62f3))

- Split CLAUDE.md into modular path-aware rules ([#38](https://github.com/thbttrd/eco-x/pull/38),
  [`01bb6ae`](https://github.com/thbttrd/eco-x/commit/01bb6ae08e4950363fa757e113d534e6bf2f62f3))

### Features

- **skills**: Integrate docs agents into update-requirements
  ([#38](https://github.com/thbttrd/eco-x/pull/38),
  [`01bb6ae`](https://github.com/thbttrd/eco-x/commit/01bb6ae08e4950363fa757e113d534e6bf2f62f3))

### Refactoring

- **skills**: Merge update-requirements into research-and-design
  ([#38](https://github.com/thbttrd/eco-x/pull/38),
  [`01bb6ae`](https://github.com/thbttrd/eco-x/commit/01bb6ae08e4950363fa757e113d534e6bf2f62f3))


## v1.19.0 (2026-01-09)

### Bug Fixes

- **docs**: Use backticks for command substitution to avoid zsh parse errors
  ([#37](https://github.com/thbttrd/eco-x/pull/37),
  [`f025da8`](https://github.com/thbttrd/eco-x/commit/f025da8e738a3670a96a377a209861a76e2d0b4c))

- **skills**: Remove invalid model field from skill frontmatter
  ([#37](https://github.com/thbttrd/eco-x/pull/37),
  [`f025da8`](https://github.com/thbttrd/eco-x/commit/f025da8e738a3670a96a377a209861a76e2d0b4c))

### Documentation

- Add architecture decision record for agentic AI system
  ([#37](https://github.com/thbttrd/eco-x/pull/37),
  [`f025da8`](https://github.com/thbttrd/eco-x/commit/f025da8e738a3670a96a377a209861a76e2d0b4c))

- Add Epic 14 requirements for agentic AI features ([#37](https://github.com/thbttrd/eco-x/pull/37),
  [`f025da8`](https://github.com/thbttrd/eco-x/commit/f025da8e738a3670a96a377a209861a76e2d0b4c))

- Clarify research-and-design skill outputs ADRs, not plan files
  ([#37](https://github.com/thbttrd/eco-x/pull/37),
  [`f025da8`](https://github.com/thbttrd/eco-x/commit/f025da8e738a3670a96a377a209861a76e2d0b4c))

### Features

- Add agentic development system with skills and agents
  ([#37](https://github.com/thbttrd/eco-x/pull/37),
  [`f025da8`](https://github.com/thbttrd/eco-x/commit/f025da8e738a3670a96a377a209861a76e2d0b4c))

- **agents**: Add ecox-agents service with news summarization
  ([#37](https://github.com/thbttrd/eco-x/pull/37),
  [`f025da8`](https://github.com/thbttrd/eco-x/commit/f025da8e738a3670a96a377a209861a76e2d0b4c))


## v1.18.2 (2025-12-28)

### Bug Fixes

- **docs**: Use backticks for command substitution to avoid zsh parse errors
  ([#36](https://github.com/thbttrd/eco-x/pull/36),
  [`48f5875`](https://github.com/thbttrd/eco-x/commit/48f5875fc31571c11899c4ed40ae82bea8cdd174))

### Documentation

- Add architecture decision record for agentic AI system
  ([#36](https://github.com/thbttrd/eco-x/pull/36),
  [`48f5875`](https://github.com/thbttrd/eco-x/commit/48f5875fc31571c11899c4ed40ae82bea8cdd174))


## v1.18.1 (2025-12-28)

### Bug Fixes

- **tests**: Update unit test mocks for SQLModel session.exec() migration
  ([#35](https://github.com/thbttrd/eco-x/pull/35),
  [`3542f43`](https://github.com/thbttrd/eco-x/commit/3542f43f216ad86fb6b9508641eee7fafa4496e5))


## v1.18.0 (2025-12-28)

### Bug Fixes

- **tests**: Add missing BDD step definitions and align documentation
  ([#34](https://github.com/thbttrd/eco-x/pull/34),
  [`d11179d`](https://github.com/thbttrd/eco-x/commit/d11179d2492667da8817dfd0e3a332eb3b518587))

### Chores

- **claude**: Clean up skills and commands configuration
  ([#34](https://github.com/thbttrd/eco-x/pull/34),
  [`d11179d`](https://github.com/thbttrd/eco-x/commit/d11179d2492667da8817dfd0e3a332eb3b518587))

### Features

- **datasets**: Add source URL links to dataset detail modal (US-2.10)
  ([#34](https://github.com/thbttrd/eco-x/pull/34),
  [`d11179d`](https://github.com/thbttrd/eco-x/commit/d11179d2492667da8817dfd0e3a332eb3b518587))


## v1.17.0 (2025-12-27)

### Features

- **news**: Implement hierarchical news sections with full content
  ([#32](https://github.com/thbttrd/eco-x/pull/32),
  [`883195f`](https://github.com/thbttrd/eco-x/commit/883195f1f19e05631220c1990b371f27d3ec85be))


## v1.16.1 (2025-12-27)

### Bug Fixes

- **deploy**: Shell escaping fixes and executable command
  ([#33](https://github.com/thbttrd/eco-x/pull/33),
  [`00d942e`](https://github.com/thbttrd/eco-x/commit/00d942eb9a7b2de45cb4d0f2bf928c6b998894db))


## v1.16.0 (2025-12-27)

### Chores

- Consolidate commands and clean up unused Playwright-dependent tools
  ([#30](https://github.com/thbttrd/eco-x/pull/30),
  [`a7a1076`](https://github.com/thbttrd/eco-x/commit/a7a1076ad0ca58f3bb5f9ab8493f111487e28e5f))

- Convert update-requirements to auto-invocable skill
  ([#30](https://github.com/thbttrd/eco-x/pull/30),
  [`a7a1076`](https://github.com/thbttrd/eco-x/commit/a7a1076ad0ca58f3bb5f9ab8493f111487e28e5f))

- Create /frontend skill with htmx/Alpine.js docs ([#30](https://github.com/thbttrd/eco-x/pull/30),
  [`a7a1076`](https://github.com/thbttrd/eco-x/commit/a7a1076ad0ca58f3bb5f9ab8493f111487e28e5f))

- Improve dev workflow with skills and documentation
  ([#30](https://github.com/thbttrd/eco-x/pull/30),
  [`a7a1076`](https://github.com/thbttrd/eco-x/commit/a7a1076ad0ca58f3bb5f9ab8493f111487e28e5f))

- Optimize CLAUDE.md token usage (~50% reduction) ([#30](https://github.com/thbttrd/eco-x/pull/30),
  [`a7a1076`](https://github.com/thbttrd/eco-x/commit/a7a1076ad0ca58f3bb5f9ab8493f111487e28e5f))

### Features

- **nbs**: Implement NBS China data source with robust API handling
  ([#31](https://github.com/thbttrd/eco-x/pull/31),
  [`c1b9de1`](https://github.com/thbttrd/eco-x/commit/c1b9de1aef7276511a89825a3cf43166066c107e))


## v1.15.1 (2025-12-25)

### Bug Fixes

- **ui**: Improve datasets tab UX with top pagination and working source filter
  ([#29](https://github.com/thbttrd/eco-x/pull/29),
  [`71e8cc9`](https://github.com/thbttrd/eco-x/commit/71e8cc9894b7af4a55bb57832527a8236aefc1e5))


## v1.15.0 (2025-12-24)

### Features

- Add multi-instance deployment support via folder copies
  ([#28](https://github.com/thbttrd/eco-x/pull/28),
  [`d53fe53`](https://github.com/thbttrd/eco-x/commit/d53fe5302e135794f352ea07106923bee01dbce5))


## v1.14.0 (2025-12-23)

### Bug Fixes

- **client**: Prevent localStorage quota errors from breaking datasets UI
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **deploy**: Ensure readable file permissions in containers
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Remove hardcoded config path ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Run feedparser in thread pool to avoid blocking
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Use UTC timestamps consistently ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

### Chores

- Remove obsolete data/.gitkeep ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

### Documentation

- Add context-optimized Claude profiles documentation
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **epic5**: Add news fetching and parsing requirements
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

### Features

- **news**: Add API endpoints for news browsing ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add article parser with RSS/CSS/XPath support
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add background worker for continuous fetching
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add configuration loader for news sources
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add database models and migration for news fetching
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add enabled flag to config schema ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add is_active field for source activation control
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add repository and service layer ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add SSE events for real-time article updates
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Economic News Aggregation - Epic 5 Complete
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Enable only ECB source initially ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Expose is_active in API responses ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Filter inactive sources in worker ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Respect enabled flag in import logic ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Show activation status in UI ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Update UI for news articles display ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

### Performance Improvements

- **news**: Fix N+1 query in list_articles API ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Fix N+1 query in upsert_articles ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

### Refactoring

- **news**: Add dependency injection for testability
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

### Testing

- **news**: Add BDD tests for Epic 05 (News Aggregation)
  ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add unit tests for news API routes ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add unit tests for NewsParser ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))

- **news**: Add unit tests for NewsRepository ([#27](https://github.com/thbttrd/eco-x/pull/27),
  [`b3c0619`](https://github.com/thbttrd/eco-x/commit/b3c06196663b36d881b92c41f5846c6bc73aed0b))


## v1.13.1 (2025-12-21)

### Bug Fixes

- **oecd**: Handle 429 rate limiting with queue pause instead of stopping
  ([#26](https://github.com/thbttrd/eco-x/pull/26),
  [`144d8b8`](https://github.com/thbttrd/eco-x/commit/144d8b8d820a5673b75ec0bdadfb4837112ddc2c))


## v1.13.0 (2025-12-20)

### Bug Fixes

- Improve dataset fetching reliability across all data sources
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **fred**: Reduce rate limit from 10 to 2 req/sec to match API limits
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **http**: Add dedicated connection pool for large downloads
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **http**: Remove unused max_retries parameter ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **http**: Retry on connection drop during streaming
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **oecd**: Add streaming support for large JSON responses
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **oecd**: Handle 'value' field as alternative to 'id' in dimension values
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **ons**: Allow datasets to recover from problematic state on success
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **ons**: Reduce failure threshold to 1 for immediate skip
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **ons**: Track and skip datasets with consistent 500 errors
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **worker**: Don't count 5xx server errors as consecutive failures
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **worker**: Improve 5xx error detection to avoid false positives
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **worker**: Track 5xx server errors and skip without counting as failure
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

### Documentation

- Add validation scripts pattern to CLAUDE.md ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- Update FRED rate limit from 10 to 2 req/s ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

### Features

- **ons**: Add Census 2021 support with /json endpoint
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

- **worker**: Add multi-queue architecture with timeout tracking
  ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))

### Testing

- Add unit tests for dataset fetching fixes ([#25](https://github.com/thbttrd/eco-x/pull/25),
  [`d502ef8`](https://github.com/thbttrd/eco-x/commit/d502ef890f85e6db728898ac228cd0c4d449c1eb))


## v1.12.0 (2025-12-19)

### Bug Fixes

- **oecd**: Address code review issues for resource management and reliability
  ([#24](https://github.com/thbttrd/eco-x/pull/24),
  [`3c205f2`](https://github.com/thbttrd/eco-x/commit/3c205f288feb3a99a18324d5735a4ecf176052f3))

### Features

- **oecd**: Implement OECD data source with SDMX 2.1 API
  ([#24](https://github.com/thbttrd/eco-x/pull/24),
  [`3c205f2`](https://github.com/thbttrd/eco-x/commit/3c205f288feb3a99a18324d5735a4ecf176052f3))


## v1.11.1 (2025-12-19)

### Bug Fixes

- **ons**: Skip negative dimension values that cause API 500 errors
  ([#23](https://github.com/thbttrd/eco-x/pull/23),
  [`c23b65d`](https://github.com/thbttrd/eco-x/commit/c23b65d5860910dd0a5a1d07073a1e48ab91da33))


## v1.11.0 (2025-12-19)

### Features

- Add /worktree command for parallel feature development
  ([#22](https://github.com/thbttrd/eco-x/pull/22),
  [`7c3027b`](https://github.com/thbttrd/eco-x/commit/7c3027b6e70d5cfa2c14b9b8decd73a1da8938f7))


## v1.10.0 (2025-12-19)

### Bug Fixes

- Resolve mypy type errors across repository and API routes
  ([#21](https://github.com/thbttrd/eco-x/pull/21),
  [`f75458a`](https://github.com/thbttrd/eco-x/commit/f75458af77fa9b7e6e1c76c30df24e9c1b020abb))

### Documentation

- Add guideline to exclude AI attribution from commits
  ([#21](https://github.com/thbttrd/eco-x/pull/21),
  [`f75458a`](https://github.com/thbttrd/eco-x/commit/f75458af77fa9b7e6e1c76c30df24e9c1b020abb))

- Update add datasource command ([#21](https://github.com/thbttrd/eco-x/pull/21),
  [`f75458a`](https://github.com/thbttrd/eco-x/commit/f75458af77fa9b7e6e1c76c30df24e9c1b020abb))

### Features

- **ons**: Implement UK Office for National Statistics data source
  ([#21](https://github.com/thbttrd/eco-x/pull/21),
  [`f75458a`](https://github.com/thbttrd/eco-x/commit/f75458af77fa9b7e6e1c76c30df24e9c1b020abb))


## v1.9.0 (2025-12-19)

### Documentation

- Restructure requirements into epic-based files ([#20](https://github.com/thbttrd/eco-x/pull/20),
  [`1d1b8f6`](https://github.com/thbttrd/eco-x/commit/1d1b8f6b50b5b8b65604ba0ddd02eb81988c9cdc))

### Features

- **fred**: Implement smart refresh using source_last_update
  ([#20](https://github.com/thbttrd/eco-x/pull/20),
  [`1d1b8f6`](https://github.com/thbttrd/eco-x/commit/1d1b8f6b50b5b8b65604ba0ddd02eb81988c9cdc))


## v1.8.0 (2025-12-18)

### Features

- Smart refresh for Eurostat datasets using source_last_update
  ([#19](https://github.com/thbttrd/eco-x/pull/19),
  [`6cfeef4`](https://github.com/thbttrd/eco-x/commit/6cfeef48ac99cf62525251aa7278967271bd4ffd))


## v1.7.1 (2025-12-17)

### Bug Fixes

- **client**: Display actual platform version in UI header
  ([#18](https://github.com/thbttrd/eco-x/pull/18),
  [`f74615d`](https://github.com/thbttrd/eco-x/commit/f74615df7e3a4bb730d3a2be94941639c039eb7e))

- **client**: Pass version to container via build arg
  ([#18](https://github.com/thbttrd/eco-x/pull/18),
  [`f74615d`](https://github.com/thbttrd/eco-x/commit/f74615df7e3a4bb730d3a2be94941639c039eb7e))

### Documentation

- Update build instructions for client version injection
  ([#18](https://github.com/thbttrd/eco-x/pull/18),
  [`f74615d`](https://github.com/thbttrd/eco-x/commit/f74615df7e3a4bb730d3a2be94941639c039eb7e))


## v1.7.0 (2025-12-16)

### Bug Fixes

- Clean up stale references and fix test resource leak
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **alembic**: Update imports for monorepo structure
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **ci**: Configure monorepo pytest for pre-push hook
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **ci**: Update paths and workspace config for monorepo structure
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **container**: Install ecox-shared before platform in Containerfile
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **eurostat**: Handle non-numeric values in JSON-stat parsing
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Improve test isolation and mock session handling
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **types**: Resolve mypy strict mode and bandit security errors
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

### Chores

- Update step_defs imports and lockfile ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

### Code Style

- Apply ruff formatting to test files ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

### Documentation

- Add testing guide for BDD tests ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- Add testing reference to CLAUDE.md ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **commands**: Update add-datasource command for monorepo structure
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

### Features

- **test**: Add pytest-bdd configuration to all packages
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **test**: Add shared BDD step definitions and fixtures
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **test**: Create BDD directory structure ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 1 BDD feature file and tests ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 1 UI BDD tests - Data Source Browsing
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 10 BDD feature file - Source Management
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 11 BDD tests - Internationalization
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 12 BDD tests - Performance & Reliability
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 13 BDD tests - Migrations & Factories
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 2 BDD feature file - Dataset Discovery
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 2 UI BDD tests - Dataset Discovery
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 3 BDD tests - Real-Time Updates
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 4 BDD feature file - Auto Refresh
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 5 BDD tests - News Aggregation
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 6 BDD feature file - Eurostat Fetching
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 7 BDD feature file - FRED Fetching
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- **tests**: Add Epic 9 BDD feature file - Storage & History
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

### Refactoring

- Migrate to BDD testing with pytest-bdd and remove legacy code
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- Remove legacy root tests/ directory ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

- Remove legacy src/data_fetchers code ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))

### Testing

- **eurostat**: Add unit tests for JSON-stat value parsing
  ([#17](https://github.com/thbttrd/eco-x/pull/17),
  [`9a36df2`](https://github.com/thbttrd/eco-x/commit/9a36df24b204eb9fb2055f91a4a8cf92c0eadc1d))


## v1.6.1 (2025-12-15)

### Bug Fixes

- **tests**: Use Integer.with_variant for SQLite/PostgreSQL compatibility
  ([#16](https://github.com/thbttrd/eco-x/pull/16),
  [`8e5641f`](https://github.com/thbttrd/eco-x/commit/8e5641f2a2106dc1adbb29b1d8bc177011a13cbb))


## v1.6.0 (2025-12-14)

### Bug Fixes

- Resolve pre-commit type errors and improve test isolation
  ([`2d919e4`](https://github.com/thbttrd/eco-x/commit/2d919e4e595c572bc80f665d28037a4ddffb4fa9))

- **client**: Add error handling and accessibility to refresh button
  ([`4287d4b`](https://github.com/thbttrd/eco-x/commit/4287d4bd85f43cca1ed43a4d9ff1af8fe86b9e1e))

- **client**: Add refresh button and auto-full-refresh for stale datasets cache
  ([`4d8b8f1`](https://github.com/thbttrd/eco-x/commit/4d8b8f13bb3bec97ccde29a2f3be629d1ade3206))

- **client**: Always run staleness check on datasets tab click
  ([`aaed718`](https://github.com/thbttrd/eco-x/commit/aaed7187994365dfe0bad605ca73f442e26683cc))

- **client**: Always show SOURCE column in datasets table
  ([`0daa636`](https://github.com/thbttrd/eco-x/commit/0daa6369baa488cd21446d2caa63caa3f3f0510c))

- **client**: Dynamically populate datasource filter from loaded datasets
  ([`fed2284`](https://github.com/thbttrd/eco-x/commit/fed228409a096a275b895d5d20c3c883df418a8d))

- **client**: Improve source management modal UX
  ([`e1eae3e`](https://github.com/thbttrd/eco-x/commit/e1eae3eb286e4219ba6bc71cdc28b3d72decfc7a))

- **client**: Properly translate datasets count with Alpine.js runtime values
  ([`1eb7948`](https://github.com/thbttrd/eco-x/commit/1eb79484ae98b71f01f4d337b93b4757a55e4c3a))

- **client**: Refresh datasource filter when sources are activated
  ([`80659a7`](https://github.com/thbttrd/eco-x/commit/80659a77c9dc76d8dc8b0f0a55a429eeadc59695))

- **client**: Use initDatasets() for incremental sync on tab click
  ([`1818ae6`](https://github.com/thbttrd/eco-x/commit/1818ae6f97ce08107af81381964923b1e926f889))

- **platform**: Add migration for skippeddataset unique constraint
  ([`2ad338b`](https://github.com/thbttrd/eco-x/commit/2ad338beca9057c8ee835047d481b32964355a11))

- **platform**: Complete record_count optimization across all endpoints
  ([`23de62b`](https://github.com/thbttrd/eco-x/commit/23de62bc2e5cc17fdcb4b2a971344240d866835c))

- **platform**: Improve worker creation failure logging
  ([`7623a26`](https://github.com/thbttrd/eco-x/commit/7623a263763067331b5f5b264953ba5b69e6741f))

- **platform**: Pass session to TOC discovery for proper DB caching
  ([`b98430d`](https://github.com/thbttrd/eco-x/commit/b98430d22900d033d2681fbfc3281e5544bfdfe1))

- **platform**: Prioritize new datasets over stale updates in worker
  ([`6f04a07`](https://github.com/thbttrd/eco-x/commit/6f04a072fb69d05abc81181d5edc5a5179939feb))

- **platform**: Use text() for raw SQL in database health check
  ([`71a0bb7`](https://github.com/thbttrd/eco-x/commit/71a0bb7c93a876dd31d1f7e52262724e16e2caa9))

- **shared**: Add unique constraint to SkippedDataset model
  ([`0b21642`](https://github.com/thbttrd/eco-x/commit/0b21642c69bda0ad796e4c9e72a331bf4d84a84b))

### Chores

- Configure context7 MCP in the repo
  ([`d133472`](https://github.com/thbttrd/eco-x/commit/d1334720549f3b598559562aa95f5acaaa2c01e5))

- Update postregesql from v16 to v18
  ([`9846257`](https://github.com/thbttrd/eco-x/commit/9846257a3e3115e0a888f70a324162dc9d19208e))

- **client**: Remove old templates directory after refactor
  ([`ab22b0e`](https://github.com/thbttrd/eco-x/commit/ab22b0e79d0fa8021e4a98b91b5e87a8a1bdd149))

### Documentation

- Add package READMEs for shared, platform, and client
  ([`c98cbbb`](https://github.com/thbttrd/eco-x/commit/c98cbbb7720a40e05f7c71a2a8f546ba414c1f34))

- Update deployment guide and add architecture documentation
  ([`237ca63`](https://github.com/thbttrd/eco-x/commit/237ca63854a2ef4020cd5aff60e9839a8d02dca8))

- Update root README for monorepo architecture
  ([`0e04ed4`](https://github.com/thbttrd/eco-x/commit/0e04ed4d450e6c7062d7d1efc566e7fc110774d1))

### Features

- Add Containerfiles and podman-compose orchestration
  ([`c78ff32`](https://github.com/thbttrd/eco-x/commit/c78ff323a2a2b6e405226f8649380f9381594379))

- Add FRED API key var to podman compose so the we fetch the FRED dataset
  ([`ef40c0f`](https://github.com/thbttrd/eco-x/commit/ef40c0f1d88d9462d8e2a9ed4650fdb8247e4682))

- **api**: Add 'fetch all datasets' endpoint for client-side pagination
  ([`1e82c3b`](https://github.com/thbttrd/eco-x/commit/1e82c3b0f2777a89690f6cc0b38c1cf67770b258))

- **cache**: Enhance cache with thread safety and performance improvements
  ([`e78d12a`](https://github.com/thbttrd/eco-x/commit/e78d12a874924e3db04cadcf1a08c9d110a01318))

- **client**: Add fuzzy search for datasets using Fuse.js
  ([`c38e2d7`](https://github.com/thbttrd/eco-x/commit/c38e2d7b908c18ee7a99ef5e2b62d92d9b8924c2))

- **client**: Add since_id support to platform client and API
  ([`8f09928`](https://github.com/thbttrd/eco-x/commit/8f099287133ad08e59ec37ec2da3ac046bd79a41))

- **client**: Add SourceActivation model for data source management
  ([`9bcfa91`](https://github.com/thbttrd/eco-x/commit/9bcfa9148ff69a76bd0791b37af001063b6cf654))

- **client**: Add SSE events endpoint for real-time connection status
  ([`fbd8e54`](https://github.com/thbttrd/eco-x/commit/fbd8e5438d926c966f37be1406fef344d7d46bd6))

- **client**: Add UI routes and i18n support
  ([`b0d605f`](https://github.com/thbttrd/eco-x/commit/b0d605f1684c72aa9fcd29a47198fd164621b7f7))

- **client**: Create ecox-client package structure
  ([`7f53850`](https://github.com/thbttrd/eco-x/commit/7f53850659ffb9b05620160d0843fe4ffbbe8630))

- **client**: Implement Alpine.js client-side pagination for datasets
  ([`49dafbc`](https://github.com/thbttrd/eco-x/commit/49dafbcbadb94794a1f0415fc66699e2192e819f))

- **client**: Implement source activation toggle with dynamic filtering
  ([`97f1bfe`](https://github.com/thbttrd/eco-x/commit/97f1bfeb9b6f0628f40a5f6db97ec1ec5a6f4bf5))

- **client**: Implement stale-while-revalidate caching with incremental updates
  ([`449c6f3`](https://github.com/thbttrd/eco-x/commit/449c6f3062f9766bc339c6f23aa8ba6f602382e7))

- **health**: Add /memory endpoint for cache and process statistics
  ([`9b821f0`](https://github.com/thbttrd/eco-x/commit/9b821f08c7575aa7275a9326e332fc7ded7af08c))

- **infra**: Add cache cleanup daemon with 8GB size limit
  ([`7cf8899`](https://github.com/thbttrd/eco-x/commit/7cf889983d5d83eaccc03332eeab2d2258313ece))

- **platform**: Add data source base classes and Eurostat implementation
  ([`94f1f6f`](https://github.com/thbttrd/eco-x/commit/94f1f6fd3f9831d419aa03afd5ed94b2d8a90468))

- **platform**: Add FRED API models
  ([`6d2693c`](https://github.com/thbttrd/eco-x/commit/6d2693c59529db9d3ec83fbc559c645413a67de7))

- **platform**: Add FRED repository
  ([`5e6cd7d`](https://github.com/thbttrd/eco-x/commit/5e6cd7d11e6b5dd0a494a90c3c21cacf71272c2c))

- **platform**: Add since_id parameter for incremental dataset fetching
  ([`ef5d316`](https://github.com/thbttrd/eco-x/commit/ef5d3165ed406407fb7a8749786809080e772f79))

- **platform**: Build REST API for data platform
  ([`dd7b7f7`](https://github.com/thbttrd/eco-x/commit/dd7b7f765ede0e10457d8e26171d81ed8c6fb0ff))

- **platform**: Create ecox-data-platform structure with PostgreSQL
  ([`099d113`](https://github.com/thbttrd/eco-x/commit/099d113cbd1647915fd4181f56b79e41f581eb03))

- **platform**: Implement continuous fetch scheduler
  ([`137186b`](https://github.com/thbttrd/eco-x/commit/137186bb7bcca15b1f494b33ec8f45656b0d6229))

- **platform**: Implement FRED service with fetch_and_store
  ([`142c345`](https://github.com/thbttrd/eco-x/commit/142c3451fce71c21d61e1e2f3d45e9ffc0c514e9))

- **platform**: Integrate cache cleanup daemon into lifespan
  ([`5a8f75b`](https://github.com/thbttrd/eco-x/commit/5a8f75b7f5c5d161f78ab3367d266bf72e504492))

- **platform**: Register FRED in continuous fetcher
  ([`6b3c1b2`](https://github.com/thbttrd/eco-x/commit/6b3c1b2e00d450ec2e181649d67462ebee10cb78))

- **platform**: Skip large datasets and track in database
  ([`83b429d`](https://github.com/thbttrd/eco-x/commit/83b429d7cbe736829f7004d7c9eb6c2ffb725dc5))

- **service**: Add chunked database inserts for data values
  ([`f585279`](https://github.com/thbttrd/eco-x/commit/f585279cb79b2b2c4ed05b3d25e7f297dafec5c4))

- **shared**: Create ecox-shared package with models and utilities
  ([`6c87490`](https://github.com/thbttrd/eco-x/commit/6c8749074dc254ba962d8f0bbd434942132e4cfa))

### Performance Improvements

- **client**: Cache datasets in sessionStorage for instant language switch
  ([`8797773`](https://github.com/thbttrd/eco-x/commit/8797773c9d3054c1749c08c90adbc44f94047022))

- **client**: Implement client-side source filtering for datasets
  ([`160b386`](https://github.com/thbttrd/eco-x/commit/160b3864475b2ad45fb03b4f6d26c27f693cadbc))

- **platform**: Add record_count column to Dataset for faster queries
  ([`0510d8f`](https://github.com/thbttrd/eco-x/commit/0510d8f373cec1660206080ac6bc962b19f9af98))

- **platform**: Implement batched inserts to prevent event loop blocking
  ([`31c35ab`](https://github.com/thbttrd/eco-x/commit/31c35abcd930aa4aa2b692b38748ccd67741dbf2))

- **platform**: Offload JSON-stat parsing to thread pool
  ([`2175817`](https://github.com/thbttrd/eco-x/commit/217581757f1804d7ce89c526fe9d88b5379dc590))

- **shared**: Add database indexes for faster dataset queries
  ([`362c1d5`](https://github.com/thbttrd/eco-x/commit/362c1d51ff2cba3d0923164bd6cfd34d053f51f3))

### Refactoring

- Remove deprecated dataset selection and config
  ([`a00f571`](https://github.com/thbttrd/eco-x/commit/a00f5712e48df69684d639440f2750b3d4d68166))

- **repos**: Migrate TOC caches to main cache system
  ([`9f6af72`](https://github.com/thbttrd/eco-x/commit/9f6af729fd03e8880787e35006fd4356a4e168f1))

### Testing

- **cache**: Add unit tests for cleanup daemon and eviction
  ([`ef89e5f`](https://github.com/thbttrd/eco-x/commit/ef89e5f5bf447a4fdf8ca03d9c20b9354ca3c700))

- **client**: Add comprehensive tests for ecox-client package
  ([`6270821`](https://github.com/thbttrd/eco-x/commit/627082156f97812dc74a9f0d7a286b93941aa92e))

- **platform**: Add API route tests for sources, datasets, and fetch logs
  ([`0a47c1c`](https://github.com/thbttrd/eco-x/commit/0a47c1c989ad1e4886517c49868edede7c74730a))

- **platform**: Add health API route tests
  ([`cbd0b9f`](https://github.com/thbttrd/eco-x/commit/cbd0b9f5300445028959dbdf97512477490e8c2d))

- **platform**: Add test infrastructure and cache tests
  ([`958defb`](https://github.com/thbttrd/eco-x/commit/958defb7d52ee99b960019807682093f724d3d71))

- **platform**: Add unit tests for FRED implementation
  ([`3dadb6a`](https://github.com/thbttrd/eco-x/commit/3dadb6a02e6a7714f82a5fa0ecd8b2cee413826c))

- **shared**: Add model and schema tests to ecox-shared
  ([`3c6caee`](https://github.com/thbttrd/eco-x/commit/3c6caeea7d402392f325212271617d8d0e589905))

- **shared**: Add ResilientHttpClient tests to ecox-shared
  ([`3427634`](https://github.com/thbttrd/eco-x/commit/3427634321eb66ed2874508c829321ccb8a35f8d))

- **shared**: Add test infrastructure to ecox-shared
  ([`5160260`](https://github.com/thbttrd/eco-x/commit/516026079a840c70485f6df8e93d553e088335a4))


## v1.5.0 (2025-12-04)

### Bug Fixes

- **http**: Enable redirect following and add WAF detection
  ([`a146be3`](https://github.com/thbttrd/eco-x/commit/a146be36d04c7dd928dd29105b8c46e01f8d3bf0))

- **nbs**: Fix TOC fetching and htmx SSE compatibility
  ([`c85dd28`](https://github.com/thbttrd/eco-x/commit/c85dd2804631e08c5babc63b46893c07ce92b872))

- **oecd**: Make metadata lookup non-fatal in service
  ([`d20ae60`](https://github.com/thbttrd/eco-x/commit/d20ae60949d778c4d057ef1cfacabab6843e2c90))

- **oecd**: Use TOC cache as primary metadata source
  ([`ff9e52f`](https://github.com/thbttrd/eco-x/commit/ff9e52fa11442320ecd5bb8b9f040db806497458))

### Chores

- Update uv.lock metadata
  ([`8a58e93`](https://github.com/thbttrd/eco-x/commit/8a58e9376a911ab50b03740a7d2b1a6462664e5c))

### Features

- **nbs**: Add NBS China data source integration
  ([`41f622a`](https://github.com/thbttrd/eco-x/commit/41f622a36a89c1f1c9343a1bc10af97cc463b5a2))

### Testing

- Add tests for OECD service and HTTP client to meet 65% coverage
  ([`163b4a9`](https://github.com/thbttrd/eco-x/commit/163b4a9795b8cb269671081935804143f58ec184))


## v1.4.2 (2025-12-04)

### Bug Fixes

- **oecd**: Use XML parsing for TOC fetch to fix truncated JSON response
  ([`17aabd3`](https://github.com/thbttrd/eco-x/commit/17aabd32808b77f6f59a94f6e63711a511fc592f))


## v1.4.1 (2025-12-03)

### Bug Fixes

- **ci**: Prevent pre-commit hooks from modifying uv.lock
  ([`308cd9e`](https://github.com/thbttrd/eco-x/commit/308cd9eca6df610abdb26b23a80d10dbc874bf54))

### Chores

- Update uv.lock format for uv 0.5.13
  ([`3f0bcd3`](https://github.com/thbttrd/eco-x/commit/3f0bcd32edf19c566a55169bee4b86c85c6ed04d))


## v1.4.0 (2025-12-03)

### Bug Fixes

- **sse**: Update SSE extension to htmx 2.x compatible version
  ([`118e347`](https://github.com/thbttrd/eco-x/commit/118e347e9fcd6c77922f46f46a33c59c2f85a20e))

- **ui**: Dynamically display version badge from package metadata
  ([`1287151`](https://github.com/thbttrd/eco-x/commit/1287151edfec1b7f64ec0dff1d9ec03185ca2b1c))

- **ui**: Use global-spinner for sources container indicator
  ([`e842e4b`](https://github.com/thbttrd/eco-x/commit/e842e4bd28814e8398a04698f738db2eb2ce5cb6))

### Features

- **ui**: Add favicon with economics chart icon
  ([`570a97c`](https://github.com/thbttrd/eco-x/commit/570a97ccfd293348fd2a6fd95d84279e3ec8dab1))


## v1.3.1 (2025-12-03)

### Bug Fixes

- **oecd**: Handle None value in dataset lookup and add model tests
  ([`ef67743`](https://github.com/thbttrd/eco-x/commit/ef6774386c69b15958c45eccc2deb62be60d4a18))


## v1.3.0 (2025-12-03)

### Chores

- Share .claude directory in git
  ([`70befcb`](https://github.com/thbttrd/eco-x/commit/70befcbfe56222b3e240ec5001eb94d501d8a3af))

- Update uv.lock
  ([`5a91c2c`](https://github.com/thbttrd/eco-x/commit/5a91c2c9a0800e7edbad72a544b32e51c13e5e87))

### Features

- **oecd**: Add OECD Data Explorer as new data source
  ([`4de1a97`](https://github.com/thbttrd/eco-x/commit/4de1a9707a3920ac058a99f9c0aa898f198a3afd))


## v1.2.0 (2025-12-02)

### Bug Fixes

- Add README.md to Containerfile build
  ([`28a92fb`](https://github.com/thbttrd/eco-x/commit/28a92fb107da12c5b09ebf8cbccf3b28fc19c8b1))

- Remove readme requirement from container build
  ([`322640a`](https://github.com/thbttrd/eco-x/commit/322640a0b9435cb74fbc80307c40acc116b74810))

### Features

- Add version to health check endpoint
  ([`02e876f`](https://github.com/thbttrd/eco-x/commit/02e876f737b00f89c138c574cd529ca709801450))

- **ui**: Add version badge to header
  ([`3d8aebc`](https://github.com/thbttrd/eco-x/commit/3d8aebc1b01799f0c018301ea86e41f2e9051933))


## v1.1.0 (2025-12-01)

### Documentation

- Add deployment guide for Podman + Pangolin setup
  ([`d3713b9`](https://github.com/thbttrd/eco-x/commit/d3713b960238101c103b9152489e8d4a26202feb))

### Features

- Add Containerfile for Podman deployment
  ([`efdcd9e`](https://github.com/thbttrd/eco-x/commit/efdcd9eaaa54d209647a7d17200b052548ed876f))


## v1.0.3 (2025-12-01)

### Bug Fixes

- Add insertion marker to CHANGELOG.md
  ([`6861e03`](https://github.com/thbttrd/eco-x/commit/6861e0379d29ee2754f0c70b4881cf2d7de8e820))


## [0.1.0] - 2024-11-29

### Added

- Initial release of eco-x
- **Data Sources:**
  - Eurostat integration (GDP, National Accounts, Prices/Inflation)
  - FRED (Federal Reserve Economic Data) integration
  - ONS (UK Office for National Statistics) integration
- **Core Features:**
  - Async HTTP client with retry logic and rate limiting
  - SQLite database storage with SQLModel
  - Database migrations with Alembic
- **Web Interface:**
  - FastAPI web application
  - htmx + Alpine.js frontend
  - Jinja2 templating
  - Server-Sent Events for real-time updates
- **CLI:**
  - Typer-based command-line interface
  - Data fetching and export commands
- **Developer Experience:**
  - Internationalization support (EN/FR)
  - Test factories with factory_boy
  - Comprehensive pre-commit hooks
  - Type checking with mypy
