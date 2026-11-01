@epic_13 @infrastructure
Feature: Migrations & Factories
  As a developer
  I want database migrations and test data factories
  So that I can manage schema changes and create test data easily

  # US-13.1: Alembic Migration Infrastructure

  @us-13.1
  Scenario: Migration infrastructure is configured
    Given the project has an alembic configuration
    Then the alembic env.py file should exist
    And the alembic versions directory should exist

  @us-13.1
  Scenario: Initial schema migration exists
    Given the project has alembic migrations
    Then an initial schema migration should exist
    And the migration should create core tables

  # US-13.2: Factory-Boy Test Data Factories

  @us-13.2
  Scenario: Dataset factory generates valid models
    Given the factory-boy library is available
    When I create a dataset using the factory
    Then the dataset should have required fields
    And the dataset code should be unique

  @us-13.2
  Scenario: DataValue factory generates valid observations
    Given the factory-boy library is available
    When I create data values using the factory
    Then the data values should have numeric values
    And the data values should have time periods

  # US-13.3: SQLModel Schema Definition

  @us-13.3
  Scenario: SQLModel metadata contains all tables
    Given the SQLModel metadata is initialized
    Then the metadata should contain the dataset table
    And the metadata should contain the datavalue table
    And the metadata should contain the fetchlog table

  # US-13.4: In-Memory Testing Support

  @us-13.4
  Scenario: In-memory SQLite works for testing
    Given an in-memory SQLite database
    When I create all tables
    Then the tables should be queryable
