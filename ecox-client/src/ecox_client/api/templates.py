"""Shared template utilities for FastAPI routes with i18n support."""

import os
import tomllib
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from ecox_client.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    get_translation,
    get_translations,
)

# Template directory (relative to ecox-client package root)
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"

# Configure Jinja2 templates (shared instance)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def timeago(value: datetime | None) -> str:
    """Convert datetime to relative time string (e.g., '2h ago').

    Used in Jinja2 templates as a filter: {{ entry.published_at | timeago }}
    """
    if value is None:
        return ""

    # Make comparison timezone-aware
    now = datetime.now(UTC).replace(tzinfo=None)
    if value.tzinfo:
        value = value.replace(tzinfo=None)

    diff = now - value
    seconds = diff.total_seconds()

    if seconds < 0:
        return "just now"
    elif seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days}d ago"
    else:
        return value.strftime("%b %d")


# Register custom filter
templates.env.filters["timeago"] = timeago


def _find_root_pyproject() -> Path | None:
    """Find the root pyproject.toml by searching for semantic_release config."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            with open(pyproject, "rb") as f:
                data = tomllib.load(f)
            # Root pyproject.toml has semantic_release config
            if "tool" in data and "semantic_release" in data["tool"]:
                return pyproject
    return None


@lru_cache(maxsize=1)
def get_version() -> str:
    """Read version from environment variable or root pyproject.toml.

    Priority:
    1. ECOX_VERSION env var (set in container builds)
    2. Root pyproject.toml (for local development)
    3. Fallback to "unknown"
    """
    # Check environment variable first (used in containers)
    env_version = os.environ.get("ECOX_VERSION")
    if env_version and env_version != "unknown":
        return env_version

    # Fall back to reading from pyproject.toml (local development)
    pyproject_path = _find_root_pyproject()
    if pyproject_path:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        version = data.get("project", {}).get("version", "unknown")
        return str(version)
    return "unknown"


# Version for cache busting (read dynamically)
VERSION = get_version()


def get_template_context(request: Request, **extra: Any) -> dict[str, Any]:
    """Build template context with i18n support.

    This should be used by all routes that render templates to ensure
    consistent translation support across the application.

    Args:
        request: FastAPI request object
        **extra: Additional context variables to pass to the template

    Returns:
        dict: Template context with translation function and language info
    """
    lang = getattr(request.state, "lang", DEFAULT_LANGUAGE)

    def t(key: str, **kwargs: Any) -> str:
        """Translation helper for templates."""
        return get_translation(key, lang, **kwargs)

    context = {
        "request": request,
        "t": t,
        "current_lang": lang,
        "supported_languages": SUPPORTED_LANGUAGES,
        "translations": get_translations(lang),
        "version": VERSION,
    }

    # Add any extra context variables
    context.update(extra)

    return context
