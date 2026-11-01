"""News event broadcasting for SSE updates.

Provides a simple in-memory event queue for broadcasting news updates
to connected SSE clients.

Updated for hierarchical structure: Category → Source → Section → Entry
"""

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class NewsEvent:
    """A news event to be broadcast to SSE clients.

    Events track section-level changes since sections are the fetchable unit.
    """

    event_type: str  # "new_entries", "fetch_complete", "fetch_error"
    section_id: int | None = None
    section_title: str | None = None
    source_id: int | None = None
    source_title: str | None = None
    entry_count: int = 0
    entries_new: int = 0
    error: str | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_type": self.event_type,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "source_id": self.source_id,
            "source_title": self.source_title,
            "entry_count": self.entry_count,
            "entries_new": self.entries_new,
            "error": self.error,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class NewsEventManager:
    """Manager for news event broadcasting.

    Uses asyncio queues to broadcast events to multiple subscribers.
    """

    def __init__(self, max_queue_size: int = 100) -> None:
        """Initialize the event manager.

        Args:
            max_queue_size: Maximum events to queue per subscriber
        """
        self.max_queue_size = max_queue_size
        self._subscribers: list[asyncio.Queue[NewsEvent | None]] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> AsyncGenerator[NewsEvent, None]:
        """Subscribe to news events.

        Yields news events as they are published.

        Yields:
            NewsEvent objects
        """
        queue: asyncio.Queue[NewsEvent | None] = asyncio.Queue(maxsize=self.max_queue_size)

        async with self._lock:
            self._subscribers.append(queue)

        logger.info(
            "SSE subscriber added",
            subscriber_count=len(self._subscribers),
        )

        try:
            while True:
                event = await queue.get()
                if event is None:
                    # Shutdown signal
                    break
                yield event
        finally:
            async with self._lock:
                self._subscribers.remove(queue)
            logger.info(
                "SSE subscriber removed",
                subscriber_count=len(self._subscribers),
            )

    async def publish(self, event: NewsEvent) -> None:
        """Publish an event to all subscribers.

        Args:
            event: The event to broadcast
        """
        async with self._lock:
            for queue in self._subscribers:
                try:
                    # Non-blocking put - if queue is full, skip this subscriber
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("SSE subscriber queue full, dropping event")

        if self._subscribers:
            logger.debug(
                "Published news event",
                event_type=event.event_type,
                subscriber_count=len(self._subscribers),
            )

    async def shutdown(self) -> None:
        """Shutdown all subscribers."""
        async with self._lock:
            for queue in self._subscribers:
                try:
                    queue.put_nowait(None)  # Send shutdown signal
                except asyncio.QueueFull:
                    pass


# Global event manager instance
_event_manager: NewsEventManager | None = None


def get_event_manager() -> NewsEventManager:
    """Get the global news event manager.

    Returns:
        NewsEventManager instance
    """
    global _event_manager
    if _event_manager is None:
        _event_manager = NewsEventManager()
    return _event_manager


async def publish_news_event(event: NewsEvent) -> None:
    """Publish a news event to all subscribers.

    Convenience function for publishing events.

    Args:
        event: The event to publish
    """
    manager = get_event_manager()
    await manager.publish(event)
