# ADR: Agentic AI System Architecture

**Date:** 2025-12-28
**Status:** Proposed
**Deciders:** Development Team
**Technical Story:** Add agentic AI capabilities to eco-x platform

---

## Context and Problem Statement

The eco-x platform currently focuses on data aggregation from economic data sources (Eurostat, FRED, OECD, etc.) and news collection. We want to extend the platform with agentic AI capabilities to provide intelligent analysis and automation.

### Proposed Agentic Features

1. **News Summarization** - Synthesize lengthy news entries (e.g., monetary policy decisions) into concise summaries (<500 words)
2. **Sentiment Analysis** - Classify text with sentiment tags (positive perspective, negative perspective, neutral)
3. **Information Extraction** - Extract crucial data points from text (interest rates, market growth figures, key dates)
4. **Dataset Q&A** - Automatically search and query datasets to answer user questions
5. **Economic Report Generation** - Create comprehensive reports via multi-step reasoning workflows

---

## Decision Drivers

1. **Self-Hostable** - Must be fully deployable on-premises without SaaS dependencies
2. **No Paywall** - All features must be available in open-source versions
3. **Cost Optimization** - Ability to use Claude Code subscription instead of per-token API pricing
4. **Type Safety** - Must integrate well with existing Pydantic/pyright-based codebase
5. **Async Support** - Must support async/await patterns used throughout eco-x
6. **Production Ready** - Framework must be stable enough for production use

---

## Current Architecture Context

### Existing Components

| Component | Tech Stack | Purpose | LOC |
|-----------|-----------|---------|-----|
| **ecox-data-platform** | FastAPI, SQLModel, AsyncPG | REST API + background workers | ~12,000 |
| **ecox-client** | FastAPI, Jinja2, htmx, Alpine.js | Web UI with SQLite cache | ~2,000 |
| **ecox-shared** | Pydantic, SQLModel, httpx | Shared models & HTTP client | ~1,200 |

### Existing Strengths for AI Integration

- Full async/await infrastructure
- Type-safe Pydantic models everywhere
- Well-defined REST APIs (suitable for agent tools)
- Structured logging with structlog
- No existing AI/ML code (clean slate)

---

## Decision 1: Component Architecture

### Question

Should agentic features be a new component or integrated into existing components?

### Considered Options

#### Option A: New Component `ecox-agents` (RECOMMENDED)

```
eco-x/
├── ecox-shared/              # Existing
├── ecox-data-platform/       # Existing
├── ecox-client/              # Existing
└── ecox-agents/              # NEW
    ├── src/ecox_agents/
    │   ├── agents/           # Agent definitions
    │   ├── tools/            # Tools (query datasets, search news)
    │   ├── workflows/        # Multi-step reasoning
    │   ├── memory/           # Conversation history
    │   └── api/              # FastAPI endpoints
    ├── pyproject.toml
    └── tests/
```

**Pros:**
- Clean separation of concerns
- Independent scaling
- Different dependencies don't bloat platform
- Easier testing (mock entire platform API)
- Future-proof (can swap AI frameworks without touching data layer)
- Team specialization possible

**Cons:**
- Additional service to deploy
- Network latency for tool calls
- More infrastructure complexity

#### Option B: Integrate into `ecox-data-platform`

```
ecox-data-platform/src/ecox_platform/
├── agents/
│   ├── agent.py
│   ├── tools.py
│   └── memory.py
└── api/routes/
    └── agents.py
```

**Pros:**
- Single deployment
- Direct database access for tools
- Simpler for small features

**Cons:**
- Mixed concerns (data + AI)
- Dependency bloat
- Harder to scale independently
- AI failures can affect data operations

### Decision Outcome

**Chosen Option: A - New Component `ecox-agents`**

The use cases (multi-step reasoning, sentiment analysis, report generation) are substantial enough to warrant clean separation. The async patterns in the codebase make inter-service communication efficient.

---

## Decision 2: AI Agent Framework

### Considered Options

#### Option 1: Pydantic AI (RECOMMENDED - Primary Framework)

