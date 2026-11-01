@epic_11 @ui
Feature: Internationalization (i18n)
  As a user
  I want to switch the application language
  So that I can use the platform in my preferred language

  Background:
    Given the client app is running

  # US-11.1: Switch Application Language

  @us-11.1
  Scenario: Default language is English
    When I request the homepage
    Then the response should be HTML
    And the response should contain "EconoScope"
    And the response should contain "Data Sources"

  @us-11.1
  Scenario: Switch to French language
    When I request the homepage with lang "fr"
    Then the response should be HTML
    And the response should contain "EconoScope"
    And the response should contain "Sources de Donnees"

  # US-11.2: Translate User Interface

  @us-11.2
  Scenario: Navigation tabs translated in English
    When I request the homepage
    Then the response should be HTML
    And the response should contain "Data Sources"
    And the response should contain "Datasets"

  @us-11.2
  Scenario: Navigation tabs translated in French
    When I request the homepage with lang "fr"
    Then the response should be HTML
    And the response should contain "Sources de Donnees"
    And the response should contain "Jeux de Donnees"

  # US-11.3: Extensible Language System

  @us-11.3
  Scenario: Translation files exist
    Given the translation files exist
    Then "en.yaml" should contain "nav.data_sources"
    And "fr.yaml" should contain "nav.data_sources"
