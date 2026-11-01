@epic_6 @api
Feature: Eurostat Data Fetching
  As a user
  I want to fetch economic data from Eurostat
  So that I can analyze EU economic statistics

  Background:
    Given the database is initialized

  # US-6.1: Fetch Eurostat Dataset (data storage verification)
  @us-6.1
  Scenario: Store Eurostat dataset values with dimensions
    Given a dataset "nama_10_gdp" exists from "eurostat"
    When I store eurostat data values for the dataset
    Then the data values should be persisted in the database
    And the data values should include geo, time, and indicator dimensions

  @us-6.1
  Scenario: Log Eurostat fetch operation
    Given a dataset "nama_10_gdp" exists from "eurostat"
    When a successful fetch is logged for the dataset
    Then a fetch log should be recorded
    And the fetch log status should be "success"

  # US-6.2: Eurostat Table of Contents (cached metadata)
  @us-6.2
  Scenario: Store Eurostat source metadata
    Given source "eurostat" has 12000 total available datasets
    When I request the list of data sources
    Then the response status should be 200
    And the source "eurostat" should show total available datasets

  @us-6.2
  Scenario: Eurostat source appears in sources list
    When I request the list of data sources
    Then the response status should be 200
    And the source "eurostat" should be in the response
