# ADR: Agentic AI System Architecture

**Date:** 2026-01-03 (Updated from 2025-12-28)
**Status:** Accepted
**Deciders:** Development Team
**Context Commit:** 5de85412d455d5d7e9cccdd4a2bebd518b28a6a5

---

## Context and Problem Statement

The eco-x platform currently focuses on data aggregation from economic data sources (Eurostat, FRED, OECD, etc.) and news collection. We want to extend the platform with agentic AI capabilities to provide intelligent analysis and automation.

### Proposed Agentic Features

1. **News Summarization** - Synthesize lengthy news entries (e.g., monetary policy decisions) into concise summaries (<500 words)
2. **Sentiment Analysis** - Classify text with sentiment tags (positive, negative, neutral)
3. **Information Extraction** - Extract crucial data points from text (interest rates, market growth figures)
4. **Dataset Q&A** - Automatically search and query datasets to answer user questions
5. **Economic Report Generation** - Create comprehensive reports via multi-step reasoning workflows (Phase 2)

---

## Decision Drivers

1. **Self-Hostable** - Must be fully deployable on-premises without SaaS dependencies
2. **No Paywall** - All features must be available in open-source versions
3. **Cost Optimization** - Support both Claude API and Claude Code subscription
4. **Type Safety** - Must integrate well with existing Pydantic/pyright-based codebase
5. **Async Support** - Must support async/await patterns used throughout eco-x
6. **Production Ready** - Framework must be stable enough for production use

---

## Current Architecture Context

### Existing Components

| Component | Tech Stack | Purpose |
|-----------|-----------|---------|
| **ecox-data-platform** | FastAPI, SQLModel, AsyncPG | REST API + background workers |
| **ecox-client** | FastAPI, Jinja2, htmx, Alpine.js | Web UI with SQLite cache |
| **ecox-shared** | Pydantic, SQLModel, httpx | Shared models & HTTP client |

### Key Codebase Patterns

- **Config**: `pydantic_settings.BaseSettings` with `env_prefix="ECOX_*"`
- **API**: FastAPI routers with `Depends(get_session)` for DB access
- **Async**: `AsyncSession` with `.exec()`, `asynccontextmanager` lifecycle
- **HTTP**: `ResilientHttpClient` with retry/rate-limiting from ecox-shared
- **Testing**: pytest-bdd with in-memory SQLite fixtures

---

## Decision 1: Component Architecture

### Question

Should agentic features be a new component or integrated into existing components?

### Decision: New Component `ecox-agents`

**Status: CONFIRMED**

```
eco-x/
├── ecox-shared/              # Existing - shared models/schemas
├── ecox-data-platform/       # Existing - data APIs (port 8000)
├── ecox-client/              # Existing - Web UI (port 8080)
└── ecox-agents/              # NEW - AI capabilities (port 8001)
    ├── src/ecox_agents/
    │   ├── __init__.py
    │   ├── config.py              # Settings with ECOX_AGENTS_ prefix
    │   ├── agents/
    │   │   ├── __init__.py
    │   │   ├── summarizer.py      # News summarization
    │   │   ├── sentiment.py       # Sentiment analysis
    │   │   ├── extractor.py       # Information extraction
    │   │   └── qa.py              # Dataset Q&A
    │   ├── tools/
    │   │   ├── __init__.py
    │   │   ├── datasets.py        # Query ecox-data-platform APIs
    │   │   ├── news.py            # Fetch/search news
    │   │   └── indicators.py      # Economic indicators
    │   ├── memory/
    │   │   ├── __init__.py
    │   │   └── conversation.py    # Conversation history
    │   └── api/
    │       ├── __init__.py
    │       ├── main.py            # FastAPI app
    │       └── routes/
    │           ├── agents.py      # /api/agents/* endpoints
    │           └── health.py
    ├── tests/
    │   ├── conftest.py
    │   ├── bdd/
    │   └── unit/
    ├── pyproject.toml
    └── Containerfile
```

### Rationale

| Factor | New Component | Integrated |
|--------|---------------|------------|
| Separation of concerns | ✅ Clean | ❌ Mixed |
| Independent scaling | ✅ Yes | ❌ No |
| Dependency isolation | ✅ AI libs isolated | ❌ Bloats platform |
| Failure isolation | ✅ AI crashes don't affect data | ❌ Risk |
| Testing | ✅ Mock platform API | ❌ Complex |
| Team specialization | ✅ Possible | ❌ Harder |

