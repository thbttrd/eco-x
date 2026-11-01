"""FastAPI application for the ecox data platform.

This is the main entry point for the platform API.
"""

# Configure logging FIRST, before any other imports that use structlog
from ecox_platform.logging_config import configure_logging

configure_logging()

from collections.abc import AsyncIterator  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from typing import Any  # noqa: E402

import structlog  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from ecox_platform.api.routes import datasets, fetch_logs, health, news, sources  # noqa: E402
from ecox_platform.config import settings  # noqa: E402
from ecox_platform.infrastructure.cache import get_cache  # noqa: E402
from ecox_platform.infrastructure.database import close_db_manager, init_db_manager  # noqa: E402
from ecox_platform.news import start_news_worker, stop_news_worker  # noqa: E402
from ecox_platform.scheduler import start_fetcher, stop_fetcher  # noqa: E402

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle.

    Handles startup and shutdown of database and scheduler.
    """
    logger.info("Starting ecox-data-platform")

    # Initialize database
    db_manager = init_db_manager()
    logger.info("Database manager initialized")

    # Create tables if needed (for development)
    # In production, use Alembic migrations
    try:
        await db_manager.create_all_tables()
    except Exception as e:
        logger.warning("Could not create tables", error=str(e))

    # Start the cache cleanup daemon
    cache = get_cache()
    await cache.start_cleanup_daemon()
    logger.info("Cache cleanup daemon started")

    # Start the continuous fetcher
    try:
        await start_fetcher()
        logger.info("Continuous fetcher started")
    except Exception as e:
        logger.error("Failed to start fetcher", error=str(e))

    # Start the news worker
    try:
        await start_news_worker()
        logger.info("News worker started")
    except Exception as e:
        logger.error("Failed to start news worker", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down ecox-data-platform")

    # Stop the fetcher
    try:
        await stop_fetcher()
    except Exception as e:
        logger.error("Error stopping fetcher", error=str(e))

    # Stop the news worker
    try:
        await stop_news_worker()
    except Exception as e:
        logger.error("Error stopping news worker", error=str(e))

    # Stop the cache cleanup daemon
    await cache.stop_cleanup_daemon()
    logger.info("Cache cleanup daemon stopped")

    # Close database
    await close_db_manager()
    logger.info("Platform shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="ecox-data-platform",
    description="Data platform for fetching and serving economic datasets",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware for client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify client origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(sources.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(fetch_logs.router, prefix="/api")
app.include_router(news.router, prefix="/api")


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "name": "ecox-data-platform",
        "version": "1.0.0",
        "description": "Data platform for economic datasets",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ecox_platform.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
