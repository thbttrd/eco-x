"""Data sources endpoints for the platform API.

Provides information about available data sources and their status.
"""

from datetime import datetime
from typing import Any

from ecox_shared.models import Dataset, SourceMetadata
from ecox_shared.schemas import SourceResponse, SourceStatusResponse
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.api.dependencies import get_session
from ecox_platform.config import settings
from ecox_platform.scheduler import get_fetcher

router = APIRouter(prefix="/sources", tags=["sources"])

# Source display names
SOURCE_NAMES = {
    "eurostat": "Eurostat",
    "fred": "Federal Reserve Economic Data (FRED)",
    "oecd": "OECD Statistics",
    "nbs": "National Bureau of Statistics of China",
    "ons": "UK Office for National Statistics",
}

SOURCE_DESCRIPTIONS = {
    "eurostat": "Statistical office of the European Union",
    "fred": "Economic data from the Federal Reserve Bank of St. Louis",
    "oecd": "OECD statistics and data",
    "nbs": "Official statistics from China's National Bureau of Statistics",
    "ons": "Official statistics from the UK",
}


@router.get("", response_model=list[SourceResponse])
async def list_sources(session: AsyncSession = Depends(get_session)) -> list[SourceResponse]:
    """List all available data sources with their dataset counts.

    Returns:
        List of source information
    """
    # Get dataset counts per source
    count_statement = select(Dataset.source, func.count()).group_by(Dataset.source)
    count_result = await session.execute(count_statement)
    counts: dict[str, int] = dict(count_result.all())  # type: ignore[arg-type]

    # Get last activity per source
    activity_statement = select(Dataset.source, func.max(Dataset.last_fetched)).group_by(
        Dataset.source
    )
    activity_result = await session.execute(activity_statement)
    activities: dict[str, datetime | None] = dict(activity_result.all())  # type: ignore[arg-type]

    # Get total available from source metadata
    metadata_statement = select(SourceMetadata)
    metadata_map = {m.source: m for m in (await session.exec(metadata_statement)).all()}

    sources = []
    for source_code in SOURCE_NAMES:
        metadata = metadata_map.get(source_code)
        sources.append(
            SourceResponse(
                code=source_code,
                name=SOURCE_NAMES[source_code],
                description=SOURCE_DESCRIPTIONS.get(source_code),
                dataset_count=counts.get(source_code, 0),
                total_available=metadata.total_datasets if metadata else None,
                last_activity=activities.get(source_code),
            )
        )

    return sources


@router.get("/{source}", response_model=SourceStatusResponse)
async def get_source_status(
    source: str,
    session: AsyncSession = Depends(get_session),
) -> SourceStatusResponse:
    """Get detailed status for a specific data source.

    Args:
        source: Source code (e.g., 'eurostat')

    Returns:
        Detailed source status including worker information
    """
    if source not in SOURCE_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")

    # Get dataset count
    count_statement = select(func.count()).where(Dataset.source == source)
    dataset_count = (await session.exec(count_statement)).one() or 0

    # Get last activity
    activity_statement = select(func.max(Dataset.last_fetched)).where(Dataset.source == source)
    last_activity = (await session.exec(activity_statement)).one()

    # Get total available from metadata
    metadata_statement = select(SourceMetadata).where(SourceMetadata.source == source)
    metadata = (await session.exec(metadata_statement)).one_or_none()

    # Get worker status
    worker_status = "stopped"
    fetch_queue_size = 0
    recent_errors = 0

    try:
        fetcher = get_fetcher()
        if source in fetcher.workers:
            worker = fetcher.workers[source]
            status = worker.status()
            worker_status = "running" if status["is_running"] else "stopped"
            recent_errors = status["datasets_failed"]
    except Exception:  # nosec B110
        pass

    # Get rate limit from config
    config = settings.get_source_config(source)

    return SourceStatusResponse(
        code=source,
        name=SOURCE_NAMES[source],
        description=SOURCE_DESCRIPTIONS.get(source),
        dataset_count=dataset_count,
        total_available=metadata.total_datasets if metadata else None,
        last_activity=last_activity,
        worker_status=worker_status,
        fetch_queue_size=fetch_queue_size,
        rate_limit=config.rate_limit,
        recent_errors=recent_errors,
    )


@router.post("/{source}/fetch", response_model=dict[str, Any])
async def trigger_fetch_cycle(
    source: str,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Trigger a fetch cycle for a specific data source.

    This runs the fetch cycle in the background and returns immediately.

    Args:
        source: Source code (e.g., 'eurostat')

    Returns:
        Acknowledgment message
    """
    if source not in SOURCE_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown source: {source}")

    try:
        fetcher = get_fetcher()

        async def run_cycle() -> None:
            await fetcher.run_single_cycle(source)

        background_tasks.add_task(run_cycle)

        return {
            "status": "started",
            "source": source,
            "message": f"Fetch cycle triggered for {source}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger fetch cycle: {str(e)}",
        ) from e