**Decision**: New component is strongly recommended given the scope (5 use cases) and distinct workload characteristics (long-running LLM calls vs. fast data queries).

---

## Decision 2: AI Agent Framework

### Decision: Pydantic AI (Primary)

**Status: CONFIRMED**

**Version:** v1.0+ (stable since September 2025)
**License:** MIT (fully open source)

### Why Pydantic AI

| Factor | Assessment |
|--------|------------|
| **Type Safety** | ⭐⭐⭐⭐⭐ Best-in-class, native Pydantic integration |
| **Async Support** | ⭐⭐⭐⭐⭐ Async-first with sync wrappers |
| **Self-Hosting** | ⭐⭐⭐⭐⭐ No SaaS dependencies |
| **Codebase Fit** | ⭐⭐⭐⭐⭐ Same patterns as FastAPI |
| **Production Ready** | ⭐⭐⭐⭐⭐ v1.0 with stability guarantees |

### Key Features

- **Structured outputs** with Pydantic models (automatic validation)
- **Dependency injection** via `RunContext` (like FastAPI's `Depends`)
- **Model-agnostic**: Anthropic, OpenAI, Ollama, 25+ providers
- **Tool calling** with type-safe parameters
- **Streaming** support for real-time responses

### Example Implementation

```python
from dataclasses import dataclass
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from typing import Literal
import httpx

# Structured output schema
class NewsSummary(BaseModel):
    summary: str = Field(description="Summary under 500 words")
    sentiment: Literal["positive", "negative", "neutral"]
    key_indicators: list[str]
    interest_rate: float | None = Field(default=None)

# Dependencies (follows FastAPI patterns)
@dataclass
class AgentDeps:
    platform_client: httpx.AsyncClient

# Agent definition
summarizer = Agent(
    'anthropic:claude-sonnet-4-5',
    deps_type=AgentDeps,
    output_type=NewsSummary,
    system_prompt="You are an economic analyst. Summarize news concisely."
)

# Tool to query datasets
@summarizer.tool
async def query_dataset(
    ctx: RunContext[AgentDeps],
    source: str,
    code: str
) -> dict:
    """Query economic dataset from platform."""
    response = await ctx.deps.platform_client.get(
        f"http://platform:8000/api/datasets/{source}/{code}/values"
    )
    return response.json()
```

### LangGraph: Deferred to Phase 2

Complex multi-step workflows (economic reports) will use LangGraph in Phase 2. For Phase 1, Pydantic AI's built-in multi-agent delegation is sufficient.

---

## Decision 3: LLM Backend

### Decision: Dual Claude Support

**Status: CONFIRMED**

Support both Claude API and Claude Agent SDK for flexibility:

| Option | When to Use | Configuration |
|--------|-------------|---------------|
| **Claude API** | Production, high throughput | `ECOX_AGENTS_ANTHROPIC_API_KEY` |
| **Claude Agent SDK** | Cost optimization, heavy usage | Uses Claude Code authentication |

### Configuration

```python
# config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ECOX_AGENTS_")

    # LLM Provider
    llm_provider: Literal["anthropic", "claude-sdk", "openai", "ollama"] = "anthropic"
    llm_model: str = "claude-sonnet-4-5"

    # API Keys (optional based on provider)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434/v1"

    # Platform communication
    platform_url: str = "http://localhost:8000"
```

### Cost Comparison

| Usage Level | Claude API | Claude Max |
|-------------|------------|------------|
| Light (500k tokens/day) | ~$90/month | $100-200/month |
| Heavy (2M tokens/day) | ~$405/month | $100-200/month |

---

## Decision 4: Database Access

### Decision: API-Only

**Status: CONFIRMED**

`ecox-agents` will communicate with `ecox-data-platform` exclusively via REST APIs.

### Rationale

| Factor | API-Only | Direct DB |
|--------|----------|-----------|
| Separation | ✅ Clean | ❌ Coupled |
| Testing | ✅ Mock HTTP | ❌ Complex |
| Security | ✅ API auth | ❌ DB credentials |
| Maintenance | ✅ Contract-based | ❌ Schema coupling |
| Performance | Adequate (async) | Slightly faster |

### Tool Implementation

```python
@dataclass
class AgentDeps:
    http_client: httpx.AsyncClient
    base_url: str = "http://platform:8000"

@agent.tool
async def search_news(ctx: RunContext[AgentDeps], query: str) -> list[dict]:
    """Search news entries."""
    response = await ctx.deps.http_client.get(
        f"{ctx.deps.base_url}/api/news/entries",
        params={"search": query, "limit": 10}
    )
    return response.json()["items"]
```

---

## Decision 5: Observability

### Decision: Langfuse (Self-Hosted)

**Status: CONFIRMED**

**License:** MIT (fully open source)
**Deployment:** Docker container alongside other services

### Integration

```python
import os
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-..."
os.environ["LANGFUSE_SECRET_KEY"] = "sk-..."
os.environ["LANGFUSE_HOST"] = "http://langfuse:3000"

from pydantic_ai.agent import Agent
Agent.instrument_all()  # Enable tracing for all agents
```

### Features

- LLM call tracing and debugging
- Token usage and cost monitoring
- Prompt versioning and evaluation
- No vendor lock-in (OpenTelemetry compatible)

### Container Configuration

```yaml
# podman-compose.yaml addition
langfuse:
  image: langfuse/langfuse:latest
  container_name: ecox-langfuse${ECOX_SUFFIX:-}
  environment:
    DATABASE_URL: postgresql://langfuse:langfuse@postgres:5432/langfuse
    NEXTAUTH_SECRET: ${LANGFUSE_SECRET}
    SALT: ${LANGFUSE_SALT}
  ports:
    - "${ECOX_LANGFUSE_PORT:-3000}:3000"
  depends_on:
    - postgres
```

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         eco-x Platform                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │ ecox-client  │   │ ecox-agents  │   │ ecox-data-platform   │ │
│  │   (8080)     │──▶│   (8001)     │──▶│      (8000)          │ │
│  │              │   │              │   │                      │ │
│  │ Web UI       │   │ Pydantic AI  │   │ Data APIs            │ │
│  │ htmx/Alpine  │   │ Claude API   │   │ News APIs            │ │
│  │              │   │ Claude SDK   │   │ Fetch Workers        │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│                            │                      │              │
│                            ▼                      ▼              │
│                     ┌─────────────┐        ┌──────────────┐     │
│                     │  Langfuse   │        │  PostgreSQL  │     │
│                     │   (3000)    │        │    (5432)    │     │
│                     └─────────────┘        └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Use Case to Implementation Mapping

| Use Case | Agent | Output Type | Tools |
|----------|-------|-------------|-------|
| News summarization | `summarizer.py` | `NewsSummary` | `get_entry`, `search_news` |
| Sentiment analysis | `sentiment.py` | `SentimentResult` | None (text input) |
| Info extraction | `extractor.py` | `ExtractedData` | None (text input) |
| Dataset Q&A | `qa.py` | `QAResponse` | `query_dataset`, `search_datasets` |
| Economic reports | Phase 2 (LangGraph) | `EconomicReport` | All tools |

---

## Implementation Phases

### Phase 1: Foundation (Current)
- [x] Create ADR with architecture decisions
- [ ] Create `ecox-agents` component structure
- [ ] Set up Pydantic AI with Claude backend
- [ ] Implement basic tools (query datasets, search news)
- [ ] Add health check and basic API
- [ ] Add Langfuse observability

### Phase 2: Simple Agents
- [ ] News summarization agent
- [ ] Sentiment analysis agent
- [ ] Information extraction agent

### Phase 3: Interactive Features
- [ ] Dataset Q&A agent with tool calling
- [ ] Conversation memory
- [ ] UI integration in ecox-client

### Phase 4: Advanced Workflows
- [ ] Add LangGraph for multi-step workflows
- [ ] Economic report generation
- [ ] Human-in-the-loop for report approval

---

## References

### Frameworks
- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Pydantic AI GitHub](https://github.com/pydantic/pydantic-ai) - MIT License
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)

### Observability
- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse GitHub](https://github.com/langfuse/langfuse) - MIT License
- [Langfuse + Pydantic AI Integration](https://langfuse.com/integrations/frameworks/pydantic-ai)

### Comparisons
- [Pydantic AI v1 Announcement](https://pydantic.dev/articles/pydantic-ai-v1)
- [AI Agent Framework Comparison - Langfuse](https://langfuse.com/blog/2025-03-19-ai-agent-comparison)
- [LangGraph vs Pydantic AI - ZenML](https://www.zenml.io/blog/pydantic-ai-vs-langgraph)
