# Epic 11: Internationalization (i18n)

## Overview

Provide multi-language support with language switching and extensible translation system.

**Package:** ecox-client
**Feature File:** `epic11_internationalization.feature`

---

## User Stories

### US-11.1: Switch Application Language

**As a** user
**I want to** switch the application language between English and French
**So that** I can use the platform in my preferred language

**Acceptance Criteria:**
- Display language switcher dropdown in the header (right side, next to connection status)
- Support English (EN) and French (FR) languages
- Language selection updates all UI text immediately without page reload (htmx partial swap)
- Current language indicated in the switcher (e.g., "EN" or "FR")
- Language preference persists via cookie (1 year expiry)
- URL parameter `?lang=fr` overrides cookie for shareable links
- Default language is English if no preference set

---

### US-11.2: Translate User Interface

**As a** user
**I want to** see all interface text in my selected language
**So that** I can fully understand and use the application

**Acceptance Criteria:**
- All navigation tabs translated (Data Sources, Datasets, News)
- All button labels translated (Add Data Source, View Details, etc.)
- All table headers translated (Source, Code, Name, Status, Last Fetched)
- All filter labels and options translated
- All empty state messages translated
- All modal content translated
- All error messages translated
- All status indicators translated (Connecting, Live, Disconnected)
- Pagination text translated (Page X of Y, Previous, Next)
- Toast notifications translated

---

### US-11.3: Extensible Language System

**As a** developer
**I want to** easily add new languages to the application
**So that** the platform can support additional locales

**Acceptance Criteria:**
- Translation files stored in YAML format in `/locales/` directory
- Each language has its own file (e.g., `en.yaml`, `fr.yaml`)
- Translations organized by section with dot-notation keys (e.g., `nav.datasets`)
- Adding new language requires: 1) Create YAML file, 2) Add to supported list, 3) Add UI option
- Missing translations fall back to English (default language)
- Translation keys visible in UI if translation missing (for debugging)
- Supported languages defined in single configuration constant

---

### US-11.4: Client-Side Translations

**As a** user
**I want to** see dynamic content (toasts, status updates) in my language
**So that** the entire experience is localized

**Acceptance Criteria:**
- JavaScript has access to translations via `window.i18n` object
- Connection status messages translated (Connecting, Live, Disconnected)
- Toast notifications display in selected language
- SSE event messages translated
- Loading indicators translated
