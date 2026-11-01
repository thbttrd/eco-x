@epic_8 @ui
Feature: Application Information
  As a user
  I want to see application information in the header
  So that I know which version of the platform I am using

  Background:
    Given the client app is running

  # US-8.1: Display Application Version

  @us-8.1
  Scenario: Version is displayed in the header
    When I request the homepage
    Then the response should be HTML
    And the response should contain the current version

  @us-8.1
  Scenario: Version badge has proper styling
    When I request the homepage
    Then the response should be HTML
    And the response should contain "bg-green-100"
    And the response should contain "text-green-700"

  # US-8.2: Display Application Name

  @us-8.2
  Scenario: Application name is displayed in the header
    When I request the homepage
    Then the response should be HTML
    And the response should contain "EconoScope"
