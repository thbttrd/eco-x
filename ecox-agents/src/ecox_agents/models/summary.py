"""Database models for summary caching."""

import hashlib
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlmodel import Column, Field, SQLModel, Text  # pyright: ignore[reportUnknownVariableType]


def _utc_now() -> datetime:
    """Get current UTC datetime (naive, for PostgreSQL TIMESTAMP WITHOUT TIME ZONE)."""
    return datetime.now(UTC).replace(tzinfo=None)


class NewsSummaryCache(SQLModel, table=True):
    """Cached news summary stored in PostgreSQL."""

    __tablename__ = "news_summary_cache"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    entry_id: int = Field(unique=True, index=True, description="NewsEntry ID")
    summary_text: str = Field(sa_column=Column(Text), description="Generated summary")
    sentiment: str = Field(description="positive/negative/neutral")
    key_indicators: str = Field(default="[]", description="JSON list of indicators")
    extracted_data: str = Field(default="{}", description="JSON dict of extracted data")
    model_version: str = Field(description="Model used for generation")
    content_hash: str = Field(index=True, description="Hash of source content for invalidation")
    created_at: datetime = Field(default_factory=_utc_now)


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
