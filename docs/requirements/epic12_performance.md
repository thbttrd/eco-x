# Epic 12: Performance & Reliability

## Overview

Ensure the platform performs well and remains reliable under various conditions.

**Package:** ecox-data-platform
**Feature File:** `epic12_performance.feature`

---

## User Stories

### US-12.1: Intelligent Caching

**As a** system
**I want** API responses cached appropriately
**So that** redundant API calls are avoided

**Acceptance Criteria:**
- 12-hour TTL cache for API responses
- Cache key based on source + dataset + filters
- Automatic cache invalidation on timeout

---

### US-12.2: Resilient HTTP Client

**As a** system
**I want** HTTP requests to be resilient
**So that** transient failures don't break fetches

**Acceptance Criteria:**
- Automatic retry with exponential backoff
- Configurable max retries (default: 3)
- Request timeout handling (default: 30s)
- Rate limiting (default: 2 req/sec)

---

### US-12.3: Self-Hosted Static Assets

**As a** system
**I want** critical JS libraries self-hosted
**So that** CDN reliability issues don't break the app

**Acceptance Criteria:**
- htmx.min.js served from /static/
- sse.js extension served from /static/
- No external CDN dependency for core functionality

---

### US-12.4: SQLite Concurrent Access

**As a** user
**I want** to browse datasets while downloads are in progress
**So that** I can continue using the application during long-running operations

**Acceptance Criteria:**
- Enable SQLite WAL (Write-Ahead Logging) mode for concurrent reads during writes
- Configure 30-second busy timeout to wait for locks instead of failing immediately
- Use shared database engine singleton across all requests (avoid separate engine instances)
- No "database is locked" errors when viewing dataset details during background downloads
- Background fetch operations complete successfully while handling concurrent read requests
- Database manager logs confirmation of WAL mode configuration on startup
