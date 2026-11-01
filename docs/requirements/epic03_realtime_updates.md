# Epic 3: Real-Time Updates

## Overview

Provide real-time notifications and connection status for live data updates.

**Package:** ecox-data-platform
**Feature File:** `epic03_realtime_updates.feature`

---

## User Stories

### US-3.1: Live Connection Status

**As a** user
**I want to** see if I'm connected to real-time updates
**So that** I know if I'll receive live notifications

**Acceptance Criteria:**
- Display "Live" indicator in header when connected
- Show connection status visually (green dot = connected)
- Auto-reconnect on disconnect

---

### US-3.2: Receive Fetch Notifications

**As a** user
**I want to** receive toast notifications when data is fetched
**So that** I'm aware of data updates in real-time

**Acceptance Criteria:**
- Show success toast when dataset fetched successfully
- Show error toast when fetch fails
- Auto-dismiss toasts after 5 seconds
- Include dataset identifier in notification
