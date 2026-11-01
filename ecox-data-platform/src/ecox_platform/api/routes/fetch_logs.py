"""Fetch logs endpoints for the platform API.

Provides access to the fetch operation audit log.
"""

import math
from datetime import datetime
from typing import Any

from ecox_shared.models import FetchLog
from ecox_shared.schemas import FetchLogListResponse, FetchLogResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.api.dependencies import get_session

router = APIRouter(prefix="/fetch-logs", tags=["fetch-logs"])


@router.get("", response_model=FetchLogListResponse)
async def list_fetch_logs(
    source: str | None = Query(default=None, description="Filter by source"),
    dataset_code: str | None = Query(default=None, description="Filter by dataset code"),
    status: str | None = Query(default=None, description="Filter by status"),
    since: datetime | None = Query(default=None, description="Filter logs since this time"),
    until: datetime | None = Query(default=None, description="Filter logs until this time"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> FetchLogListResponse:
    """List fetch logs with optional filtering and pagination.

    Args:
        source: Filter by data source
        dataset_code: Filter by dataset code
        status: Filter by status ('success', 'error', 'partial')
        since: Only include logs after this time
        until: Only include logs before this time
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Paginated list of fetch logs
    """
    statement = select(FetchLog)

    if source:
        statement = statement.where(FetchLog.source == source)
    if dataset_code:
        statement = statement.where(FetchLog.dataset_code == dataset_code)
    if status:
        statement = statement.where(FetchLog.status == status)
    if since:
        statement = statement.where(FetchLog.started_at >= since)
    if until:
        statement = statement.where(FetchLog.started_at <= until)

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total = (await session.exec(count_statement)).one() or 0

    # Apply pagination and ordering (newest first)
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(FetchLog.started_at.desc())  # type: ignore[attr-defined]

    logs = (await session.exec(statement)).all()

    items = [
        FetchLogResponse(
            id=log.id,  # type: ignore[arg-type]
            dataset_code=log.dataset_code,
            source=log.source,
            status=log.status,
            records_fetched=log.records_fetched,
            error_message=log.error_message,
            started_at=log.started_at,
            completed_at=log.completed_at,
            duration_seconds=log.duration_seconds,
        )
        for log in logs
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return FetchLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/summary")
async def get_fetch_summary(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Get a summary of recent fetch operations.

    Args:
        hours: Number of hours to look back (max 168 = 1 week)

    Returns:
        Summary statistics for fetch operations
    """
    from datetime import timedelta

    since = datetime.now() - timedelta(hours=hours)

    # Get counts by status
    status_statement = (
        select(FetchLog.status, func.count())
        .where(FetchLog.started_at >= since)
        .group_by(FetchLog.status)
    )
    status_result = await session.execute(status_statement)
    status_counts: dict[str, int] = dict(status_result.all())  # type: ignore[arg-type]

    # Get counts by source
    source_statement = (
        select(FetchLog.source, func.count())
        .where(FetchLog.started_at >= since)
        .group_by(FetchLog.source)
    )
    source_result = await session.execute(source_statement)
    source_counts: dict[str, int] = dict(source_result.all())  # type: ignore[arg-type]

    # Get total records fetched
    records_statement = select(func.sum(FetchLog.records_fetched)).where(
        FetchLog.started_at >= since, FetchLog.status == "success"
    )
    total_records = (await session.exec(records_statement)).one() or 0

    # Get average duration
    duration_statement = select(func.avg(FetchLog.duration_seconds)).where(
        FetchLog.started_at >= since,
        FetchLog.duration_seconds.isnot(None),  # type: ignore[union-attr]
    )
    avg_duration = (await session.exec(duration_statement)).one()

    return {
        "period_hours": hours,
        "since": since.isoformat(),
        "total_operations": sum(status_counts.values()),
        "by_status": {
            "success": status_counts.get("success", 0),
            "error": status_counts.get("error", 0),
            "partial": status_counts.get("partial", 0),
        },
        "by_source": source_counts,
        "total_records_fetched": total_records,
        "average_duration_seconds": round(avg_duration, 2) if avg_duration else None,
    }
