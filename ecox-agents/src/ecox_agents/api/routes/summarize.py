"""Summarization API routes."""

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_agents.api.dependencies import get_session
from ecox_agents.models.summary import SummaryResponse
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
        raise HTTPException(status_code=500, detail=f"Failed to summarize entry: {str(e)}") from e


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
