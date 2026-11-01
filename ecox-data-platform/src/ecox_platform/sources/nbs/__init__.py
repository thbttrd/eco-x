"""NBS China data source implementation.

Provides access to China's National Bureau of Statistics data through
the data.stats.gov.cn API.
"""

from ecox_platform.sources.nbs.repository import NbsRepository
from ecox_platform.sources.nbs.service import NbsService

__all__ = ["NbsRepository", "NbsService"]