**Description:** Python agent framework by the Pydantic team, bringing "FastAPI feeling" to agent development.

**License:** MIT (fully open source)

**Key Features:**
- Type-safe structured outputs with Pydantic models
- Model-agnostic: OpenAI, Anthropic, Gemini, Ollama, etc.
- Dependency injection (familiar from FastAPI)
- MCP protocol support
- Durable execution for long-running workflows
- Graph support for complex workflows

**Self-Hosting:**
- Core framework: Fully self-hostable, no paywall
- Pydantic AI Gateway: AGPL-3.0, self-hostable
- Observability: Optional Logfire or standard OpenTelemetry

**Example Usage:**
```python
from pydantic_ai import Agent
from pydantic import BaseModel

class EconomicSummary(BaseModel):
    summary: str
    key_indicators: list[str]
    sentiment: Literal["positive", "negative", "neutral"]

agent = Agent(
    'anthropic:claude-sonnet-4-20250514',
    result_type=EconomicSummary,
    system_prompt="You are an economic analyst..."
)

@agent.tool
async def query_dataset(ctx, source: str, code: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"http://platform:8000/api/datasets/{source}/{code}/values")
        return resp.json()
```

**Why Best Fit:**
- Codebase is already Pydantic-native
- Strict type safety matches pyright configuration
- FastAPI patterns team already knows
- Simpler learning curve

#### Option 2: LangGraph (For Complex Workflows)

**Description:** Graph-based agent orchestration from LangChain team.

**License:** MIT (library), LangSmith is proprietary

**Key Features:**
- State machine-based workflow execution
- Built-in persistence and checkpointing
- Human-in-the-loop support
- Multi-step reasoning with branching

**Self-Hosting:**
- LangGraph library: Fully self-hostable, MIT license
- LangSmith (observability): Requires Enterprise license for self-hosting
- Alternative: Use Langfuse (open source) for observability

**Example Usage:**
```python
from langgraph.graph import StateGraph

class ReportState(TypedDict):
    news_summary: str
    data_analysis: str
    sentiment: str
    final_report: str

graph = StateGraph(ReportState)
graph.add_node("fetch_news", fetch_news_node)
graph.add_node("analyze_data", analyze_data_node)
graph.add_node("compile_report", compile_report_node)
```

**When to Use:**
- Multi-step report generation
- Complex conditional logic
- Human-in-the-loop workflows

#### Option 3: Claude Agent SDK

**Description:** Anthropic's SDK providing programmatic access to Claude Code's agent harness.

**License:** MIT

**Key Features:**
- Same agent loop as Claude Code
- Built-in tools (file ops, web search, code execution)
- Custom tools via MCP servers
- In-process or subprocess execution

**Cost Advantage:**
- Uses Claude Code authentication (subscription-based)
- Potentially significant savings vs per-token API pricing

**Example Usage:**
```python
from claude_agent_sdk import ClaudeSDKClient

client = ClaudeSDKClient()

@client.tool
async def search_news(query: str) -> list[dict]:
    # Call eco-x API
    ...

async for message in client.query("Summarize ECB decision", tools=[search_news]):
    print(message)
```

#### Option 4: CrewAI

**Description:** Role-based multi-agent framework.

**License:** MIT

**Key Features:**
- Team-based agent orchestration
- Role-driven design (Researcher, Analyst, Writer)
- Both self-organizing and scripted modes

**When to Use:**
- Complex multi-perspective analysis
- Role-based collaboration scenarios

#### Option 5: OpenAI Agents SDK

**Description:** OpenAI's framework for multi-agent workflows.

**License:** MIT

**Key Features:**
- Handoffs between agents
- Built-in guardrails
- Tracing support

**Consideration:**
- OpenAI-first (though supports other providers via compatible APIs)
- Less aligned with Claude-based strategy

### Framework Comparison Matrix

| Framework | Type Safety | Multi-Agent | Self-Host | Learning Curve | Best For |
|-----------|-------------|-------------|-----------|----------------|----------|
| **Pydantic AI** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | Low | Structured outputs |
| **LangGraph** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | High | Complex workflows |
| **Claude Agent SDK** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | Low | Claude-native agents |
| **CrewAI** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Medium | Role-based teams |
| **OpenAI SDK** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Low | OpenAI ecosystem |

