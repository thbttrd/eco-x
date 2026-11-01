"""ONS (UK Office for National Statistics) data source.

This module provides access to the ONS API for UK economic and social data.
"""

from ecox_platform.sources.ons.repository import OnsRepository
from ecox_platform.sources.ons.service import OnsService

__all__ = ["OnsRepository", "OnsService"]
