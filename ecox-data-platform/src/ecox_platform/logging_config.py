"""Logging configuration for the platform.

Configures structlog and Python stdlib logging to respect ECOX_LOG_LEVEL.
"""

import logging
import sys

import structlog

from ecox_platform.config import settings

# Maximum length for error messages in logs (prevents huge SQL dumps)
MAX_ERROR_LENGTH = 500


def truncate_error(error: Exception | str, max_length: int = MAX_ERROR_LENGTH) -> str:
    """Truncate error message to prevent log flooding from large SQL statements.

    Args:
        error: Exception or error string to truncate
        max_length: Maximum length of returned string

    Returns:
        Truncated error string
    """
    error_str = str(error)
    if len(error_str) <= max_length:
        return error_str
    return error_str[:max_length] + "... [truncated]"


def configure_logging() -> None:
    """Configure structlog and stdlib logging with the configured log level.

    This must be called early in application startup, before any logging occurs.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure stdlib logging (used by uvicorn, httpx, etc.)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Set log level for common noisy loggers
    logging.getLogger("httpx").setLevel(max(log_level, logging.WARNING))
    logging.getLogger("httpcore").setLevel(max(log_level, logging.WARNING))
    logging.getLogger("asyncio").setLevel(max(log_level, logging.WARNING))

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=True),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
