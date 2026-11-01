@epic_1 @ui
Feature: Data Source Browsing (UI)
  As a user
  I want to see all available data sources at a glance
  So that I can understand what economic data is accessible

  Background:
    Given the client app is running

  # US-1.1: View Available Data Sources

  @us-1.1
  Scenario: Display sources grid when no sources available
    Given the platform returns no sources
    When I request the sources grid
    Then the response should be HTML
    And the response should contain "No Data Sources Yet"

  @us-1.1
  Scenario: Display sources with dataset counts
    Given the platform returns sources with datasets
    When I request the sources grid
    Then the response should be HTML
    And the response should contain "eurostat"
    And the response should contain "10"

  @us-1.1
  Scenario: Only activated sources are shown
    Given the platform returns multiple sources
    And the source "ons" is deactivated
    When I request the sources grid
    Then the response should be HTML
    And the response should contain "eurostat"
    And the response should not contain "ons"

  # US-1.2: View Source Statistics

  @us-1.2
  Scenario: Source cards show available dataset count
    Given the platform returns sources with datasets
    When I request the sources grid
    Then the response should be HTML
    And the response should contain "available"

  @us-1.2
  Scenario: Source cards show last activity timestamp
    Given the platform returns sources with last activity
    When I request the sources grid
    Then the response should be HTML
    And the response should contain "Last"

  # US-1.1: Click source to filter datasets

  @us-1.1
  Scenario: Source cards have click handler for filtering
    Given the platform returns sources with datasets
    When I request the sources grid
    Then the response should be HTML
    And the response should contain "sourceFilter"
    And the response should contain "initDatasets()"
