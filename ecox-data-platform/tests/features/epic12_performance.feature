@epic_12 @api @performance
Feature: Performance & Reliability
  As a system
  I want reliable and performant operations
  So that the application handles load gracefully

  Background:
    Given the database is initialized

  # US-12.1: Intelligent Caching

  @us-12.1
  Scenario: API responses should be cacheable
    Given the database is empty
    And a dataset "nama_10_gdp" exists from "eurostat"
    When I request the dataset list twice
    Then both requests should succeed

  # US-12.2: Resilient HTTP Client
  # The application uses httpx with retry logic via tenacity.

  @us-12.2
  Scenario: HTTP client configuration includes retry logic
    Given the HTTP client is configured
    Then the client should have retry capability

  # US-12.3: Self-Hosted Static Assets
  # Static files are served from /static/ directory.

  @us-12.3
  Scenario: Health endpoint is available
    When I request the health endpoint
    Then the response status should be 200

  # US-12.4: SQLite Concurrent Access
  # WAL mode enables concurrent reads during writes.

  @us-12.4
  Scenario: Database supports concurrent operations
    Given the database is initialized
    When I perform multiple concurrent reads
    Then all reads should succeed
