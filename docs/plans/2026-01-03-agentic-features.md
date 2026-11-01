# Agentic AI Features Implementation Plan

## Overview

This plan implements two AI-powered features for the eco-x platform:
1. **News Summarization** - Generate concise summaries of economic news articles (< 500 words)
2. **Dataset Q&A** - Answer natural language questions about economic data

The implementation creates a new `ecox-agents` microservice using Pydantic AI with Claude as the LLM backend.

## Current State Analysis

### Existing Components
- `ecox-data-platform` (port 8000) - Data APIs for datasets and news
- `ecox-client` (port 8080) - Web UI with htmx/Alpine.js
- `ecox-shared` - Shared models and schemas

### Key Discoveries
- News entries have `content_full` field available via `/api/news/entries/{id}` (`ecox-data-platform/src/ecox_platform/api/routes/news.py:331`)
- Datasets API supports search, filtering by geo/time_period/indicator (`ecox-data-platform/src/ecox_platform/api/routes/datasets.py:60-353`)
- Client uses `PlatformClient` pattern for HTTP communication (`ecox-client/src/ecox_client/infrastructure/platform_client.py:31`)
- Component structure follows: `pyproject.toml` → `src/ecox_{name}/` → `config.py`, `main.py`, `api/routes/`

## Desired End State

After implementation:
1. A new `ecox-agents` service running on port 8001
2. Users can click "Summarize" on news entries to get AI-generated summaries
3. Users can ask questions like "What is inflation in Germany?" in a new "Ask" tab
4. Summaries are cached in PostgreSQL to avoid redundant LLM calls
5. Q&A conversation history is stored in Redis for follow-up questions

### Verification
- `curl http://localhost:8001/health` returns healthy status
- POST to `/api/agents/summarize/news/{id}` returns structured summary
- POST to `/api/agents/qa/ask` with question returns data-backed answer
- UI shows "Summarize" button in news modal and "Ask" tab in navigation

## What We're NOT Doing

- Langfuse observability (deferred to later phase)
- Sentiment analysis as standalone feature (included in summary)
- Economic report generation (Phase 2 per ADR)
- Multi-language summaries
- Voice input for Q&A
- Streaming responses (simpler request/response for now)

## Implementation Approach

**Strategy**: Build incrementally with working features at each phase checkpoint.

1. **Phase 1**: Create `ecox-agents` scaffolding with health check
2. **Phase 2**: Implement news summarization with caching
3. **Phase 3**: Implement dataset Q&A with Redis memory
4. **Phase 4**: Integrate UI components in ecox-client

---

## Phase 1: ecox-agents Foundation

### Overview
Create the new `ecox-agents` component with basic structure, configuration, and health check endpoint.

### Changes Required

#### 1. Create Component Structure

**Directory**: `ecox-agents/`

```
ecox-agents/
├── pyproject.toml
├── Containerfile
└── src/
    └── ecox_agents/
        ├── __init__.py
        ├── config.py
        ├── main.py
        └── api/
            ├── __init__.py
            └── routes/
                ├── __init__.py
                └── health.py
```

#### 2. pyproject.toml

**File**: `ecox-agents/pyproject.toml`

```toml
[project]
name = "ecox-agents"
version = "1.0.0"
description = "AI agent service for eco-x platform"
requires-python = ">=3.12"
authors = [
    { name = "Thibaut Troude" }
]
dependencies = [
    # Web framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    # AI framework
    "pydantic-ai>=1.0.0",
    "anthropic>=0.40.0",
    # HTTP client for platform API
    "httpx>=0.27.0",
    # Redis for conversation memory
    "redis>=5.0.0",
    # Utilities
    "structlog>=24.0.0",
    "pydantic-settings>=2.1.0",
]

[project.scripts]
ecox-agents = "ecox_agents.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ecox_agents"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "respx>=0.21.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.pyright]
include = ["src"]
pythonVersion = "3.12"
typeCheckingMode = "strict"
```

#### 3. Package Init

**File**: `ecox-agents/src/ecox_agents/__init__.py`

```python
"""ECOX Agents - AI-powered analysis service for eco-x platform.

This service provides:
- News summarization with sentiment analysis
- Natural language Q&A over economic datasets
"""

__version__ = "1.0.0"
```

#### 4. Configuration

**File**: `ecox-agents/src/ecox_agents/config.py`

```python
"""Configuration settings for ecox-agents service."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Agent service configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ECOX_AGENTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Server
    api_host: str = Field(default="0.0.0.0", description="API host")  # nosec B104
    api_port: int = Field(default=8001, description="API port")

    # LLM Configuration
    llm_provider: Literal["anthropic", "openai", "ollama"] = Field(
        default="anthropic", description="LLM provider"
    )
    llm_model: str = Field(
        default="claude-sonnet-4-5", description="Model name"
    )
    anthropic_api_key: str | None = Field(
        default=None, description="Anthropic API key"
    )

    # Platform Communication
    platform_url: str = Field(
        default="http://localhost:8000", description="Platform API URL"
    )
    platform_timeout: float = Field(
        default=30.0, description="Platform API timeout"
    )

    # Redis for Conversation Memory
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )
    conversation_ttl: int = Field(
        default=1800, description="Conversation TTL in seconds (30 min)"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")


# Global settings instance
settings = Settings()
```

#### 5. Main Application

**File**: `ecox-agents/src/ecox_agents/main.py`

```python
"""FastAPI application for ecox-agents service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ecox_agents.api.routes import health
from ecox_agents.config import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle."""
    logger.info(
        "Starting ecox-agents",
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
    )

    yield

    logger.info("Shutting down ecox-agents")


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ecox_agents.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
```

#### 6. Health Check Router

**File**: `ecox-agents/src/ecox_agents/api/routes/health.py`

```python
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
        import pydantic_ai  # noqa: F401
        return {"ready": True}
    except ImportError:
        return {"ready": False, "reason": "pydantic_ai not available"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "alive"}
```

#### 7. API Routes Package

**File**: `ecox-agents/src/ecox_agents/api/__init__.py`

```python
"""API module for ecox-agents."""
```

**File**: `ecox-agents/src/ecox_agents/api/routes/__init__.py`

```python
"""API routes for ecox-agents."""

from ecox_agents.api.routes import health

__all__ = ["health"]
```

#### 8. Containerfile

**File**: `ecox-agents/Containerfile`

