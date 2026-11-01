"""FastAPI application for the ecox client web UI.

This is the main entry point for the client application.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ecox_client.api.routes import events, ui
from ecox_client.api.routes.ui import get_source_activations
from ecox_client.api.templates import get_template_context, templates
from ecox_client.config import settings
from ecox_client.i18n import I18nMiddleware
from ecox_client.infrastructure.database import close_db_manager, init_db_manager
from ecox_client.infrastructure.platform_client import (
    PlatformClientError,
    close_platform_client,
    get_platform_client,
)

logger = structlog.get_logger(__name__)

# Static file path
BASE_DIR = Path(__file__).parent.parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle.

    Handles startup and shutdown of database and platform client.
    """
    logger.info("Starting ecox-client")

    # Initialize database
    db_manager = init_db_manager()
    logger.info("Database manager initialized")

    # Create tables if needed
    try:
        await db_manager.create_all_tables()
    except Exception as e:
        logger.warning("Could not create tables", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down ecox-client")

    # Close platform client
    await close_platform_client()

    # Close database
    await close_db_manager()
    logger.info("Client shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="ecox-client",
    description="Web UI client for the ecox data platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add i18n middleware for language detection
app.add_middleware(I18nMiddleware)


# Root route - serves main application page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Serve the main application page with activated sources for dropdown."""
    # Fetch activated sources for the source filter dropdown
    try:
        client = get_platform_client()
        api_sources = await client.list_sources()
        activations = await get_source_activations()

        # Filter to only activated sources
        activated_sources = [
            {"code": src["code"], "name": src["name"]}
            for src in api_sources
            if activations.get(src["code"], True)  # Default to activated
        ]
    except PlatformClientError as e:
        logger.error("Failed to fetch sources for dropdown", error=str(e))
        activated_sources = []

    return templates.TemplateResponse(
        "pages/index.html",
        get_template_context(request, activated_sources=activated_sources),
    )


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Check client health status."""
    from ecox_client.infrastructure.database import get_db_manager
    from ecox_client.infrastructure.platform_client import get_platform_client

    db_manager = get_db_manager()
    db_health = await db_manager.health_check()

    # Check platform connectivity
    platform_status = "unknown"
    try:
        client = get_platform_client()
        platform_health = await client.health()
        platform_status = platform_health.get("status", "unknown")
    except Exception as e:
        platform_status = f"error: {e}"

    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "service": "ecox-client",
        "database": db_health,
        "platform": {"status": platform_status, "url": settings.platform_url},
    }


# Include UI routes (htmx endpoints)
app.include_router(ui.router, prefix="/api", tags=["ui"])

# Include SSE events route
app.include_router(events.router, prefix="/api", tags=["events"])

# Mount static files (must be after routes to not catch everything)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ecox_client.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
