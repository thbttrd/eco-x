@epic_1 @api
Feature: Data Source Browsing
  As a user
  I want to see all available data sources at a glance
  So that I can understand what economic data is accessible

  Background:
    Given the database is initialized

  # US-1.1: View Available Data Sources
  @us-1.1
  Scenario: List all available data sources with no data
    Given the database is empty
    When I request the list of data sources
    Then the response status should be 200
    And the response should be successful

  @us-1.1
  Scenario: List data sources with downloaded datasets
    Given there are 10 datasets from "eurostat" in the database
    And there are 5 datasets from "fred" in the database
    When I request the list of data sources
    Then the response status should be 200
    And the source "eurostat" should have 10 datasets
    And the source "fred" should have 5 datasets

  @us-1.1
  Scenario: All configured sources appear in listing
    Given the database is empty
    When I request the list of data sources
    Then the response status should be 200
    And the source "eurostat" should be in the response
    And the source "fred" should be in the response

  # US-1.2: View Source Statistics
  @us-1.2
  Scenario: View source with downloaded and available counts
    Given there are 25 datasets from "eurostat" in the database
    And source "eurostat" has 12000 total available datasets
    When I request the list of data sources
    Then the response status should be 200
    And the source "eurostat" should show 25 of 12000 datasets

  @us-1.2
  Scenario: Source with no downloaded datasets
    Given source "fred" has 500000 total available datasets
    When I request the list of data sources
    Then the response status should be 200
    And the source "fred" should have 0 datasets
