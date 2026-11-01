@epic_9 @api
Feature: Data Storage & History
  As a user
  I want downloaded data stored locally and fetch history tracked
  So that I can access data offline and understand data freshness

  Background:
    Given the database is initialized

  # US-9.1: Store Economic Data
  @us-9.1
  Scenario: Store data values with all dimensions
    Given a dataset "GDP" exists from "eurostat"
    When I store data values for the dataset
    Then the data values should be persisted in the database
    And the data values should include geo, time, and indicator dimensions

  @us-9.1
  Scenario: Store dataset metadata
    Given a dataset "GDP" exists from "eurostat"
    When I update the dataset metadata
    Then the dataset metadata should be persisted
    And the metadata should include last updated timestamp

  @us-9.1
  Scenario: Support multiple sources in same database
    Given there are 3 datasets from "eurostat" in the database
    And there are 2 datasets from "fred" in the database
    When I request all datasets
    Then the response status should be 200
    And the response should have 5 items

  # US-9.2: Track Fetch History
  @us-9.2
  Scenario: Log successful fetch operation
    Given a dataset "GDP" exists from "eurostat"
    When a successful fetch is logged for the dataset
    Then a fetch log should be recorded
    And the fetch log status should be "success"
    And the fetch log should include records count

  @us-9.2
  Scenario: Log failed fetch operation with error message
    Given a dataset "CPI" exists from "eurostat"
    When a failed fetch is logged for the dataset with error "Connection timeout"
    Then a fetch log should be recorded
    And the fetch log status should be "error"
    And the fetch log error message should be "Connection timeout"

  @us-9.2
  Scenario: Track fetch duration
    Given a dataset "GDP" exists from "fred"
    When a fetch is logged with duration 2.5 seconds
    Then the fetch log should record duration 2.5 seconds
