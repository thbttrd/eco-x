"""OECD data source implementation.

Provides access to OECD's SDMX 2.1 REST API for economic and statistical data.
"""

from ecox_platform.sources.oecd.repository import OecdRepository
from ecox_platform.sources.oecd.service import OecdService

__all__ = ["OecdRepository", "OecdService"]
