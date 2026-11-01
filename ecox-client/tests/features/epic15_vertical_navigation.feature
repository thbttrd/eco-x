@epic_15 @ui
Feature: Vertical Navigation Panel
  As a user
  I want a vertical navigation sidebar
  So that I can easily switch between application sections with better visual hierarchy

  Background:
    Given the web application is running
    And I am on the main page

  # US-15.1: Vertical Navigation Sidebar
  @us-15.1
  Scenario: Sidebar displays all navigation sections
    Then I should see a vertical navigation sidebar on the left
    And the sidebar should contain a "Sources" navigation item with a database icon
    And the sidebar should contain a "Datasets" navigation item with an archive icon
    And the sidebar should contain a "News" navigation item with a newspaper icon

  @us-15.1
  Scenario: Active section is highlighted
    When I click on "Datasets" in the sidebar
    Then the "Datasets" navigation item should have an active indicator
    And the "Sources" navigation item should not have an active indicator
    And the main content area should show the Datasets section

  @us-15.1
  Scenario: Sidebar supports dark mode
    Given dark mode is enabled
    Then the sidebar should have dark mode styling
    And the active indicator should remain visible in dark mode

  # US-15.2: Sidebar Expand/Collapse
  @us-15.2
  Scenario: Toggle sidebar expanded state
    Given the sidebar is expanded
    When I click the sidebar toggle button
    Then the sidebar should collapse to icon-only mode
    And the navigation labels should be hidden

  @us-15.2
  Scenario: Collapsed sidebar shows icons only
    Given the sidebar is collapsed
    Then I should see navigation icons
    And I should not see navigation labels

  @us-15.2
  Scenario: Sidebar state persists across page refresh
    Given the sidebar is collapsed
    When I refresh the page
    Then the sidebar should still be collapsed

  # US-15.3: Sidebar Hover Expansion
  @us-15.3
  Scenario: Collapsed sidebar expands on hover
    Given the sidebar is collapsed
    When I hover over the sidebar
    Then the sidebar should expand temporarily
    And I should see navigation labels

  @us-15.3
  Scenario: Sidebar collapses when mouse leaves
    Given the sidebar is collapsed
    And I am hovering over the sidebar
    When I move the mouse away from the sidebar
    Then the sidebar should collapse back to icon-only mode

  # US-15.4: Navigation State Persistence
  @us-15.4
  Scenario: URL updates when navigating
    When I click on "News" in the sidebar
    Then the URL should contain "?tab=news"

  @us-15.4
  Scenario: Active section restored from URL
    Given I navigate to the page with "?tab=datasets" in the URL
    Then the "Datasets" navigation item should be active
    And the main content area should show the Datasets section

  @us-15.4
  Scenario: Default to Sources when no tab parameter
    Given I navigate to the page without a tab parameter
    Then the "Sources" navigation item should be active

  # US-15.5: Mobile Navigation
  @us-15.5 @mobile
  Scenario: Bottom navigation on mobile
    Given I am viewing on a mobile device
    Then I should not see the vertical sidebar
    And I should see a bottom navigation bar
    And the bottom nav should contain Sources, Datasets, and News items

  @us-15.5 @mobile
  Scenario: Mobile navigation highlights active section
    Given I am viewing on a mobile device
    When I tap on "News" in the bottom navigation
    Then the "News" item in the bottom nav should be highlighted
    And the main content area should show the News section

  # US-15.6: Keyboard Navigation
  @us-15.6 @accessibility
  Scenario: Tab key cycles through navigation items
    When I press Tab to focus the sidebar
    And I press Tab repeatedly
    Then focus should cycle through Sources, Datasets, and News items

  @us-15.6 @accessibility
  Scenario: Enter key activates navigation item
    Given "Datasets" navigation item is focused
    When I press Enter
    Then the "Datasets" section should be activated
    And the main content area should show the Datasets section

  @us-15.6 @accessibility
  Scenario: Arrow keys navigate within sidebar
    Given "Sources" navigation item is focused
    When I press Arrow Down
    Then "Datasets" navigation item should be focused

  @us-15.6 @accessibility
  Scenario: Visible focus indicator
    When I use keyboard to navigate to the sidebar
    Then the focused item should have a visible focus ring

  # US-15.7: Updated Layout Structure
  @us-15.7
  Scenario: Layout structure with sidebar
    Then the header should span full width at the top
    And the sidebar should be positioned below the header
    And the main content area should fill the space to the right of the sidebar

  @us-15.7
  Scenario: Content area scrolls independently
    Given I am viewing a section with scrollable content
    When I scroll the content area
    Then the sidebar should remain fixed in place
    And the header should remain fixed in place
