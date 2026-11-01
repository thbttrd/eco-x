"""Health check endpoints."""

from typing import Any

import httpx
import structlog
from fastapi import APIRouter

from ecox_agents.config import settings

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Check agent service health."""
    # Check platform connectivity
    platform_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.platform_url}/health")
            platform_status = "connected" if response.status_code == 200 else "error"
    except Exception as e:
        logger.warning("Platform health check failed", error=str(e))
        platform_status = "disconnected"

    return {
        "status": "healthy",
        "service": "ecox-agents",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "platform": platform_status,
    }


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Check if service is ready to handle requests."""
    # For now, just check if we can import pydantic_ai
    try:
        import pydantic_ai  # noqa: F401  # pyright: ignore[reportUnusedImport]

        return {"ready": True}
    except ImportError:
        return {"ready": False, "reason": "pydantic_ai not available"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "alive"}
