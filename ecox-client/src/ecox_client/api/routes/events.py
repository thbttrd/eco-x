"""SSE events endpoint for real-time updates.

Provides Server-Sent Events for the WebUI to maintain a live connection
and receive real-time notifications.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

logger = structlog.get_logger(__name__)

router = APIRouter()


async def event_generator(request: Request) -> AsyncGenerator[dict[str, Any], None]:
    """Generate SSE events with keepalive messages.

    Sends keepalive events every 30 seconds to maintain the connection
    and prevent browser timeout.

    Args:
        request: The incoming request (used to detect client disconnect)

    Yields:
        SSE event dictionaries with event type and data
    """
    logger.info("SSE connection established")

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("SSE client disconnected")
                break

            # Send keepalive event
            yield {"event": "keepalive", "data": "ping"}

            # Wait 30 seconds before next keepalive
            await asyncio.sleep(30)
    except asyncio.CancelledError:
        logger.info("SSE connection cancelled")
    finally:
        logger.info("SSE connection closed")


@router.get("/events")
async def sse_events(request: Request) -> EventSourceResponse:
    """SSE endpoint for real-time updates.

    Establishes a Server-Sent Events connection for the WebUI to receive
    live updates and maintain connection status.

    Returns:
        EventSourceResponse streaming SSE events
    """
    return EventSourceResponse(event_generator(request))
