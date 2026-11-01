"""AI agents for ecox-agents service."""

from ecox_agents.agents.summarizer import (
    NewsSummary,
    SummarizerDeps,
    create_summarizer_agent,
    get_summarizer_agent,
)

__all__ = [
    "NewsSummary",
    "SummarizerDeps",
    "create_summarizer_agent",
    "get_summarizer_agent",
]