```dockerfile
# ecox-agents Containerfile
# Multi-stage build for minimal production image

# Build stage
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv for fast dependency management
RUN pip install uv

# Copy agent package
COPY ecox-agents/pyproject.toml /build/ecox-agents/
COPY ecox-agents/src/ /build/ecox-agents/src/

# Install dependencies
WORKDIR /build/ecox-agents
RUN uv pip install --system --no-cache-dir .

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/

# Copy application code
COPY ecox-agents/src/ /app/src/
RUN chmod -R a+rX /app/src

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd --create-home appuser
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "ecox_agents.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### 9. Update Workspace

**File**: `pyproject.toml` (root)

Add to workspace members:

```toml
[tool.uv.workspace]
members = ["ecox-data-platform", "ecox-client", "ecox-shared", "ecox-agents"]
```

#### 10. Update podman-compose.yaml

Add Redis and agents services:

```yaml
  # Redis for conversation memory
  redis:
    image: redis:7-alpine
    container_name: ecox-redis${ECOX_SUFFIX:-}
    ports:
      - "${ECOX_REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  # AI Agents service
  agents:
    build:
      context: .
      dockerfile: ecox-agents/Containerfile
    container_name: ecox-agents${ECOX_SUFFIX:-}
    environment:
      ECOX_AGENTS_PLATFORM_URL: http://platform:8000
      ECOX_AGENTS_REDIS_URL: redis://redis:6379/0
      ECOX_AGENTS_ANTHROPIC_API_KEY: ${ECOX_AGENTS_ANTHROPIC_API_KEY}
      ECOX_AGENTS_LOG_LEVEL: INFO
    ports:
      - "${ECOX_AGENTS_PORT:-8001}:8001"
    depends_on:
      platform:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8001/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

volumes:
  # ... existing volumes ...
  redis_data:
```

### Success Criteria

#### Automated Verification:
- [x] Package installs: `cd ecox-agents && uv sync`
- [x] Type checking passes: `cd ecox-agents && uv run pyright src/`
- [x] Service starts locally: `cd ecox-agents && uv run python -m ecox_agents.main`
- [x] Health check responds: `curl http://localhost:8001/health`

#### Manual Verification:
- [x] Container builds: `podman-compose build agents`
- [x] Service starts in container: `podman-compose up -d agents`
- [x] Health check returns platform connection status
- [x] Logs show correct configuration values

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation before proceeding to Phase 2.

---

## Phase 2: News Summarization

### Overview
Implement the news summarization agent with caching in PostgreSQL.

### Changes Required

#### 1. Create Summarizer Agent

**File**: `ecox-agents/src/ecox_agents/agents/summarizer.py`

```python
"""News summarization agent."""

from dataclasses import dataclass
from typing import Literal

import httpx
import structlog
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

from ecox_agents.config import settings

logger = structlog.get_logger(__name__)


class NewsSummary(BaseModel):
    """Structured output for news summarization."""

    summary: str = Field(description="Concise summary under 500 words")
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Overall sentiment of the article"
    )
    key_indicators: list[str] = Field(
        default_factory=list,
        description="Economic indicators mentioned (GDP, CPI, rates, etc.)",
    )
    extracted_data: dict[str, str | float] = Field(
        default_factory=dict,
        description="Key data points extracted (interest rates, growth figures)",
    )


@dataclass
class SummarizerDeps:
    """Dependencies for summarization agent."""

    http_client: httpx.AsyncClient


def create_summarizer_agent() -> Agent[SummarizerDeps, NewsSummary]:
    """Create the news summarizer agent."""
    model = f"{settings.llm_provider}:{settings.llm_model}"

    agent: Agent[SummarizerDeps, NewsSummary] = Agent(
        model,
        deps_type=SummarizerDeps,
        output_type=NewsSummary,
        system_prompt="""You are an expert economic analyst. Your task is to:

1. Summarize news articles concisely (MUST be under 500 words)
2. Identify the overall sentiment (positive/negative/neutral)
3. Extract key economic indicators mentioned (GDP, CPI, unemployment, etc.)
4. Note specific data points (interest rates, growth percentages, etc.)

Be precise with numbers and focus on the most important information.
If the article is about a policy decision, highlight the decision and its implications.
If numbers are mentioned, include them in extracted_data with descriptive keys.""",
    )

    @agent.output_validator
    async def validate_summary(
        ctx: RunContext[SummarizerDeps], output: NewsSummary
    ) -> NewsSummary:
        """Validate summary meets requirements."""
        word_count = len(output.summary.split())
        if word_count > 500:
            raise ModelRetry(
                f"Summary is {word_count} words. Please condense to under 500 words."
            )
        if word_count < 30:
            raise ModelRetry(
                "Summary is too brief. Please provide more substantive analysis."
            )
        return output

    return agent


# Global agent instance
summarizer_agent = create_summarizer_agent()
```

#### 2. Create Summary Cache Model

**File**: `ecox-agents/src/ecox_agents/models/summary.py`

```python
"""Database models for summary caching."""

import hashlib
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlmodel import Column, Field, SQLModel, Text


class NewsSummaryCache(SQLModel, table=True):
    """Cached news summary stored in PostgreSQL."""

    __tablename__ = "news_summary_cache"

    id: int | None = Field(default=None, primary_key=True)
    entry_id: int = Field(unique=True, index=True, description="NewsEntry ID")
    summary_text: str = Field(sa_column=Column(Text), description="Generated summary")
    sentiment: str = Field(description="positive/negative/neutral")
    key_indicators: str = Field(
        default="[]", description="JSON list of indicators"
    )
    extracted_data: str = Field(
        default="{}", description="JSON dict of extracted data"
    )
    model_version: str = Field(description="Model used for generation")
    content_hash: str = Field(
        index=True, description="Hash of source content for invalidation"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SummaryRequest(BaseModel):
    """Request to summarize a news entry."""

    entry_id: int
    force_regenerate: bool = False


class SummaryResponse(BaseModel):
    """Response containing news summary."""

    entry_id: int
    summary: str
    sentiment: str
    key_indicators: list[str]
    extracted_data: dict[str, Any]
    cached: bool
    cached_at: datetime | None = None
    model_version: str


def compute_content_hash(content: str) -> str:
    """Compute hash of content for cache invalidation."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
```

#### 3. Create Summarization Service

**File**: `ecox-agents/src/ecox_agents/services/summarizer.py`

