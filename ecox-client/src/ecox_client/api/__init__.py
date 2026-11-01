"""API module for the client application."""

from ecox_client.api.routes import ui
from ecox_client.api.templates import get_template_context, templates

__all__ = ["ui", "templates", "get_template_context"]
