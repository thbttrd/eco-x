"""Internationalization step definitions for ecox-client BDD tests."""

from pathlib import Path
from typing import Any

import yaml
from pytest_bdd import given, parsers, then, when

# ==============================================================================
# Given Steps - i18n Setup
# ==============================================================================


@given("the translation files exist")
def translation_files_exist(scenario_context: dict[str, Any]) -> None:
    """Verify translation files exist."""
    locales_dir = Path(__file__).parent.parent.parent.parent / "locales"
    assert locales_dir.exists(), f"Locales directory not found: {locales_dir}"

    en_file = locales_dir / "en.yaml"
    fr_file = locales_dir / "fr.yaml"

    assert en_file.exists(), f"English translation file not found: {en_file}"
    assert fr_file.exists(), f"French translation file not found: {fr_file}"

    scenario_context["locales_dir"] = locales_dir


# ==============================================================================
# When Steps - i18n Requests
# ==============================================================================


@when("I request the homepage")
def request_homepage(
    scenario_context: dict[str, Any],
    api_client: Any,
) -> None:
    """Request the homepage without language parameter."""
    response = api_client.get("/")
    scenario_context["response"] = response


@when(parsers.parse('I request the homepage with lang "{lang}"'))
def request_homepage_with_lang(
    scenario_context: dict[str, Any],
    api_client: Any,
    lang: str,
) -> None:
    """Request the homepage with a specific language."""
    response = api_client.get(f"/?lang={lang}")
    scenario_context["response"] = response


# ==============================================================================
# Then Steps - i18n Assertions
# ==============================================================================


@then(parsers.parse('"{filename}" should contain "{key}"'))
def translation_file_contains_key(
    scenario_context: dict[str, Any],
    filename: str,
    key: str,
) -> None:
    """Assert translation file contains a key (dot notation)."""
    locales_dir = scenario_context.get("locales_dir")
    if not locales_dir:
        locales_dir = Path(__file__).parent.parent.parent.parent / "locales"

    filepath = locales_dir / filename
    assert filepath.exists(), f"Translation file not found: {filepath}"

    with open(filepath) as f:
        translations = yaml.safe_load(f)

    # Parse dot notation key (e.g., "nav.data_sources")
    keys = key.split(".")
    value = translations
    for k in keys:
        assert k in value, f"Key '{key}' not found in {filename}"
        value = value[k]
