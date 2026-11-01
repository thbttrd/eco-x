"""News summarization agent."""

from dataclasses import dataclass
from typing import Literal

import httpx
import structlog
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider

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
    # Create model with explicit API key from settings
    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        provider = AnthropicProvider(api_key=settings.anthropic_api_key)
        model = AnthropicModel(settings.llm_model, provider=provider)
    else:
        # Fall back to string-based model (uses env var ANTHROPIC_API_KEY)
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
    async def validate_summary(  # pyright: ignore[reportUnusedFunction]
        ctx: RunContext[SummarizerDeps], output: NewsSummary
    ) -> NewsSummary:
        """Validate summary meets requirements."""
        word_count = len(output.summary.split())
        if word_count > 500:
            raise ModelRetry(f"Summary is {word_count} words. Please condense to under 500 words.")
        if word_count < 30:
            raise ModelRetry("Summary is too brief. Please provide more substantive analysis.")
        return output

    return agent


# Lazy agent instance - created on first use
_summarizer_agent: Agent[SummarizerDeps, NewsSummary] | None = None


def get_summarizer_agent() -> Agent[SummarizerDeps, NewsSummary]:
    """Get or create the summarizer agent (lazy initialization)."""
    global _summarizer_agent
    if _summarizer_agent is None:
        _summarizer_agent = create_summarizer_agent()
    return _summarizer_agent