```python
"""Summarization service with caching."""

import json
from datetime import datetime

import httpx
import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_agents.agents.summarizer import NewsSummary, SummarizerDeps, summarizer_agent
from ecox_agents.config import settings
from ecox_agents.models.summary import (
    NewsSummaryCache,
    SummaryResponse,
    compute_content_hash,
)

logger = structlog.get_logger(__name__)


class SummarizationService:
    """Service for summarizing news entries with caching."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_cached_summary(self, entry_id: int) -> NewsSummaryCache | None:
        """Get cached summary if exists."""
        statement = select(NewsSummaryCache).where(
            NewsSummaryCache.entry_id == entry_id
        )
        result = await self.session.exec(statement)
        return result.one_or_none()

    async def save_summary(
        self,
        entry_id: int,
        summary: NewsSummary,
        content_hash: str,
    ) -> NewsSummaryCache:
        """Save summary to cache."""
        cache_entry = NewsSummaryCache(
            entry_id=entry_id,
            summary_text=summary.summary,
            sentiment=summary.sentiment,
            key_indicators=json.dumps(summary.key_indicators),
            extracted_data=json.dumps(summary.extracted_data),
            model_version=f"{settings.llm_provider}:{settings.llm_model}",
            content_hash=content_hash,
        )

        # Upsert - delete existing if present
        existing = await self.get_cached_summary(entry_id)
        if existing:
            await self.session.delete(existing)
            await self.session.flush()

        self.session.add(cache_entry)
        await self.session.commit()
        await self.session.refresh(cache_entry)

        return cache_entry

    async def summarize_entry(
        self, entry_id: int, force_regenerate: bool = False
    ) -> SummaryResponse:
        """Summarize a news entry, using cache if available."""
        # Fetch entry from platform
        async with httpx.AsyncClient(timeout=settings.platform_timeout) as client:
            response = await client.get(
                f"{settings.platform_url}/api/news/entries/{entry_id}"
            )
            response.raise_for_status()
            entry_data = response.json()

        content = entry_data.get("content_full") or entry_data.get("content_preview")
        if not content:
            raise ValueError(f"No content available for entry {entry_id}")

        content_hash = compute_content_hash(content)

        # Check cache
        if not force_regenerate:
            cached = await self.get_cached_summary(entry_id)
            if cached and cached.content_hash == content_hash:
                logger.info("Returning cached summary", entry_id=entry_id)
                return SummaryResponse(
                    entry_id=entry_id,
                    summary=cached.summary_text,
                    sentiment=cached.sentiment,
                    key_indicators=json.loads(cached.key_indicators),
                    extracted_data=json.loads(cached.extracted_data),
                    cached=True,
                    cached_at=cached.created_at,
                    model_version=cached.model_version,
                )

        # Generate new summary
        logger.info("Generating new summary", entry_id=entry_id)
        async with httpx.AsyncClient(timeout=60.0) as client:
            deps = SummarizerDeps(http_client=client)

            # Build prompt with article content
            title = entry_data.get("title", "Untitled")
            prompt = f"# {title}\n\n{content}"

            result = await summarizer_agent.run(prompt, deps=deps)
            summary = result.output

        # Save to cache
        cache_entry = await self.save_summary(entry_id, summary, content_hash)

        return SummaryResponse(
            entry_id=entry_id,
            summary=summary.summary,
            sentiment=summary.sentiment,
            key_indicators=summary.key_indicators,
            extracted_data=summary.extracted_data,
            cached=False,
            cached_at=cache_entry.created_at,
            model_version=cache_entry.model_version,
        )
```

#### 4. Create Summarization API Routes

**File**: `ecox-agents/src/ecox_agents/api/routes/summarize.py`

```python
"""Summarization API routes."""

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_agents.api.dependencies import get_session
from ecox_agents.models.summary import SummaryRequest, SummaryResponse
from ecox_agents.services.summarizer import SummarizationService

router = APIRouter(prefix="/agents/summarize", tags=["summarize"])
logger = structlog.get_logger(__name__)


@router.post("/news/{entry_id}", response_model=SummaryResponse)
async def summarize_news_entry(
    entry_id: int,
    force_regenerate: bool = False,
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    """Generate or retrieve summary for a news entry.

    Args:
        entry_id: ID of the news entry to summarize
        force_regenerate: If True, bypass cache and generate new summary
    """
    service = SummarizationService(session)

    try:
        return await service.summarize_entry(entry_id, force_regenerate)
    except Exception as e:
        logger.error("Summarization failed", entry_id=entry_id, error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to summarize entry: {str(e)}"
        ) from e


@router.get("/news/{entry_id}", response_model=SummaryResponse | None)
async def get_cached_summary(
    entry_id: int,
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse | dict[str, Any]:
    """Get cached summary if it exists (does not generate new summary)."""
    service = SummarizationService(session)
    cached = await service.get_cached_summary(entry_id)

    if not cached:
        return {"cached": False, "entry_id": entry_id}

    import json

    return SummaryResponse(
        entry_id=entry_id,
        summary=cached.summary_text,
        sentiment=cached.sentiment,
        key_indicators=json.loads(cached.key_indicators),
        extracted_data=json.loads(cached.extracted_data),
        cached=True,
        cached_at=cached.created_at,
        model_version=cached.model_version,
    )
```

#### 5. Add Database Infrastructure

**File**: `ecox-agents/src/ecox_agents/infrastructure/database.py`

```python
"""Database infrastructure for ecox-agents."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_agents.config import settings

logger = structlog.get_logger(__name__)

# Database URL - reuse platform's database
DATABASE_URL = settings.platform_url.replace("http://", "postgresql+asyncpg://").replace(
    ":8000", ":5432"
).rstrip("/") + "/ecox_platform"

# For local development, use a configurable URL
import os
AGENTS_DATABASE_URL = os.environ.get(
    "ECOX_AGENTS_DATABASE_URL",
    "postgresql+asyncpg://ecox:ecox@localhost:5432/ecox_platform"
)


class DatabaseManager:
    """Manages database connections for agents service."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or AGENTS_DATABASE_URL

        self.engine = create_async_engine(
            self.database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )

        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        session = self.async_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_tables(self) -> None:
        """Create tables for agents service."""
        async with self.engine.begin() as conn:
            # Import models to register them
            from ecox_agents.models import summary  # noqa: F401

            await conn.run_sync(SQLModel.metadata.create_all)

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()


# Global instance
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_db_manager(database_url: str | None = None) -> DatabaseManager:
    """Initialize the global database manager."""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    return _db_manager


async def close_db_manager() -> None:
    """Close the global database manager."""
    global _db_manager
    if _db_manager is not None:
        await _db_manager.close()
        _db_manager = None
```

#### 6. Add Dependencies

**File**: `ecox-agents/src/ecox_agents/api/dependencies.py`

