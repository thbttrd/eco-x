"""Health check endpoint for the data platform.

Provides status information about the platform, database, and workers.
"""

from typing import Any

from fastapi import APIRouter

from ecox_platform.infrastructure.cache import get_cache
from ecox_platform.infrastructure.database import get_db_manager
from ecox_platform.scheduler import get_fetcher

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Check platform health status.

    Returns:
        Health status including database and worker status
    """
    db_manager = get_db_manager()
    db_health = await db_manager.health_check()

    # Get scheduler status if available
    try:
        fetcher = get_fetcher()
        fetcher_status = fetcher.status()
    except Exception:
        fetcher_status = {"is_running": False, "error": "Scheduler not initialized"}

    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "service": "ecox-data-platform",
        "database": db_health,
        "scheduler": fetcher_status,
    }


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Check if the platform is ready to serve requests.

    Returns:
        Readiness status
    """
    db_manager = get_db_manager()
    db_health = await db_manager.health_check()

    if db_health["status"] != "healthy":
        return {"ready": False, "reason": "Database not ready"}

    return {"ready": True}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Simple liveness probe.

    Returns:
        Liveness status
    """
    return {"status": "alive"}


@router.get("/memory")
async def memory_stats() -> dict[str, Any]:
    """Get memory and cache statistics.

    Returns detailed information about cache usage and process memory
    for monitoring and debugging memory growth issues.

    Returns:
        Memory and cache statistics
    """
    cache = get_cache()
    return cache.stats()
