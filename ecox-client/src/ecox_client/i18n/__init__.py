"""Internationalization (i18n) module for ecox-client.

Provides translation loading and language detection middleware.
"""

from ecox_client.i18n.loader import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    clear_cache,
    get_translation,
    get_translations,
)
from ecox_client.i18n.middleware import I18nMiddleware

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "get_translation",
    "get_translations",
    "clear_cache",
    "I18nMiddleware",
]
