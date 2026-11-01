@epic_4 @api
Feature: Automatic Data Refresh
  As an administrator
  I want datasets to refresh automatically based on configuration
  So that critical data stays up-to-date

  Background:
    Given the database is initialized

  # US-4.1: Configure Dataset Refresh

  @us-4.1
  Scenario: Source configuration includes refresh settings
    Given a source configuration for "eurostat"
    Then the source config should have a refresh_hours setting
    And the source config should have an enabled setting
    And the source config should have a rate_limit setting

  @us-4.1
  Scenario: Different sources can have different refresh intervals
    Given a source configuration for "eurostat" with refresh_hours 24
    And a source configuration for "fred" with refresh_hours 12
    Then the eurostat refresh interval should be 24 hours
    And the fred refresh interval should be 12 hours

  @us-4.1
  Scenario: Source can be disabled via configuration
    Given a source configuration for "eurostat" with enabled false
    Then the eurostat source should be disabled

  # US-4.2: Startup Refresh

  @us-4.2
  Scenario: Dataset freshness is determined by last_fetched time
    Given the database is empty
    And a dataset "GDP" from "eurostat" exists with last_fetched 48 hours ago
    When I check if the dataset needs refresh with max_age 24 hours
    Then the dataset should be marked as stale

  @us-4.2
  Scenario: Fresh dataset does not need refresh
    Given the database is empty
    And a dataset "GDP" from "eurostat" exists with last_fetched 6 hours ago
    When I check if the dataset needs refresh with max_age 24 hours
    Then the dataset should be marked as fresh

  # US-4.3: Smart Refresh Using Source Metadata

  @us-4.3
  Scenario: Skip fetch when source last_update unchanged
    Given the database is empty
    And a dataset "GDP" from "eurostat" exists with source_last_update "14.12.2024"
    And the TOC metadata shows last_update "14.12.2024" for dataset "GDP"
    When the smart refresh check runs for "eurostat"
    Then the dataset "GDP" should be marked as unchanged
    And the dataset "GDP" should not be queued for fetch

  @us-4.3
  Scenario: Fetch when source last_update has changed
    Given the database is empty
    And a dataset "GDP" from "eurostat" exists with source_last_update "14.12.2024"
    And the TOC metadata shows last_update "15.12.2024" for dataset "GDP"
    When the smart refresh check runs for "eurostat"
    Then the dataset "GDP" should be marked as stale
    And the dataset "GDP" should be queued for fetch

  @us-4.3
  Scenario: Prioritize new datasets over stale datasets
    Given the database is empty
    And a dataset "GDP" from "eurostat" exists with source_last_update "14.12.2024"
    And the TOC metadata shows last_update "15.12.2024" for dataset "GDP"
    And the TOC metadata shows a new dataset "CPI" with last_update "01.12.2024"
    When the smart refresh check runs for "eurostat"
    Then the dataset "CPI" should be queued before "GDP"

  @us-4.3
  Scenario: Smart refresh works for FRED datasets
    Given the database is empty
    And a dataset "GDP" from "fred" exists with source_last_update "2024-12-14"
    And the TOC metadata shows last_update "2024-12-14" for dataset "GDP"
    When the smart refresh check runs for "fred"
    Then the dataset "GDP" should be marked as unchanged
