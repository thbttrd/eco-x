@epic_5 @ui
Feature: Economic News Aggregation UI
  As a user
  I want to browse curated economic news in a dedicated tab
  So that I can quickly access relevant economic information

  Background:
    Given the client app is running

  # =============================================================================
  # US-5.1: Browse News Sources (SUPERSEDED by US-5.14)
  # NOTE: The original category/source view was replaced by a chronological feed.
  # =============================================================================

  @us-5.1 @superseded
  Scenario: Display news sources organized by category
    # SUPERSEDED: Category view replaced by chronological feed (US-5.14)
    Given news sources exist in the database
    When I navigate to the News tab
    Then I should see sources grouped by category
    And I should see categories like "Central Banks" and "National Statistics"

  @us-5.1 @superseded
  Scenario: Display empty state when no news sources
    # SUPERSEDED: Empty state redesigned for chronological feed
    Given no news sources exist
    When I navigate to the News tab
    Then I should see "No News Sources Yet"

  @us-5.1
  Scenario: Click source opens in new tab
    Given a news source "ECB" exists with URL "https://ecb.europa.eu"
    When I click on the source "ECB"
    Then a new tab should open with URL "https://ecb.europa.eu"

  @us-5.1 @superseded
  Scenario: Display last fetched timestamp per source
    # SUPERSEDED: Source-level timestamps not shown in feed view
    Given a source "ECB" was last fetched "2 hours ago"
    When I view the News tab
    Then I should see "Last updated: 2 hours ago" for source "ECB"

  @us-5.1 @superseded
  Scenario: Display fetch error indicator
    # SUPERSEDED: Source-level errors not shown in feed view
    Given a source "ECB" has last_fetch_status "error"
    When I view the News tab
    Then I should see an error indicator next to "ECB"
    And hovering should show the error message

  # =============================================================================
  # US-5.6: Browse Fetched Articles (PARTIALLY SUPERSEDED)
  # =============================================================================

  @us-5.6 @superseded
  Scenario: Display articles in the News tab
    # SUPERSEDED: Replaced by US-5.14 chronological feed
    Given articles have been fetched from news sources
    When I navigate to the News tab
    Then I should see a list of article headlines
    And each article should show the source name
    And each article should show relative time (e.g., "2 hours ago")

  @us-5.6
  Scenario: Click article opens in new tab
    Given an article "ECB raises rates" with URL "https://ecb.europa.eu/news/1"
    When I click on the article
    Then a new tab should open with the article URL

  @us-5.6
  Scenario: Filter articles by category
    Given articles exist in "Central Banks" and "Press" categories
    When I select "Central Banks" from the category filter
    Then only articles from "Central Banks" sources should be visible

  @us-5.6
  Scenario: Filter articles by time range
    Given articles exist from today and last week
    When I select "Last 24 hours" from the time filter
    Then only articles from the last 24 hours should be visible

  @us-5.6
  Scenario: Search articles by keyword
    Given articles with titles "ECB raises rates" and "Fed holds steady"
    When I search for "ECB"
    Then only "ECB raises rates" should be visible

  @us-5.6 @superseded
  Scenario: Paginate through articles
    # SUPERSEDED: Pagination replaced by infinite scroll (US-5.14)
    Given 50 articles exist
    When I view the News tab
    Then I should see the first 10 articles
    And I should see pagination controls
    When I click "Next"
    Then I should see articles 11-20

  @us-5.6 @superseded
  Scenario: Toggle between sources view and articles view
    # SUPERSEDED: Toggle removed - now feed-only view
    When I view the News tab
    Then I should see a toggle between "Sources" and "Articles"
    When I select "Articles"
    Then I should see the articles feed
    When I select "Sources"
    Then I should see sources grouped by category

  # =============================================================================
  # US-5.7: Article Freshness Indicator (SUPERSEDED)
  # =============================================================================

  @us-5.7 @superseded
  Scenario: Show new articles badge
    # SUPERSEDED: Badge feature not implemented in feed view
    Given 5 new articles have arrived since my last visit
    When I navigate to the News tab
    Then I should see a badge "5 new" on the News tab

  @us-5.7
  Scenario: Clear new articles badge on visit
    Given the News tab shows "5 new" badge
    When I click on the News tab
    Then the badge should disappear
    And new articles should be marked as "seen"

  # =============================================================================
  # US-5.8: Manual Refresh (PARTIALLY SUPERSEDED)
  # =============================================================================

  @us-5.8 @superseded
  Scenario: Refresh all news button
    # SUPERSEDED: Global refresh button removed from feed view
    When I view the News tab
    Then I should see a "Refresh" button
    When I click "Refresh"
    Then I should see a loading indicator
    And the button should be disabled during refresh

  @us-5.8
  Scenario: Refresh single source
    Given I am viewing the sources list
    Then each source should have a refresh icon
    When I click the refresh icon for "ECB"
    Then only "ECB" should show a loading indicator
    And a toast should confirm "Refreshing ECB..."

  @us-5.8
  Scenario: Real-time update during refresh
    Given I am viewing the News tab
    And a refresh is in progress
    When new articles are found
    Then they should appear in the list without page reload
    And a toast should show "3 new articles from ECB"

  @us-5.8
  Scenario: Refresh completes with summary
    Given I triggered a full refresh
    When the refresh completes
    Then a toast should show "Refresh complete: 15 new articles"
    And the loading indicator should disappear

  # =============================================================================
  # Responsive Design
  # =============================================================================

  @ui @responsive @superseded
  Scenario: News tab on mobile
    # SUPERSEDED: Mobile layout redesigned for feed view
    Given the viewport is 375px wide
    When I view the News tab
    Then the layout should be single-column
    And category filters should collapse into a dropdown

  # =============================================================================
  # Error Handling
  # =============================================================================

  @ui @error
  Scenario: Display error when news fetch fails
    Given the news API returns an error
    When I try to load the News tab
    Then I should see an error message
    And I should see a "Retry" button

  @ui @error
  Scenario: Offline indicator
    Given I am viewing the News tab
    When the connection is lost
    Then I should see "Offline - showing cached data"
    And cached articles should still be visible

  # =============================================================================
  # US-5.11: Browse Sections in Collapsible Tree (SUPERSEDED by US-5.14)
  # NOTE: These scenarios are retained for reference but marked as superseded.
  # The tree view has been replaced by a chronological feed (US-5.14).
  # =============================================================================

  @us-5.11 @ui @superseded
  Scenario: News tree displays sources with sections
    # SUPERSEDED: Tree view replaced by chronological feed
    Given the news tab is visible
    And there are sources with sections
    Then each source should show a section count badge
    And sources should be collapsed by default

  @us-5.11 @ui @superseded
  Scenario: Expand source to show sections
    # SUPERSEDED: Tree view replaced by chronological feed
    Given a source "ECB Monetary Policy" has 2 sections
    When I click to expand "ECB Monetary Policy"
    Then I should see the sections listed
    And each section should show an entry count badge

  @us-5.11 @ui @superseded
  Scenario: Entries are displayed as a list of titles
    # SUPERSEDED: Tree view replaced by chronological feed
    Given a section is expanded with entries
    Then entries should be displayed as a list
    And each entry should show its title prominently
    And each entry should show published date
    And clicking an entry title should open full content view

  @us-5.11 @ui @superseded
  Scenario: Expanding section lazy-loads entries
    # SUPERSEDED: Tree view replaced by chronological feed
    Given a collapsed section with entries
    When I click to expand the section
    Then entries should be loaded via htmx
    And a loading indicator should show during fetch

  @us-5.11 @ui @superseded
  Scenario: Section shows fetch status indicator
    # SUPERSEDED: Tree view replaced by chronological feed
    Given a section with last_fetch_status "success"
    Then the section should show a green status indicator
    Given a section with last_fetch_status "error"
    Then the section should show a red status indicator
    And hovering should show the error message

  @us-5.11 @ui @superseded
  Scenario: Tree state persists during session
    # SUPERSEDED: Tree view replaced by chronological feed
    Given I have expanded source "ECB" and section "Decisions"
    When I navigate away and back to the News tab
    Then source "ECB" should still be expanded
    And section "Decisions" should still be expanded

  # =============================================================================
  # US-5.12: View Entry Full Content (SUPERSEDED - now uses panel)
  # NOTE: Modal scenarios replaced by detail panel (US-5.15)
  # =============================================================================

  @us-5.12 @ui @superseded
  Scenario: Clicking entry opens detail modal
    # SUPERSEDED: Modal replaced by detail panel (US-5.15)
    Given a section with entries is expanded
    When I click on an entry title
    Then a modal should open with full entry content
    And the modal should show entry title and source info

  @us-5.12 @ui @superseded
  Scenario: Entry modal displays full content
    # SUPERSEDED: Modal replaced by detail panel (US-5.15)
    Given an entry detail modal is open
    Then I should see the full article text
    And the text should be properly formatted with paragraphs
    And the published date should be displayed

  @us-5.12 @ui @superseded
  Scenario: Entry modal has external link
    # SUPERSEDED: Modal replaced by detail panel (US-5.15)
    Given an entry detail modal is open
    Then there should be an "Open original" link
    And clicking it should open the original URL in new tab

  @us-5.12 @ui @superseded
  Scenario: Close entry modal with Escape key
    # SUPERSEDED: Modal replaced by detail panel (US-5.15)
    Given an entry detail modal is open
    When I press the Escape key
    Then the modal should close
    And focus should return to the entries list

  @us-5.12 @ui @superseded
  Scenario: Close entry modal with click outside
    # SUPERSEDED: Modal replaced by detail panel (US-5.15)
    Given an entry detail modal is open
    When I click outside the modal
    Then the modal should close

  # =============================================================================
  # US-5.13: Section-Level Fetch Status
  # =============================================================================

  @us-5.13 @ui
  Scenario: Refresh single section
    Given a section "Monetary policy decisions" is visible
    When I click the refresh icon for the section
    Then only that section should show a loading indicator
    And a toast should confirm "Refreshing Monetary policy decisions..."

  @us-5.13 @ui @superseded
  Scenario: Section last fetched time is displayed
    # SUPERSEDED: Tree view replaced by chronological feed
    Given a section was last fetched "30 minutes ago"
    Then I should see "Updated 30m ago" for that section

  @us-5.13 @ui
  Scenario: Section error tooltip
    Given a section has a fetch error "Connection timeout"
    When I hover over the error indicator
    Then a tooltip should show "Connection timeout"

  # =============================================================================
  # US-5.14: Browse Chronological News Feed (NEW - Step definitions WIP)
  # =============================================================================

  @us-5.14 @ui @wip
  Scenario: Display chronological news feed
    Given news entries exist from multiple sources
    When I navigate to the News tab
    Then I should see a vertical stack of news cards
    And entries should be sorted by date with newest first
    And entries from all sources should be mixed together

  @us-5.14 @ui @wip
  Scenario: News card displays entry information
    Given a news entry exists with title "ECB raises rates" from source "ECB Monetary Policy"
    When I view the News tab
    Then the card should show the entry title
    And the card should show "ECB Monetary Policy" as the source
    And the card should show relative time like "2 hours ago"

  @us-5.14 @ui @wip
  Scenario: Infinite scroll loads more entries
    Given 50 news entries exist
    When I view the News tab
    Then I should see the first 20 entries
    When I scroll to the bottom of the feed
    Then more entries should load automatically
    And I should see a loading indicator during fetch

  @us-5.14 @ui @wip
  Scenario: Filter feed by category
    Given entries exist in "Central Banks" and "Press" categories
    When I select "Central Banks" from the category filter
    Then only entries from "Central Banks" sources should be visible
    And the filter should be visually indicated as active

  @us-5.14 @ui @wip
  Scenario: Search entries by keyword
    Given entries with titles "ECB raises rates" and "Fed holds steady"
    When I search for "ECB"
    Then only "ECB raises rates" should be visible in the feed

  @us-5.14 @ui @wip
  Scenario: Empty feed state
    Given no news entries exist
    When I navigate to the News tab
    Then I should see "No news yet" message
    And I should see a prompt to refresh news sources

  @us-5.14 @ui @wip
  Scenario: Clicking card selects it and opens panel
    Given news entries exist
    When I click on a news card
    Then the card should be visually highlighted
    And the detail panel should open (see US-5.15)

  # =============================================================================
  # US-5.15: View Entry in Detail Panel (NEW - Step definitions WIP)
  # =============================================================================

  @us-5.15 @ui @wip
  Scenario: Detail panel opens when entry is selected
    Given news entries exist
    When I click on a news card
    Then a detail panel should slide in from the right
    And the panel should display the full entry content

  @us-5.15 @ui @wip
  Scenario: Detail panel displays entry information
    Given an entry is selected and the panel is open
    Then I should see the entry title in the panel header
    And I should see the source name and section name
    And I should see the published date
    And I should see the full article content with proper formatting

  @us-5.15 @ui @wip
  Scenario: Detail panel has external link
    Given an entry is selected and the panel is open
    Then there should be an "Open original" link
    And clicking it should open the original URL in new tab

  @us-5.15 @ui @wip
  Scenario: Close detail panel with close button
    Given the detail panel is open
    When I click the close button (X)
    Then the panel should slide out to the right
    And the selected card should no longer be highlighted

  @us-5.15 @ui @wip
  Scenario: Close detail panel with Escape key
    Given the detail panel is open
    When I press the Escape key
    Then the panel should close

  @us-5.15 @ui @wip
  Scenario: Close detail panel by clicking outside
    Given the detail panel is open
    When I click on the feed area (outside the panel)
    Then the panel should close

  @us-5.15 @ui @wip
  Scenario: Navigate between entries with keyboard
    Given the detail panel is open showing entry 1
    When I press the Down arrow key
    Then the panel should show entry 2
    And entry 2 should be highlighted in the feed
    When I press the Up arrow key
    Then the panel should show entry 1

  @us-5.15 @ui @responsive @wip
  Scenario: Detail panel on mobile becomes full-screen
    Given the viewport is 375px wide
    And the detail panel is open
    Then the panel should cover the full screen
    And there should be a back button to close

  # =============================================================================
  # US-5.16: News Feed Loading States (NEW - Step definitions WIP)
  # =============================================================================

  @us-5.16 @ui @wip
  Scenario: Initial feed loading shows skeleton
    Given news entries exist
    When the News tab is loading
    Then I should see skeleton placeholder cards
    And the skeletons should have a pulse animation

  @us-5.16 @ui @wip
  Scenario: Infinite scroll loading indicator
    Given I am scrolling through the feed
    When more entries are being loaded
    Then I should see "Loading more..." at the bottom
    When loading completes
    Then the indicator should disappear and new cards should appear

  @us-5.16 @ui @wip
  Scenario: Panel loading shows skeleton
    Given I click on a news card
    When the entry details are being fetched
    Then the panel should show a content skeleton
    When loading completes
    Then the full content should replace the skeleton

  @us-5.16 @ui @wip
  Scenario: Feed error state
    Given the news API returns an error
    When I try to load the News tab
    Then I should see "Failed to load news" message
    And I should see a "Retry" button

  @us-5.16 @ui @wip
  Scenario: Empty state after filtering
    Given entries exist but none match the filter
    When I apply a category filter that has no entries
    Then I should see "No entries match your filters"
    And I should see a "Clear filters" option
