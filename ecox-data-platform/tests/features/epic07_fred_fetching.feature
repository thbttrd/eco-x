@epic_7 @api
Feature: FRED Data Fetching
  As a user
  I want to fetch economic data from FRED
  So that I can analyze US economic indicators

  Background:
    Given the database is initialized

  # US-7.1: Fetch FRED Series (data storage verification)
  @us-7.1
  Scenario: Store FRED series values
    Given a dataset "GDP" exists from "fred"
    When I store fred data values for the dataset
    Then the data values should be persisted in the database
    And the data values should include time and value

  @us-7.1
  Scenario: Log FRED fetch operation
    Given a dataset "GDP" exists from "fred"
    When a successful fetch is logged for the dataset
    Then a fetch log should be recorded
    And the fetch log status should be "success"

  @us-7.1
  Scenario: FRED source appears in sources list
    When I request the list of data sources
    Then the response status should be 200
    And the source "fred" should be in the response