### Decision Outcome

**Chosen Options:**
1. **Primary Framework: Pydantic AI** - Best match for existing codebase patterns
2. **LLM Backend: Claude Agent SDK** - Use Claude Code subscription for cost optimization
3. **Complex Workflows: LangGraph + Langfuse** - For multi-step report generation (with open-source observability)

---

## Decision 3: LLM Backend & Cost Optimization

### Problem

Direct API usage can be expensive for heavy workloads:
- Claude API (Sonnet 4): ~$3/M input tokens + $15/M output tokens
- Heavy usage (1M input + 200K output daily): ~$540/month

### Solution: Claude Code Subscription as Backend

Use Claude Agent SDK or Claude Code CLI as the LLM backend to leverage subscription pricing:
- Claude Max: $100-200/month (unlimited within fair use)
- Potential savings: 60-80%

### Integration Approaches

#### Approach 1: Claude Agent SDK (Recommended)

```python
from claude_agent_sdk import ClaudeSDKClient

client = ClaudeSDKClient()  # Uses Claude Code auth

async for message in client.query(prompt):
    yield message
```

#### Approach 2: Claude Code Proxy

Use [claude-code-proxy](https://github.com/fuergaosi233/claude-code-proxy) to expose OpenAI-compatible API:

```python
from pydantic_ai.models.openai import OpenAIModel

model = OpenAIModel(
    "claude-code",
    base_url="http://localhost:8080/v1",
    api_key="not-needed"
)
```

#### Approach 3: Subprocess Wrapper

```python
import subprocess

async def call_claude_code(prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)["result"]
```

### Considerations

| Aspect | Claude Code/Agent SDK | Direct API |
|--------|----------------------|------------|
| Pricing | Subscription ($100-200/mo) | Per-token ($$$) |
| Rate Limits | Claude Code limits | Higher API limits |
| Latency | Slightly higher | Lower |
| Best For | Cost optimization | High-throughput |

---

## Decision 4: Observability

### Requirements

- Trace agent executions
- Debug multi-step workflows
- Monitor costs and performance
- Must be self-hostable

### Considered Options

| Tool | License | Self-Host | Features |
|------|---------|-----------|----------|
| **Langfuse** | MIT | ✅ Free | Tracing, evals, prompts |
| **Pydantic Logfire** | Proprietary | ❌ SaaS | Deep Pydantic integration |
| **LangSmith** | Proprietary | ❌ Enterprise only | Full LangChain integration |
| **OpenTelemetry** | Apache 2.0 | ✅ Free | Standard tracing |

### Decision Outcome

**Chosen Option: Langfuse**

- Fully open source and self-hostable
- Compatible with both Pydantic AI and LangGraph
- No licensing costs
- Can run in Docker/Podman alongside other services

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
│  │ htmx/Alpine  │   │ Claude SDK   │   │ News APIs            │ │
│  │              │   │ LangGraph    │   │ Fetch Workers        │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│                            │                      │              │
│                            ▼                      ▼              │
│                     ┌─────────────┐        ┌──────────────┐     │
│                     │  Langfuse   │        │  PostgreSQL  │     │
│                     │ (optional)  │        │              │     │
│                     └─────────────┘        └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### ecox-agents Component Structure

```
ecox-agents/
├── src/ecox_agents/
│   ├── __init__.py
│   ├── config.py              # Settings, LLM provider config
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── summarizer.py      # News summarization agent
│   │   ├── sentiment.py       # Sentiment analysis agent
│   │   ├── extractor.py       # Information extraction agent
│   │   └── qa.py              # Dataset Q&A agent
│   ├── workflows/
│   │   ├── __init__.py
│   │   └── report.py          # Multi-step report generation (LangGraph)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── datasets.py        # Query eco-x datasets
│   │   ├── news.py            # Search/retrieve news
│   │   └── indicators.py      # Get economic indicators
│   ├── memory/
│   │   ├── __init__.py
│   │   └── conversation.py    # Conversation history (SQLite)
│   └── api/
│       ├── __init__.py
│       ├── main.py            # FastAPI app
│       └── routes/
│           ├── agents.py      # /api/agents/* endpoints
│           └── health.py
├── tests/
│   ├── bdd/
│   └── unit/
├── pyproject.toml
└── Dockerfile
```

---

## Use Case to Implementation Mapping

| Use Case | Framework | Implementation |
|----------|-----------|----------------|
| News summarization | Pydantic AI | `agents/summarizer.py` with structured output |
| Sentiment analysis | Pydantic AI | `agents/sentiment.py` with `Literal` type |
| Information extraction | Pydantic AI | `agents/extractor.py` with typed schema |
| Dataset Q&A | Pydantic AI + Tools | `agents/qa.py` with `tools/datasets.py` |
| Economic report | LangGraph | `workflows/report.py` with state machine |

---

## Implementation Phases

### Phase 1: Foundation
- Create `ecox-agents` component structure
- Set up Pydantic AI with Claude backend
- Implement basic tools (query datasets, search news)
- Add health check and basic API

### Phase 2: Simple Agents
- News summarization agent
- Sentiment analysis agent
- Information extraction agent

### Phase 3: Interactive Features
- Dataset Q&A agent with tool calling
- Conversation memory
- UI integration in ecox-client

### Phase 4: Advanced Workflows
- Multi-step report generation with LangGraph
- Add Langfuse observability
- Human-in-the-loop for report approval

---

## References

### Frameworks

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Pydantic AI GitHub](https://github.com/pydantic/pydantic-ai)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Claude Agent SDK GitHub](https://github.com/anthropics/claude-agent-sdk-python)
- [CrewAI Documentation](https://docs.crewai.com/)

### Comparisons & Best Practices

- [Langfuse: Comparing Open-Source AI Agent Frameworks](https://langfuse.com/blog/2025-03-19-ai-agent-comparison)
- [14 AI Agent Frameworks Compared](https://softcery.com/lab/top-14-ai-agent-frameworks-of-2025-a-founders-guide-to-building-smarter-systems)
- [Building Production-Grade AI Agents in 2025](https://dev.to/zimaxeg/building-production-grade-ai-agents-in-2025-the-complete-technical-guide-512h)
- [UiPath: Best Practices for AI Agents](https://www.uipath.com/blog/ai/agent-builder-best-practices)

### Self-Hosting & Licensing

- [Pydantic Open Source Commitment](https://pydantic.dev/opensource)
- [LangSmith vs Langfuse](https://langfuse.com/faq/all/langsmith-alternative)
- [LangGraph Pricing Guide](https://www.zenml.io/blog/langgraph-pricing)

### Claude Code Integration

- [Claude Code Proxy](https://github.com/fuergaosi233/claude-code-proxy)
- [Claude Code Router](https://github.com/musistudio/claude-code-router)
- [Building Agents with Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)

### Observability

- [Langfuse - Open Source LLM Observability](https://langfuse.com/)
- [OpenTelemetry for LLMs](https://opentelemetry.io/)

---

## Appendix: Cost Comparison

### Scenario: Moderate Usage

**Assumptions:**
- 500K input tokens/day
- 100K output tokens/day
- 30 days/month

**Claude API (Sonnet 4):**
- Input: 500K × 30 × $3/M = $45/month
- Output: 100K × 30 × $15/M = $45/month
- **Total: ~$90/month**

**Claude Max Subscription:**
- **Fixed: $100-200/month**

**Verdict:** At moderate usage, costs are similar. API may be cheaper for light usage, subscription better for heavy usage.

### Scenario: Heavy Usage

**Assumptions:**
- 2M input tokens/day
- 500K output tokens/day

**Claude API:**
- Input: 2M × 30 × $3/M = $180/month
- Output: 500K × 30 × $15/M = $225/month
- **Total: ~$405/month**

**Claude Max Subscription:**
- **Fixed: $100-200/month**

**Verdict:** Subscription saves ~60-75% at heavy usage.
