"""Translation loading and access for ecox-client i18n."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

# Supported languages - add new language codes here
SUPPORTED_LANGUAGES: list[str] = ["en", "fr"]
DEFAULT_LANGUAGE: str = "en"

# Path to locales directory (relative to ecox-client package root)
LOCALES_DIR = Path(__file__).parent.parent.parent.parent / "locales"


def _flatten_dict(data: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, str]:
    """Flatten a nested dictionary to dot-notation keys.

    Example:
        {"app": {"name": "EconoScope"}} -> {"app.name": "EconoScope"}
    """
    items: list[tuple[str, str]] = []
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(_flatten_dict(value, new_key, sep).items())
        else:
            items.append((new_key, str(value)))
    return dict(items)


@lru_cache(maxsize=len(SUPPORTED_LANGUAGES))
def _load_translation_file(lang: str) -> dict[str, str]:
    """Load and flatten translations for a language.

    Uses LRU cache to avoid repeated file reads.
    Falls back to default language if file not found.
    """
    locale_path = LOCALES_DIR / f"{lang}.yaml"

    # Fall back to default language if file doesn't exist
    if not locale_path.exists():
        locale_path = LOCALES_DIR / f"{DEFAULT_LANGUAGE}.yaml"

    if not locale_path.exists():
        return {}

    with open(locale_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return _flatten_dict(data)


def get_translations(lang: str) -> dict[str, str]:
    """Get all translations for a language as a flat dictionary.

    Args:
        lang: Language code (e.g., "en", "fr")

    Returns:
        Dictionary mapping translation keys to translated strings
    """
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    return _load_translation_file(lang)


def get_translation(key: str, lang: str, **kwargs: Any) -> str:
    """Get a single translation by key with optional interpolation.

    Args:
        key: Translation key in dot notation (e.g., "app.name")
        lang: Language code (e.g., "en", "fr")
        **kwargs: Values to interpolate into the translation

    Returns:
        Translated string, or the key itself if not found (for debugging)

    Example:
        get_translation("datasets.showing_of", "en", count=5, total=100)
        -> "Showing 5 of 100 datasets"
    """
    translations = get_translations(lang)
    text = translations.get(key, key)  # Fall back to key if not found

    # Interpolate values if provided
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            # If interpolation fails, return text as-is
            pass

    return text


def clear_cache() -> None:
    """Clear the translation cache.

    Useful for development/testing when translation files are modified.
    """
    _load_translation_file.cache_clear()
