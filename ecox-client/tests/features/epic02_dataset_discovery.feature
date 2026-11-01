@epic_2 @ui
Feature: Dataset Discovery & Browsing (UI)
  As a user
  I want to browse and search datasets in a unified view
  So that I can find data across multiple sources

  Background:
    Given the client app is running

  # US-2.1: Browse All Datasets

  @us-2.1
  Scenario: Display empty state when no datasets
    Given the platform returns no datasets
    When I request the datasets table
    Then the response should be HTML
    And the response should contain "No Datasets Found"

  @us-2.1
  Scenario: Display datasets in table format
    Given the platform returns datasets
    When I request the datasets table
    Then the response should be HTML
    And the response should contain "nama_10_gdp"
    And the response should contain "GDP"

  @us-2.1
  Scenario: Filter datasets by source
    Given the platform returns datasets
    When I request datasets for source "eurostat"
    Then the response should be HTML

  # US-2.2: View Dataset Details

  @us-2.2
  Scenario: Display dataset detail modal
    Given the platform returns a dataset detail
    When I request dataset detail for "eurostat/nama_10_gdp"
    Then the response should be HTML
    And the response should contain "nama_10_gdp"
    And the response should contain "GDP and main components"

  # US-2.1: Pagination

  @us-2.1
  Scenario: Pagination controls are in table header
    Given the platform returns datasets
    When I request the datasets page
    Then the response should be HTML
    And the response should contain "prevPage()"
    And the response should contain "nextPage()"
    And the response should contain "Header with Pagination"

  # US-2.4: Search Datasets

  @us-2.4
  Scenario: Search datasets by query
    Given the platform returns datasets
    When I search datasets with query "gdp"
    Then the response should be HTML

  # US-2.10: View Original Source Link

  @us-2.10
  Scenario: Display source URL in dataset detail modal
    Given the platform returns a dataset detail with source_url
    When I request dataset detail for "eurostat/nama_10_gdp"
    Then the response should be HTML
    And the response should contain "Original Source"
    And the response should contain "View on source website"

  @us-2.10
  Scenario: Source URL opens in new tab
    Given the platform returns a dataset detail with source_url
    When I request dataset detail for "fred/GDP"
    Then the response should be HTML
    And the response should contain "_blank"
    And the response should contain "noopener noreferrer"