```python
"""FastAPI dependencies for agents service."""

from collections.abc import AsyncGenerator

from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_agents.infrastructure.database import get_db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session."""
    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        yield session
```

#### 7. Update Main App

**File**: `ecox-agents/src/ecox_agents/main.py` (update lifespan)

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle."""
    logger.info(
        "Starting ecox-agents",
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
    )

    # Initialize database
    from ecox_agents.infrastructure.database import init_db_manager, close_db_manager

    db_manager = init_db_manager()
    await db_manager.create_tables()
    logger.info("Database tables created")

    yield

    logger.info("Shutting down ecox-agents")
    await close_db_manager()
```

And add the router:

```python
from ecox_agents.api.routes import health, summarize

# Include routers
app.include_router(health.router)
app.include_router(summarize.router, prefix="/api")
```

#### 8. Update podman-compose.yaml

Add database URL environment variable:

```yaml
  agents:
    # ... existing config ...
    environment:
      ECOX_AGENTS_PLATFORM_URL: http://platform:8000
      ECOX_AGENTS_DATABASE_URL: postgresql+asyncpg://ecox:${POSTGRES_PASSWORD:-ecox_dev_password}@postgres:5432/ecox_platform
      ECOX_AGENTS_REDIS_URL: redis://redis:6379/0
      ECOX_AGENTS_ANTHROPIC_API_KEY: ${ECOX_AGENTS_ANTHROPIC_API_KEY}
      ECOX_AGENTS_LOG_LEVEL: INFO
```

### Success Criteria

#### Automated Verification:
- [x] Type checking passes: `cd ecox-agents && uv run pyright src/`
- [x] Service starts: `uv run python -m ecox_agents.main`
- [x] Tables created in database: `podman exec ecox-postgres psql -U ecox -d ecox_platform -c "\dt news_summary*"`
- [x] POST endpoint works: `curl -X POST http://localhost:8001/api/agents/summarize/news/185`

#### Manual Verification:
- [ ] Summary is generated correctly for a real news entry
- [ ] Cache is used on second request (check logs)
- [ ] Force regenerate bypasses cache
- [ ] Summary quality is acceptable (< 500 words, sentiment correct)

**Implementation Note**: Pause here for manual verification before proceeding to Phase 3.

---

## Phase 3: Dataset Q&A

### Overview
Implement the Q&A agent with dataset tools and Redis-based conversation memory.

### Changes Required

#### 1. Create Q&A Agent

**File**: `ecox-agents/src/ecox_agents/agents/qa.py`

```python
"""Dataset Q&A agent."""

from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from ecox_agents.config import settings

logger = structlog.get_logger(__name__)


class QAResponse(BaseModel):
    """Structured response for Q&A queries."""

    answer: str = Field(description="Natural language answer to the question")
    data_sources: list[str] = Field(
        default_factory=list,
        description="Dataset sources used (e.g., 'eurostat:gdp_growth')",
    )
    confidence: str = Field(
        default="medium",
        description="Confidence level: high, medium, low",
    )
    data_values: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Specific data values retrieved",
    )


@dataclass
class QADeps:
    """Dependencies for Q&A agent."""

    http_client: httpx.AsyncClient
    platform_url: str = "http://localhost:8000"


def create_qa_agent() -> Agent[QADeps, QAResponse]:
    """Create the dataset Q&A agent."""
    model = f"{settings.llm_provider}:{settings.llm_model}"

    agent: Agent[QADeps, QAResponse] = Agent(
        model,
        deps_type=QADeps,
        output_type=QAResponse,
        system_prompt="""You are an economic data analyst with access to datasets from multiple sources:
- Eurostat (European statistics)
- FRED (US Federal Reserve data)
- OECD (international economic data)
- ONS (UK statistics)
- NBS (China statistics)

When answering questions:
1. Use search_datasets to find relevant datasets
2. Use get_dimension_values to understand available countries/periods
3. Use get_dataset_values to retrieve specific data
4. Always cite your data sources in the response
5. If data is not available, explain why and suggest alternatives

