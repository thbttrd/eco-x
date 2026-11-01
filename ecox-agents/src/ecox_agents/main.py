"""FastAPI application for ecox-agents service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ecox_agents.api.routes import health, summarize
from ecox_agents.config import settings
from ecox_agents.infrastructure.database import close_db_manager, init_db_manager

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle."""
    logger.info(
        "Starting ecox-agents",
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
    )

    # Initialize database
    db_manager = init_db_manager()
    await db_manager.create_tables()
    logger.info("Database tables created")

    yield

    logger.info("Shutting down ecox-agents")
    await close_db_manager()


# Create FastAPI app
app = FastAPI(
    title="ecox-agents",
    description="AI agent service for eco-x platform",
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

# Include routers
app.include_router(health.router)
app.include_router(summarize.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ecox_agents.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
