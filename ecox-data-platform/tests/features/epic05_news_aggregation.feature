@epic_5 @api
Feature: Economic News Aggregation
  As a user
  I want economic news to be automatically fetched and parsed
  So that I can browse current economic news without visiting each source

  Background:
    Given the database is initialized

  # US-5.2: Configure News Sources

  @us-5.2
  Scenario: News configuration includes parse selectors
    Given a news source configuration with parse_selector "article.news a"
    Then the source config should have a parse_selector field
    And the source config should have a parse_comment field

  @us-5.2
  Scenario: News sources can be imported from config
    Given a news configuration file with 3 categories and 10 sources
    When I call the news import endpoint
    Then the database should contain 3 news categories
    And the database should contain 10 news sources

  @us-5.2
  Scenario: Re-importing config updates existing sources
    Given a news source "ECB" already exists in the database
    And the config file has an updated URL for "ECB"
    When I call the news import endpoint
    Then the "ECB" source URL should be updated
    And no duplicate sources should exist

  # US-5.3: Configure Fetch Interval

  @us-5.3
  Scenario: Global default fetch interval
    Given a news configuration with default_fetch_interval_minutes 60
    Then all sources without explicit interval should use 60 minutes

  @us-5.3
  Scenario: Category-level fetch interval override
    Given a news configuration with default_fetch_interval_minutes 60
    And category "Central Banks" has fetch_interval_minutes 30
    Then sources in "Central Banks" should use 30 minutes interval
    And sources in other categories should use 60 minutes interval

  @us-5.3
  Scenario: Source-level fetch interval override
    Given category "Central Banks" has fetch_interval_minutes 30
    And source "ECB" has fetch_interval_minutes 15
    Then source "ECB" should use 15 minutes interval
    And other sources in "Central Banks" should use 30 minutes interval

  @us-5.3
  Scenario: Minimum fetch interval enforced
    Given a source with fetch_interval_minutes 5
    Then the effective interval should be at least 15 minutes

  @us-5.3
  Scenario: Maximum fetch interval enforced
    Given a source with fetch_interval_minutes 2000
    Then the effective interval should be at most 1440 minutes

  @us-5.3
  Scenario: Environment variable overrides config
    Given the environment variable ECOX_NEWS_FETCH_INTERVAL_MINUTES is set to 45
    Then all sources should use 45 minutes as the base interval

  # US-5.4: Automatic News Fetching

  @us-5.4
  Scenario: Fetch runs on startup
    Given news fetch on startup is enabled
    When the application starts
    Then a news fetch task should be scheduled after startup delay

  @us-5.4
  Scenario: Concurrent fetch limit respected
    Given max_concurrent_fetches is set to 3
    And there are 10 sources to fetch
    When the news fetch runs
    Then at most 3 sources should be fetched concurrently

  @us-5.4
  Scenario: Rate limiting per domain
    Given rate_limit_per_domain is set to 2.0
    And there are 5 sources from the same domain
    When fetching those sources
    Then requests to that domain should not exceed 2 per second

  @us-5.4
  Scenario: Unreachable source is skipped gracefully
    Given a source "ECB" that returns HTTP 503
    When the news fetch runs
    Then the fetch should continue with other sources
    And source "ECB" should be marked with error status
    And the error should be logged

  @us-5.4
  Scenario: SSE notification on new articles
    Given SSE connection is established
    When the news fetch finds 5 new articles from "ECB"
    Then an SSE event "news-fetch-completed" should be sent
    And the event should contain articles_new = 5

  # US-5.5: News Article Parsing

  @us-5.5
  Scenario: Parse articles using CSS selector
    Given a source with parse_selector "article.item a"
    And the source page contains 10 matching links
    When the source is fetched
    Then 10 articles should be extracted

  @us-5.5
  Scenario: Parse articles using XPath
    Given a source with parse_selector "xpath://div[@class='news']//a"
    And the source page contains 5 matching links
    When the source is fetched
    Then 5 articles should be extracted

  @us-5.5
  Scenario: RSS feed fallback when no selector configured
    Given a source with no parse_selector
    And the source page has an RSS feed link
    When the source is fetched
    Then articles should be extracted from the RSS feed

  @us-5.5
  Scenario: Link extraction fallback
    Given a source with no parse_selector
    And the source page has no RSS feed
    When the source is fetched
    Then articles should be extracted from main content links

  @us-5.5
  Scenario: Duplicate articles are skipped
    Given an article with URL "https://example.com/news/1" already exists
    When fetching a source that contains the same URL
    Then the article should not be duplicated
    And articles_new should not include the duplicate

  @us-5.5
  Scenario: Article published date extraction
    Given a parsed article with date in the link text "Dec 20, 2025"
    Then the article published_at should be "2025-12-20"

  @us-5.5
  Scenario: Store raw HTML for debugging
    Given store_raw_html is enabled
    When a source is fetched
    Then the raw HTML should be stored in the fetch log

  # US-5.7: Article Freshness Indicator

  @us-5.7
  Scenario: Last fetched timestamp updated on success
    Given a source "ECB" with last_fetched_at "2025-12-20 10:00:00"
    When the source is successfully fetched at "2025-12-21 09:00:00"
    Then last_fetched_at should be "2025-12-21 09:00:00"
    And last_checked_at should be "2025-12-21 09:00:00"

  @us-5.7
  Scenario: Last checked updated on failure
    Given a source "ECB" with last_fetched_at "2025-12-20 10:00:00"
    When the source fetch fails at "2025-12-21 09:00:00"
    Then last_fetched_at should remain "2025-12-20 10:00:00"
    And last_checked_at should be "2025-12-21 09:00:00"
    And last_fetch_status should be "error"

  # US-5.8: Manual Refresh

  @us-5.8
  Scenario: Manual refresh all sources
    Given there are 5 news sources configured
    When I POST to /api/news/refresh
    Then all 5 sources should be queued for fetch
    And the response should indicate refresh started

  @us-5.8
  Scenario: Manual refresh single source
    Given a news source "ECB" with id 42
    When I POST to /api/news/refresh/42
    Then only source "ECB" should be fetched
    And other sources should not be affected

  @us-5.8
  Scenario: Refresh status endpoint
    Given a news refresh is in progress
    When I GET /api/news/status
    Then the response should show status "running"
    And the response should show progress (e.g., "3/10 sources completed")

  @us-5.8
  Scenario: Prevent concurrent refresh
    Given a news refresh is already running
    When I POST to /api/news/refresh
    Then the response should indicate refresh already in progress
    And a new refresh should not be started

  # API Endpoints

  @api
  Scenario: GET /api/news returns sources with articles
    Given news sources exist with fetched articles
    When I GET /api/news
    Then the response should contain sources grouped by category
    And each source should include latest articles

  @api
  Scenario: GET /api/news/articles with pagination
    Given 50 news articles exist
    When I GET /api/news/articles?page=1&per_page=10
    Then the response should contain 10 articles
    And the response should include pagination metadata

  @api
  Scenario: GET /api/news/articles with category filter
    Given articles exist in categories "Central Banks" and "Press"
    When I GET /api/news/articles?category=Central%20Banks
    Then only articles from "Central Banks" should be returned

  @api
  Scenario: GET /api/news/articles with time filter
    Given articles exist from various dates
    When I GET /api/news/articles?since=24h
    Then only articles from the last 24 hours should be returned

  @api
  Scenario: GET /api/news/articles with search
    Given articles exist with various titles
    When I GET /api/news/articles?search=inflation
    Then only articles with "inflation" in the title should be returned

  # US-5.9: Define News Sections

  @us-5.9
  Scenario: News source can have multiple sections
    Given a news source "ECB Monetary Policy" exists
    And the source has sections:
      | title                      | url                                                    |
      | Monetary policy decisions  | https://www.ecb.europa.eu/press/govcdec/mopo/html/... |
      | Monetary policy statements | https://www.ecb.europa.eu/press/press_conference/...  |
    When I fetch sections for source "ECB Monetary Policy"
    Then I should receive 2 sections

  @us-5.9
  Scenario: Section inherits parse_selector from source if not specified
    Given a news source with parse_selector "main a"
    And a section without parse_selector
    Then the section should use parse_selector "main a"

  @us-5.9
  Scenario: Sections can be individually disabled
    Given a news source with 3 sections
    And section "Archives" is disabled
    When the news fetch runs
    Then only 2 sections should be fetched

  @us-5.9
  Scenario: Import config with hierarchical sections
    Given a news configuration with sections under sources
    When I call the news import endpoint
    Then the database should contain news sections
    And each section should be linked to its source

  # US-5.10: Fetch Full Entry Content

  @us-5.10
  Scenario: Entry content is fully fetched and stored
    Given a section with an entry URL pointing to article content
    When the section is fetched
    Then the entry should have content_full populated
    And the content_preview should be first 500 chars of content_full

  @us-5.10
  Scenario: Content extraction removes navigation and scripts
    Given an article page with nav, header, footer, and main content
    When content is extracted
    Then the result should contain only main article text
    And should not contain navigation elements

  @us-5.10
  Scenario: Failed content extraction is handled gracefully
    Given an entry URL that returns 404
    When content extraction is attempted
    Then content_full should be null
    And the error should be logged
    And other entries should continue processing

  @us-5.10
  Scenario: Content extraction uses heuristics
    Given an article page with article tag containing main content
    When content is extracted
    Then the result should come from the article tag
    And should exclude header and footer within the article

  # US-5.11: Browse Sections in Collapsible Tree

  @us-5.11
  Scenario: API returns hierarchical category-source-section structure
    Given categories with sources and sections exist
    When I call GET /api/news/categories
    Then the response should include sources nested under categories
    And sources should include their sections
    And each level should include counts

  @us-5.11
  Scenario: Get sections for a source
    Given a source "ECB" with 3 sections
    When I call GET /api/news/sources/{source_id}/sections
    Then I should receive 3 sections
    And each section should include entry count

  @us-5.11
  Scenario: Get entries for a section
    Given a section "Monetary policy decisions" with 10 entries
    When I call GET /api/news/sections/{section_id}/entries
    Then I should receive paginated entries
    And each entry should include title, published_at, and has_content flag

  # US-5.12: View Entry Full Content

  @us-5.12
  Scenario: Get entry with full content
    Given an entry exists with full content
    When I call GET /api/news/entries/{entry_id}
    Then the response should include content_full
    And the response should include section and source info

  @us-5.12
  Scenario: Entry not found returns 404
    Given no entry with ID 99999 exists
    When I call GET /api/news/entries/99999
    Then the response status should be 404
    And the response should include an error message

  @us-5.12
  Scenario: Entry response includes metadata
    Given an entry with published_at and discovered_at
    When I call GET /api/news/entries/{entry_id}
    Then the response should include published_at
    And the response should include discovered_at
    And the response should include the original URL

  # US-5.13: Section-Level Fetch Status

  @us-5.13
  Scenario: Section status is updated after successful fetch
    Given a section "Monetary policy decisions" exists
    When the section is fetched successfully with 5 new entries
    Then section last_fetched_at should be updated
    And section last_fetch_status should be "success"

  @us-5.13
  Scenario: Section status shows error on failure
    Given a section with an unreachable URL
    When the section fetch is attempted
    Then section last_fetch_status should be "error"
    And section last_fetch_error should contain error details

  @us-5.13
  Scenario: Manual section refresh via API
    Given a section "Monetary policy decisions" exists
    When I call POST /api/news/sections/{id}/refresh
    Then the section should be fetched immediately
    And the response should include fetch result

  @us-5.13
  Scenario: Fetch log includes section reference
    Given a section fetch completes
    Then the fetch log should include section_id
    And the fetch log should include entries_found and entries_new