Geographic codes: Germany=DE, France=FR, Spain=ES, Italy=IT, UK=GB, US=US, China=CN
Time periods: Use YYYY for years, YYYY-QN for quarters, YYYY-MM for months""",
    )

    @agent.tool
    async def search_datasets(
        ctx: RunContext[QADeps],
        query: str,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for datasets matching a query.

        Args:
            query: Search terms (e.g., 'inflation', 'GDP growth', 'unemployment')
            source: Optional filter by source (eurostat, fred, oecd, ons, nbs)
        """
        params: dict[str, Any] = {"search": query, "page_size": 10}
        if source:
            params["source"] = source

        response = await ctx.deps.http_client.get(
            f"{ctx.deps.platform_url}/api/datasets",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])

    @agent.tool
    async def get_dimension_values(
        ctx: RunContext[QADeps],
        source: str,
        code: str,
        dimension: str,
    ) -> list[str]:
        """Get available values for a dataset dimension.

        Args:
            source: Data source (eurostat, fred, etc.)
            code: Dataset code
            dimension: Dimension name (geo, time_period, indicator)
        """
        response = await ctx.deps.http_client.get(
            f"{ctx.deps.platform_url}/api/datasets/{source}/{code}/dimensions/{dimension}",
        )
        response.raise_for_status()
        data = response.json()
        return data.get("values", [])

    @agent.tool
    async def get_dataset_values(
        ctx: RunContext[QADeps],
        source: str,
        code: str,
        geo: str | None = None,
        time_period: str | None = None,
        indicator: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Query values from a dataset.

        Args:
            source: Data source (eurostat, fred, oecd, ons, nbs)
            code: Dataset code
            geo: Geographic filter (e.g., 'DE', 'FR', 'US')
            time_period: Time period filter (e.g., '2024', '2024-Q1')
            indicator: Indicator filter
            limit: Maximum records to return
        """
        params: dict[str, Any] = {"page_size": limit}
        if geo:
            params["geo"] = geo
        if time_period:
            params["time_period"] = time_period
        if indicator:
            params["indicator"] = indicator

        response = await ctx.deps.http_client.get(
            f"{ctx.deps.platform_url}/api/datasets/{source}/{code}/values",
            params=params,
        )
        response.raise_for_status()
        return response.json()

    return agent


# Global agent instance
qa_agent = create_qa_agent()
```

#### 2. Create Conversation Memory

**File**: `ecox-agents/src/ecox_agents/memory/conversation.py`

```python
"""Redis-based conversation memory for Q&A sessions."""

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

import redis.asyncio as redis
import structlog

from ecox_agents.config import settings

logger = structlog.get_logger(__name__)


class ConversationMemory:
    """Manages conversation history in Redis."""

    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or settings.redis_url
        self.ttl = settings.conversation_ttl
        self._client: redis.Redis | None = None

    async def get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url)
        return self._client

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    def _key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"ecox:qa:conversation:{session_id}"

    async def create_session(self) -> str:
        """Create a new conversation session."""
        session_id = str(uuid4())
        client = await self.get_client()

        data = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
            "context": {},
        }

        await client.setex(
            self._key(session_id),
            self.ttl,
            json.dumps(data),
        )

        return session_id

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get conversation session data."""
        client = await self.get_client()
        data = await client.get(self._key(session_id))

        if data is None:
            return None

        return json.loads(data)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to conversation history."""
        client = await self.get_client()
        key = self._key(session_id)

        # Get existing data
        data = await client.get(key)
        if data is None:
            # Session expired, create new
            session_id = await self.create_session()
            data = await client.get(self._key(session_id))

        session_data = json.loads(data)  # type: ignore

        # Add message
        session_data["messages"].append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }
        )

        # Keep last 10 messages for context
        if len(session_data["messages"]) > 10:
            session_data["messages"] = session_data["messages"][-10:]

        # Update context with latest query info
        if metadata:
            session_data["context"].update(metadata)

        # Save with TTL refresh
        await client.setex(key, self.ttl, json.dumps(session_data))

    async def get_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get conversation history for a session."""
        session_data = await self.get_session(session_id)
        if session_data is None:
            return []
        return session_data.get("messages", [])

    async def clear_session(self, session_id: str) -> None:
        """Clear a conversation session."""
        client = await self.get_client()
        await client.delete(self._key(session_id))


# Global memory instance
_memory: ConversationMemory | None = None


def get_conversation_memory() -> ConversationMemory:
    """Get the global conversation memory."""
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory


async def close_conversation_memory() -> None:
    """Close the global conversation memory."""
    global _memory
    if _memory is not None:
        await _memory.close()
        _memory = None
```

#### 3. Create Q&A Service

**File**: `ecox-agents/src/ecox_agents/services/qa.py`

```python
"""Q&A service for dataset queries."""

import httpx
import structlog

from ecox_agents.agents.qa import QADeps, QAResponse, qa_agent
from ecox_agents.config import settings
from ecox_agents.memory.conversation import ConversationMemory

logger = structlog.get_logger(__name__)


class QAService:
    """Service for answering questions about economic data."""

    def __init__(self, memory: ConversationMemory) -> None:
        self.memory = memory

    async def ask(
        self,
        question: str,
        session_id: str | None = None,
    ) -> tuple[QAResponse, str]:
        """Ask a question about economic data.

        Args:
            question: Natural language question
            session_id: Optional session ID for conversation continuity

        Returns:
            Tuple of (response, session_id)
        """
        # Get or create session
        if session_id is None:
            session_id = await self.memory.create_session()
            history_context = ""
        else:
            # Get conversation history for context
            history = await self.memory.get_history(session_id)
            if history:
                history_context = "\n\nPrevious conversation:\n"
                for msg in history[-4:]:  # Last 4 messages
                    role = "User" if msg["role"] == "user" else "Assistant"
                    history_context += f"{role}: {msg['content'][:200]}...\n"
            else:
                history_context = ""

        # Build prompt with history context
        prompt = question
        if history_context:
            prompt = f"{history_context}\n\nCurrent question: {question}"

        # Run agent
        logger.info("Processing Q&A question", session_id=session_id)

        async with httpx.AsyncClient(timeout=60.0) as client:
            deps = QADeps(
                http_client=client,
                platform_url=settings.platform_url,
            )
            result = await qa_agent.run(prompt, deps=deps)

        response = result.output

        # Save to conversation history
        await self.memory.add_message(
            session_id,
            "user",
            question,
            {"data_sources": response.data_sources},
        )
        await self.memory.add_message(
            session_id,
            "assistant",
            response.answer,
            {
                "confidence": response.confidence,
                "data_sources": response.data_sources,
            },
        )

        return response, session_id
```

#### 4. Create Q&A API Routes

**File**: `ecox-agents/src/ecox_agents/api/routes/qa.py`

```python
"""Q&A API routes."""

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ecox_agents.memory.conversation import get_conversation_memory
from ecox_agents.services.qa import QAService

router = APIRouter(prefix="/agents/qa", tags=["qa"])
logger = structlog.get_logger(__name__)


class AskRequest(BaseModel):
    """Request to ask a question."""

    question: str = Field(min_length=3, description="Question to ask")
    session_id: str | None = Field(
        default=None, description="Session ID for conversation continuity"
    )


class AskResponse(BaseModel):
    """Response to a question."""

    answer: str
    data_sources: list[str]
    confidence: str
    data_values: list[dict[str, Any]]
    session_id: str


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """Ask a question about economic data.

    Examples:
    - "What is the inflation rate in Germany?"
    - "Show me GDP growth for France in 2023"
    - "Compare unemployment rates between Spain and Italy"
    """
    memory = get_conversation_memory()
    service = QAService(memory)

    try:
        response, session_id = await service.ask(
            request.question,
            request.session_id,
        )

        return AskResponse(
            answer=response.answer,
            data_sources=response.data_sources,
            confidence=response.confidence,
            data_values=response.data_values,
            session_id=session_id,
        )

    except Exception as e:
        logger.error("Q&A failed", question=request.question, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process question: {str(e)}",
        ) from e


@router.get("/conversations/{session_id}")
async def get_conversation(session_id: str) -> dict[str, Any]:
    """Get conversation history for a session."""
    memory = get_conversation_memory()
    session = await memory.get_session(session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    return session


@router.delete("/conversations/{session_id}")
async def clear_conversation(session_id: str) -> dict[str, str]:
    """Clear a conversation session."""
    memory = get_conversation_memory()
    await memory.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}
```

#### 5. Update Main App

Add Q&A router and memory cleanup:

```python
from ecox_agents.api.routes import health, summarize, qa
from ecox_agents.memory.conversation import close_conversation_memory

# In lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ... startup code ...

    yield

    # Shutdown
    logger.info("Shutting down ecox-agents")
    await close_db_manager()
    await close_conversation_memory()

# Include routers
app.include_router(health.router)
app.include_router(summarize.router, prefix="/api")
app.include_router(qa.router, prefix="/api")
```

### Success Criteria

#### Automated Verification:
- [ ] Type checking passes: `cd ecox-agents && uv run pyright src/`
- [ ] Redis connection works: `redis-cli ping` returns PONG
- [ ] POST /api/agents/qa/ask works: `curl -X POST -H "Content-Type: application/json" -d '{"question": "What datasets are available?"}' http://localhost:8001/api/agents/qa/ask`

#### Manual Verification:
- [ ] Question "What is inflation in Germany?" returns relevant data
- [ ] Follow-up question "What about France?" uses conversation context
- [ ] Session persists after service restart (Redis)
- [ ] Clear session endpoint works

**Implementation Note**: Pause here for manual verification before proceeding to Phase 4.

---

## Phase 4: UI Integration

### Overview
Add UI components to ecox-client for summarization and Q&A features.

### Changes Required

#### 1. Create Agents Client

**File**: `ecox-client/src/ecox_client/infrastructure/agents_client.py`

```python
"""HTTP client for ecox-agents service."""

from typing import Any

import httpx
import structlog

from ecox_client.config import settings

logger = structlog.get_logger(__name__)


class AgentsClientError(Exception):
    """Error from agents service."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AgentsClient:
    """Client for ecox-agents API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or settings.agents_url).rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Accept": "application/json"},
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make HTTP request to agents service."""
        try:
            response = await self.client.request(
                method, path, json=json, params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise AgentsClientError(
                f"Agents API error: {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise AgentsClientError(f"Agents connection error: {e}") from e

    # Health
    async def health(self) -> dict[str, Any]:
        """Check agents service health."""
        return await self._request("GET", "/health")

    # Summarization
    async def summarize_news(
        self, entry_id: int, force_regenerate: bool = False
    ) -> dict[str, Any]:
        """Summarize a news entry."""
        params = {"force_regenerate": force_regenerate} if force_regenerate else None
        return await self._request(
            "POST", f"/api/agents/summarize/news/{entry_id}", params=params
        )

    async def get_cached_summary(self, entry_id: int) -> dict[str, Any] | None:
        """Get cached summary if exists."""
        try:
            return await self._request("GET", f"/api/agents/summarize/news/{entry_id}")
        except AgentsClientError as e:
            if e.status_code == 404:
                return None
            raise

    # Q&A
    async def ask_question(
        self, question: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """Ask a question about economic data."""
        payload: dict[str, Any] = {"question": question}
        if session_id:
            payload["session_id"] = session_id
        return await self._request("POST", "/api/agents/qa/ask", json=payload)

    async def get_conversation(self, session_id: str) -> dict[str, Any]:
        """Get conversation history."""
        return await self._request("GET", f"/api/agents/qa/conversations/{session_id}")

    async def clear_conversation(self, session_id: str) -> dict[str, str]:
        """Clear conversation."""
        return await self._request(
            "DELETE", f"/api/agents/qa/conversations/{session_id}"
        )


# Global client instance
_client: AgentsClient | None = None


def get_agents_client() -> AgentsClient:
    """Get the global agents client."""
    global _client
    if _client is None:
        _client = AgentsClient()
    return _client


async def close_agents_client() -> None:
    """Close the global agents client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
```

#### 2. Update Client Config

**File**: `ecox-client/src/ecox_client/config.py`

Add agents URL:

```python
# Agents service
agents_url: str = Field(
    default="http://localhost:8001", description="Agents service URL"
)
agents_timeout: float = Field(
    default=60.0, description="Agents API timeout (longer for AI operations)"
)
```

#### 3. Create Agents UI Routes

**File**: `ecox-client/src/ecox_client/api/routes/agents.py`

```python
"""UI routes for agents features."""

from typing import Any

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ecox_client.api.templates import get_template_context, templates
from ecox_client.infrastructure.agents_client import (
    AgentsClientError,
    get_agents_client,
)

router = APIRouter(tags=["agents"])
logger = structlog.get_logger(__name__)


@router.post("/agents/summarize/news/{entry_id}", response_class=HTMLResponse)
async def summarize_news_entry(
    request: Request,
    entry_id: int,
    force_regenerate: bool = False,
) -> HTMLResponse:
    """Generate summary for a news entry."""
    client = get_agents_client()

    try:
        result = await client.summarize_news(entry_id, force_regenerate)

        return templates.TemplateResponse(
            "partials/_summary_result.html",
            get_template_context(
                request,
                summary=result,
                error=None,
            ),
        )

    except AgentsClientError as e:
        logger.error("Summarization failed", entry_id=entry_id, error=str(e))
        return templates.TemplateResponse(
            "partials/_summary_result.html",
            get_template_context(
                request,
                summary=None,
                error=str(e),
            ),
        )


@router.get("/ask", response_class=HTMLResponse)
async def ask_page(request: Request) -> HTMLResponse:
    """Render the Q&A page."""
    return templates.TemplateResponse(
        "partials/_qa_panel.html",
        get_template_context(request),
    )


@router.post("/agents/qa/ask", response_class=HTMLResponse)
async def ask_question(
    request: Request,
) -> HTMLResponse:
    """Process Q&A question and return result."""
    form = await request.form()
    question = str(form.get("question", ""))
    session_id = str(form.get("session_id", "")) or None

    if not question.strip():
        return templates.TemplateResponse(
            "partials/_qa_response.html",
            get_template_context(
                request,
                response=None,
                error="Please enter a question",
            ),
        )

    client = get_agents_client()

    try:
        result = await client.ask_question(question, session_id)

        return templates.TemplateResponse(
            "partials/_qa_response.html",
            get_template_context(
                request,
                response=result,
                question=question,
                error=None,
            ),
        )

    except AgentsClientError as e:
        logger.error("Q&A failed", question=question, error=str(e))
        return templates.TemplateResponse(
            "partials/_qa_response.html",
            get_template_context(
                request,
                response=None,
                question=question,
                error=str(e),
            ),
        )


@router.post("/agents/qa/clear", response_class=HTMLResponse)
async def clear_conversation(request: Request) -> HTMLResponse:
    """Clear conversation and return fresh Q&A panel."""
    form = await request.form()
    session_id = str(form.get("session_id", ""))

    if session_id:
        client = get_agents_client()
        try:
            await client.clear_conversation(session_id)
        except AgentsClientError:
            pass  # Ignore errors when clearing

    return templates.TemplateResponse(
        "partials/_qa_panel.html",
        get_template_context(request, cleared=True),
    )
```

#### 4. Create Summary Result Template

**File**: `ecox-client/templates/partials/_summary_result.html`

```html
{% if error %}
<div class="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
    <p class="text-sm text-red-600 dark:text-red-400">
        {{ t('agents.summary_error') }}: {{ error }}
    </p>
</div>
{% elif summary %}
<div class="mt-4 space-y-4">
    <!-- Summary Header -->
    <div class="flex items-center justify-between">
        <h4 class="text-sm font-semibold text-slate-700 dark:text-slate-300">
            {{ t('agents.ai_summary') }}
        </h4>
        <div class="flex items-center gap-2">
            <!-- Sentiment Badge -->
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
                {% if summary.sentiment == 'positive' %}
                bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300
                {% elif summary.sentiment == 'negative' %}
                bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-300
                {% else %}
                bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-300
                {% endif %}">
                {{ summary.sentiment }}
            </span>
            {% if summary.cached %}
            <span class="text-xs text-slate-500" title="{{ summary.cached_at }}">
                {{ t('agents.cached') }}
            </span>
            {% endif %}
        </div>
    </div>

    <!-- Summary Text -->
    <div class="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
        <p class="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{{ summary.summary }}</p>
    </div>

    <!-- Key Indicators -->
    {% if summary.key_indicators %}
    <div>
        <h5 class="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">
            {{ t('agents.key_indicators') }}
        </h5>
        <div class="flex flex-wrap gap-2">
            {% for indicator in summary.key_indicators %}
            <span class="px-2 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 text-xs rounded">
                {{ indicator }}
            </span>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <!-- Extracted Data -->
    {% if summary.extracted_data %}
    <div>
        <h5 class="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-2">
            {{ t('agents.extracted_data') }}
        </h5>
        <dl class="grid grid-cols-2 gap-2 text-sm">
            {% for key, value in summary.extracted_data.items() %}
            <div class="flex justify-between">
                <dt class="text-slate-500 dark:text-slate-400">{{ key }}:</dt>
                <dd class="font-medium text-slate-900 dark:text-slate-100">{{ value }}</dd>
            </div>
            {% endfor %}
        </dl>
    </div>
    {% endif %}

    <!-- Regenerate Button -->
    <div class="flex justify-end">
        <button
            hx-post="/api/agents/summarize/news/{{ summary.entry_id }}?force_regenerate=true"
            hx-target="#summary-container"
            hx-swap="innerHTML"
            hx-indicator="#summary-spinner"
            class="text-xs text-blue-600 dark:text-blue-400 hover:underline">
            {{ t('agents.regenerate') }}
        </button>
    </div>
</div>
{% endif %}
```

#### 5. Create Q&A Panel Template

**File**: `ecox-client/templates/partials/_qa_panel.html`

```html
<div x-data="{
    sessionId: null,
    messages: [],
    loading: false
}" class="h-full flex flex-col">
    <!-- Header -->
    <div class="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100">
            {{ t('agents.ask_title') }}
        </h2>
        <p class="text-sm text-slate-500 dark:text-slate-400">
            {{ t('agents.ask_description') }}
        </p>
    </div>

    <!-- Messages Area -->
    <div id="qa-messages" class="flex-1 overflow-y-auto p-4 space-y-4">
        <!-- Example Questions (shown when empty) -->
        <template x-if="messages.length === 0">
            <div class="space-y-3">
                <p class="text-sm text-slate-500 dark:text-slate-400">
                    {{ t('agents.example_questions') }}:
                </p>
                <div class="space-y-2">
                    <button @click="$refs.questionInput.value = 'What is the inflation rate in Germany?'; $refs.questionInput.focus()"
                            class="block w-full text-left px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-slate-700 dark:text-slate-300">
                        "What is the inflation rate in Germany?"
                    </button>
                    <button @click="$refs.questionInput.value = 'Show me GDP growth for France in 2023'; $refs.questionInput.focus()"
                            class="block w-full text-left px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-slate-700 dark:text-slate-300">
                        "Show me GDP growth for France in 2023"
                    </button>
                    <button @click="$refs.questionInput.value = 'Compare unemployment in Spain and Italy'; $refs.questionInput.focus()"
                            class="block w-full text-left px-3 py-2 text-sm bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg text-slate-700 dark:text-slate-300">
                        "Compare unemployment in Spain and Italy"
                    </button>
                </div>
            </div>
        </template>

        <!-- Conversation History -->
        <div id="qa-history"></div>
    </div>

    <!-- Input Area -->
    <div class="px-4 py-3 border-t border-slate-200 dark:border-slate-700">
        <form hx-post="/api/agents/qa/ask"
              hx-target="#qa-history"
              hx-swap="beforeend"
              hx-indicator="#qa-spinner"
              @htmx:after-request="$refs.questionInput.value = ''; messages.push(1)">
            <input type="hidden" name="session_id" :value="sessionId">
            <div class="flex gap-2">
                <input
                    x-ref="questionInput"
                    type="text"
                    name="question"
                    placeholder="{{ t('agents.ask_placeholder') }}"
                    class="flex-1 px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg
                           bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100
                           focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                    minlength="3">
                <button
                    type="submit"
                    class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
                           disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
                    <span id="qa-spinner" class="htmx-indicator">
                        <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                        </svg>
                    </span>
                    {{ t('agents.ask_button') }}
                </button>
            </div>
        </form>

        <!-- Clear Button -->
        <div class="mt-2 flex justify-end" x-show="messages.length > 0">
            <button
                hx-post="/api/agents/qa/clear"
                hx-target="#qa-messages"
                hx-swap="innerHTML"
                hx-vals='{"session_id": sessionId}'
                @click="sessionId = null; messages = []"
                class="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
                {{ t('agents.clear_conversation') }}
            </button>
        </div>
    </div>
</div>
```

#### 6. Create Q&A Response Template

**File**: `ecox-client/templates/partials/_qa_response.html`

```html
{% if error %}
<!-- Error Message -->
<div class="flex gap-3 mb-4">
    <div class="flex-shrink-0 w-8 h-8 rounded-full bg-red-100 dark:bg-red-900/50 flex items-center justify-center">
        <svg class="w-4 h-4 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
    </div>
    <div class="flex-1 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
        <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
    </div>
</div>
{% else %}
<!-- User Question -->
<div class="flex gap-3 mb-4">
    <div class="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center">
        <svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
        </svg>
    </div>
    <div class="flex-1 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <p class="text-sm text-slate-900 dark:text-slate-100">{{ question }}</p>
    </div>
</div>

<!-- AI Response -->
<div class="flex gap-3 mb-4">
    <div class="flex-shrink-0 w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/50 flex items-center justify-center">
        <svg class="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
        </svg>
    </div>
    <div class="flex-1 space-y-3">
        <!-- Answer -->
        <div class="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <p class="text-sm text-slate-900 dark:text-slate-100 whitespace-pre-wrap">{{ response.answer }}</p>
        </div>

        <!-- Data Sources -->
        {% if response.data_sources %}
        <div class="flex flex-wrap gap-2">
            {% for source in response.data_sources %}
            <span class="px-2 py-0.5 text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 rounded">
                {{ source }}
            </span>
            {% endfor %}
        </div>
        {% endif %}

        <!-- Confidence -->
        <div class="text-xs text-slate-500 dark:text-slate-400">
            {{ t('agents.confidence') }}: {{ response.confidence }}
        </div>
    </div>
</div>

<!-- Store session ID for follow-ups -->
<script>
    // Update Alpine.js state with session ID
    const qaPanel = document.querySelector('[x-data]');
    if (qaPanel && qaPanel.__x) {
        qaPanel.__x.$data.sessionId = '{{ response.session_id }}';
    }
</script>
{% endif %}
```

#### 7. Add Translations

**File**: `ecox-client/locales/en.json` (add to existing)

```json
{
  "agents": {
    "ai_summary": "AI Summary",
    "summary_error": "Failed to generate summary",
    "cached": "Cached",
    "regenerate": "Regenerate",
    "key_indicators": "Key Indicators",
    "extracted_data": "Extracted Data",
    "summarize_button": "Summarize",
    "ask_title": "Ask about Economic Data",
    "ask_description": "Ask questions in natural language and get answers from our datasets",
    "ask_placeholder": "Ask a question about economic data...",
    "ask_button": "Ask",
    "example_questions": "Example questions",
    "clear_conversation": "Clear conversation",
    "confidence": "Confidence",
    "data_sources": "Data Sources"
  }
}
```

#### 8. Update News Entry Modal

**File**: `ecox-client/templates/partials/_news_entry_modal.html`

Add summarize button and container in the modal body:

```html
<!-- Add after content section -->
{% if entry.content_full %}
<div class="mt-6 border-t border-slate-200 dark:border-slate-700 pt-4">
    <div class="flex items-center justify-between mb-2">
        <h4 class="text-sm font-semibold text-slate-700 dark:text-slate-300">
            {{ t('agents.ai_summary') }}
        </h4>
        <button
            hx-post="/api/agents/summarize/news/{{ entry.id }}"
            hx-target="#summary-container"
            hx-swap="innerHTML"
            hx-indicator="#summary-spinner"
            class="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700">
            <span id="summary-spinner" class="htmx-indicator">
                <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
            </span>
            {{ t('agents.summarize_button') }}
        </button>
    </div>
    <div id="summary-container">
        <!-- Summary will be loaded here -->
    </div>
</div>
{% endif %}
```

#### 9. Add Ask Tab to Main Page

**File**: `ecox-client/templates/pages/index.html`

Add "Ask" tab button and panel:

```html
<!-- In tab buttons section -->
<button @click="setTab('ask')"
        :class="{ 'border-blue-500 text-blue-600 dark:text-blue-400': activeTab === 'ask',
                  'border-transparent text-slate-500 hover:text-slate-700': activeTab !== 'ask' }"
        class="flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors">
    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
    </svg>
    {{ t('tabs.ask') }}
</button>

<!-- In tab panels section -->
<div x-show="activeTab === 'ask'" x-cloak class="h-[600px]">
    <div hx-get="/api/ask" hx-trigger="load once" hx-indicator="#global-spinner">
        <!-- Loading skeleton -->
        <div class="animate-pulse p-4 space-y-4">
            <div class="h-6 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
            <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2"></div>
            <div class="h-32 bg-slate-200 dark:bg-slate-700 rounded"></div>
        </div>
    </div>
</div>
```

#### 10. Update Client Main to Include Agents Routes

**File**: `ecox-client/src/ecox_client/main.py`

```python
from ecox_client.api.routes import ui, events, agents
from ecox_client.infrastructure.agents_client import close_agents_client

# In lifespan shutdown:
await close_agents_client()

# Include routers:
app.include_router(agents.router, prefix="/api", tags=["agents"])
```

#### 11. Update podman-compose for Client

Add agents URL environment variable:

```yaml
  client:
    # ... existing config ...
    environment:
      ECOX_CLIENT_PLATFORM_URL: http://platform:8000
      ECOX_CLIENT_AGENTS_URL: http://agents:8001
      # ... other vars ...
```

### Success Criteria

#### Automated Verification:
- [ ] Client starts with new routes: `uv run python -m ecox_client.main`
- [ ] Templates render without errors
- [ ] No pyright errors in new code

#### Manual Verification:
- [ ] "Summarize" button appears in news entry modal
- [ ] Clicking "Summarize" generates and displays summary
- [ ] "Ask" tab appears in navigation
- [ ] Q&A interface loads and example questions work
- [ ] Conversation history persists within session
- [ ] Dark mode works correctly for all new components

---

## Testing Strategy

### Unit Tests
- Agent output validation (NewsSummary, QAResponse)
- Cache hash computation
- Conversation memory operations

### Integration Tests
- End-to-end summarization flow (mock LLM)
- Q&A with mock platform responses
- Cache retrieval and invalidation

### Manual Testing Steps
1. Start all services: `podman-compose up -d`
2. Navigate to news section, click an entry
3. Click "Summarize" button, verify summary appears
4. Navigate to "Ask" tab
5. Type "What is inflation in Germany?" and submit
6. Verify answer includes data sources
7. Ask follow-up "What about France?"
8. Verify context is maintained
9. Click "Clear conversation" and verify reset

## Performance Considerations

- **LLM Response Time**: 5-15 seconds expected, UI shows loading state
- **Summary Caching**: Avoids redundant LLM calls, cache hit should be instant
- **Redis Memory**: Conversations expire after 30 minutes (configurable)
- **Connection Pooling**: HTTP clients use connection pooling

## Migration Notes

- No existing data to migrate
- New `news_summary_cache` table created automatically
- Redis starts empty, conversations build up over time

## References

- Original requirements: `docs/requirements/epic14_agentic_features.md`
- Architecture ADR: `docs/adrs/agentic-system-adr.md`
- Pydantic AI docs: https://ai.pydantic.dev/
- Similar patterns: `ecox-client/src/ecox_client/infrastructure/platform_client.py`
