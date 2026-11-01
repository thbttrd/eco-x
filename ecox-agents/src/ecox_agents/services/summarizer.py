"""Summarization service with caching."""

import json

import httpx
import structlog
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_agents.agents.summarizer import (
    NewsSummary,
    SummarizerDeps,
    get_summarizer_agent,
)
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
        statement = select(NewsSummaryCache).where(NewsSummaryCache.entry_id == entry_id)
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
            response = await client.get(f"{settings.platform_url}/api/news/entries/{entry_id}")
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

            result = await get_summarizer_agent().run(prompt, deps=deps)
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
