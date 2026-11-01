@epic_2 @api
Feature: Dataset Discovery & Browsing
  As a user
  I want to discover and browse datasets from multiple sources
  So that I can find and work with economic data

  Background:
    Given the database is initialized

  # US-2.1: Browse All Datasets
  @us-2.1
  Scenario: Browse all datasets with pagination
    Given there are 25 datasets from "eurostat" in the database
    When I request all datasets
    Then the response status should be 200
    And the response should include pagination info

  @us-2.1
  Scenario: Browse datasets from specific source
    Given there are 10 datasets from "eurostat" in the database
    And there are 5 datasets from "fred" in the database
    When I request datasets from "eurostat"
    Then the response status should be 200
    And all datasets should be from source "eurostat"

  # US-2.2: View Dataset Details
  @us-2.2
  Scenario: View dataset details
    Given a dataset "GDP" exists from "eurostat"
    When I request dataset details for "eurostat/GDP"
    Then the response status should be 200
    And the response should contain dataset code "GDP"
    And the response should contain source "eurostat"

  @us-2.2
  Scenario: View non-existent dataset returns 404
    When I request dataset details for "eurostat/NONEXISTENT"
    Then the response status should be 404

  # US-2.3: Identify Dataset Status (tested via response format)
  @us-2.3
  Scenario: Downloaded datasets have status field
    Given a dataset "GDP" exists from "eurostat"
    When I request datasets from "eurostat"
    Then the response status should be 200
    And the dataset "GDP" should have a status field

  # US-2.4: Search Datasets
  @us-2.4
  Scenario: Search datasets by code
    Given a dataset "GDP_MAIN" with name "Gross Domestic Product" exists from "eurostat"
    And a dataset "CPI_MONTHLY" with name "Consumer Price Index" exists from "eurostat"
    When I search datasets with query "GDP"
    Then the response status should be 200
    And the dataset "GDP_MAIN" should be in the response
    And the dataset "CPI_MONTHLY" should not be in the response

  @us-2.4
  Scenario: Search datasets by name
    Given a dataset "NAM_GDP" with name "National Accounts GDP" exists from "eurostat"
    And a dataset "PRICE_CPI" with name "Price Consumer Index" exists from "eurostat"
    When I search datasets with query "National"
    Then the response status should be 200
    And the dataset "NAM_GDP" should be in the response

  @us-2.4
  Scenario: Search with no results
    Given a dataset "GDP" exists from "eurostat"
    When I search datasets with query "NONEXISTENT"
    Then the response status should be 200
    And the response should be empty

  # US-2.5: Filter Datasets by Status
  @us-2.5
  Scenario: Filter datasets by downloaded status
    Given a dataset "GDP" exists from "eurostat"
    When I filter datasets by status "downloaded"
    Then the response status should be 200

  # US-2.6: Filter Datasets by Source
  @us-2.6
  Scenario: Filter datasets by source
    Given there are 5 datasets from "eurostat" in the database
    And there are 3 datasets from "fred" in the database
    When I request datasets from "fred"
    Then the response status should be 200
    And all datasets should be from source "fred"

  # US-2.7: Combined Filtering
  @us-2.7
  Scenario: Combine search with source filter
    Given a dataset "GDP" with name "Gross Domestic Product" exists from "eurostat"
    And a dataset "GDP" with name "Gross Domestic Product" exists from "fred"
    When I search datasets from "eurostat" with query "GDP"
    Then the response status should be 200
    And all datasets should be from source "eurostat"

  # Note: US-2.8 (Download) and US-2.9 (Purge) are more integration-focused
  # and may require mock HTTP clients for external API calls

  # US-2.10: View Original Source Link
  @us-2.10
  Scenario: API returns source_url for Eurostat dataset
    Given a dataset "nama_10_gdp" exists from "eurostat"
    When I request dataset details for "eurostat/nama_10_gdp"
    Then the response status should be 200
    And the response should contain "source_url"

  @us-2.10
  Scenario: API returns source_url for FRED dataset
    Given a dataset "GDP" exists from "fred"
    When I request dataset details for "fred/GDP"
    Then the response status should be 200
    And the response should contain "source_url"

  @us-2.10
  Scenario: API computes source_url for dataset without stored URL
    Given a dataset "old_dataset" exists from "ons" without source_url
    When I request dataset details for "ons/old_dataset"
    Then the response status should be 200
    And the response should contain "source_url"
