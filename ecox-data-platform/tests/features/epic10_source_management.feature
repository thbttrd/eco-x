@epic_10 @api
Feature: Data Source Management
  As a user
  I want to manage data sources
  So that I can control which sources appear in the app

  Background:
    Given the database is initialized

  # US-10.3: Data Source Catalog API (existing implementation)
  @us-10.3
  Scenario: Get list of available data sources
    When I request the list of data sources
    Then the response status should be 200
    And the response should contain configured sources

  @us-10.3
  Scenario: Each source includes metadata
    When I request the list of data sources
    Then the response status should be 200
    And each source should have code, name, and description

  @us-10.3
  Scenario: Get specific source status
    When I request source status for "eurostat"
    Then the response status should be 200
    And the response should contain source "eurostat"

  @us-10.3
  Scenario: Unknown source returns 404
    When I request source status for "unknown_source"
    Then the response status should be 404

  @us-10.3
  Scenario: Source status includes worker information
    When I request source status for "eurostat"
    Then the response status should be 200
    And the response should include worker status
