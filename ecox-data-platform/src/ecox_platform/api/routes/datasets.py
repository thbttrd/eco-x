"""Dataset endpoints for the platform API.

Provides access to datasets and their data values.
"""

import json
import math
from typing import Any

from ecox_shared.models import Dataset, DataValue
from ecox_shared.schemas import (
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetResponse,
    DatasetSyncResponse,
    DataValueListResponse,
    DataValueResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_platform.api.dependencies import get_session

router = APIRouter(prefix="/datasets", tags=["datasets"])


def generate_source_url(source: str, code: str) -> str | None:
    """Generate source URL for datasets without stored URL.

    Args:
        source: Data source name (e.g., "eurostat", "fred")
        code: Dataset code

    Returns:
        URL to the original dataset page, or None if source is unknown or unsupported
    """
    if source == "oecd":
        # OECD Data Explorer doesn't support reliable deep linking
        # Use SDMX dataflow endpoint for dataset metadata
        parts = code.split(",")
        if len(parts) == 3:
            agency, dataflow, version = parts
            return f"https://sdmx.oecd.org/public/rest/dataflow/{agency}/{dataflow}/{version}"
        return None  # Fallback if code format is unexpected

    if source == "nbs":
        # NBS China doesn't support direct browser URLs to specific datasets
        return None

    patterns = {
        "fred": f"https://fred.stlouisfed.org/series/{code}",
        "ons": f"https://www.ons.gov.uk/datasets/{code}",
        "eurostat": f"https://ec.europa.eu/eurostat/databrowser/view/{code}/default/table",
    }
    return patterns.get(source)


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    source: str | None = Query(default=None, description="Filter by source"),
    search: str | None = Query(default=None, description="Search in name and code"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> DatasetListResponse:
    """List datasets with optional filtering and pagination.

    Args:
        source: Filter by data source
        search: Search term for name and code
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Paginated list of datasets
    """
    # Build query
    statement = select(Dataset)

    if source:
        statement = statement.where(Dataset.source == source)

    if search:
        search_term = f"%{search.lower()}%"
        statement = statement.where(
            or_(
                func.lower(Dataset.code).like(search_term),
                func.lower(Dataset.name).like(search_term),
            )
        )

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total = (await session.exec(count_statement)).one() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    statement = statement.offset(offset).limit(page_size).order_by(Dataset.code)

    datasets = (await session.exec(statement)).all()

    # Use record_count from Dataset table directly (no expensive GROUP BY needed)
    # Database results always have IDs, so we assert they're not None
    items = [
        DatasetResponse(
            id=d.id,  # type: ignore[arg-type]
            code=d.code,
            name=d.name,
            source=d.source,
            description=d.description,
            last_fetched=d.last_fetched,
            record_count=d.record_count,
        )
        for d in datasets
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return DatasetListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/all", response_model=DatasetSyncResponse)
async def list_all_datasets(
    source: str | None = Query(default=None, description="Filter by source"),
    since_id: int | None = Query(
        default=None, description="Only return datasets with id > since_id (for incremental sync)"
    ),
    session: AsyncSession = Depends(get_session),
) -> DatasetSyncResponse:
    """Get all datasets or incremental updates for client-side pagination.

    This endpoint returns datasets in a single response for use with
    client-side pagination in the WebUI. Supports incremental fetching
    via the `since_id` parameter to fetch only new datasets.

    Args:
        source: Optional filter by data source
        since_id: Only return datasets with id > since_id (for incremental sync)

    Returns:
        DatasetSyncResponse with items and max_id for next sync
    """
    # Build query
    statement = select(Dataset)

    if source:
        statement = statement.where(Dataset.source == source)

    if since_id is not None:
        statement = statement.where(Dataset.id > since_id)  # type: ignore[operator]

    # Order by id for consistent incremental fetching
    statement = statement.order_by(Dataset.id)  # type: ignore[arg-type]

    datasets = (await session.exec(statement)).all()

    # Use record_count from Dataset table directly (no expensive GROUP BY needed)
    items = [
        DatasetResponse(
            id=d.id,  # type: ignore[arg-type]
            code=d.code,
            name=d.name,
            source=d.source,
            description=d.description,
            last_fetched=d.last_fetched,
            record_count=d.record_count,
        )
        for d in datasets
    ]

    # Calculate max_id for next incremental sync
    max_id = max((d.id for d in datasets), default=None) if datasets else None  # type: ignore[type-var]

    return DatasetSyncResponse(items=items, max_id=max_id)


@router.get("/{source}/{code}", response_model=DatasetDetailResponse)
async def get_dataset(
    source: str,
    code: str,
    session: AsyncSession = Depends(get_session),
) -> DatasetDetailResponse:
    """Get detailed information about a specific dataset.

    Args:
        source: Data source code
        code: Dataset code

    Returns:
        Dataset details including metadata
    """
    statement = select(Dataset).where(Dataset.source == source, Dataset.code == code)
    dataset = (await session.exec(statement)).one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {source}/{code}")

    # Parse extra metadata
    extra_metadata: dict[str, Any] | None = None
    if dataset.extra_metadata:
        try:
            extra_metadata = json.loads(dataset.extra_metadata)
        except json.JSONDecodeError:
            pass

    # Get unique dimensions (geo, indicator, time_period patterns)
    dimensions = ["geo", "time_period", "indicator"]

    # Get source_url, falling back to generated URL if not stored
    source_url = dataset.source_url or generate_source_url(source, code)

    return DatasetDetailResponse(
        id=dataset.id,  # type: ignore[arg-type]
        code=dataset.code,
        name=dataset.name,
        source=dataset.source,
        description=dataset.description,
        last_fetched=dataset.last_fetched,
        record_count=dataset.record_count,
        extra_metadata=extra_metadata,
        dimensions=dimensions,
        source_url=source_url,
    )


@router.get("/{source}/{code}/values", response_model=DataValueListResponse)
async def get_dataset_values(
    source: str,
    code: str,
    geo: str | None = Query(default=None, description="Filter by geographic area"),
    time_period: str | None = Query(default=None, description="Filter by time period"),
    indicator: str | None = Query(default=None, description="Filter by indicator"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=100, ge=1, le=1000, description="Items per page"),
    session: AsyncSession = Depends(get_session),
) -> DataValueListResponse:
    """Get data values for a specific dataset with filtering.

    Args:
        source: Data source code
        code: Dataset code
        geo: Filter by geographic area
        time_period: Filter by time period
        indicator: Filter by indicator
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Paginated list of data values
    """
    # First get the dataset
    dataset_statement = select(Dataset).where(Dataset.source == source, Dataset.code == code)
    dataset = (await session.exec(dataset_statement)).one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {source}/{code}")

    # Build values query
    statement = select(DataValue).where(DataValue.dataset_id == dataset.id)

    if geo:
        statement = statement.where(DataValue.geo == geo)
    if time_period:
        statement = statement.where(DataValue.time_period == time_period)
    if indicator:
        statement = statement.where(DataValue.indicator == indicator)

    # Get total count
    count_statement = select(func.count()).select_from(statement.subquery())
    total = (await session.exec(count_statement)).one() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    statement = (
        statement.offset(offset)
        .limit(page_size)
        .order_by(DataValue.time_period.desc(), DataValue.geo)  # type: ignore[attr-defined]
    )

    values = (await session.exec(statement)).all()

    items = [
        DataValueResponse(
            geo=v.geo,
            time_period=v.time_period,
            indicator=v.indicator,
            value=v.value,
            unit=v.unit,
            flags=v.flags,
        )
        for v in values
    ]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return DataValueListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        dataset_code=code,
        source=source,
    )


@router.get("/{source}/{code}/dimensions/{dimension}")
async def get_dimension_values(
    source: str,
    code: str,
    dimension: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | list[str]]:
    """Get unique values for a dimension (geo, time_period, indicator).

    Args:
        source: Data source code
        code: Dataset code
        dimension: Dimension name

    Returns:
        List of unique values for the dimension
    """
    # Validate dimension
    valid_dimensions = {"geo", "time_period", "indicator"}
    if dimension not in valid_dimensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dimension: {dimension}. Valid: {valid_dimensions}",
        )

    # Get dataset
    dataset_statement = select(Dataset).where(Dataset.source == source, Dataset.code == code)
    dataset = (await session.exec(dataset_statement)).one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {source}/{code}")

    # Get unique values for the dimension
    column = getattr(DataValue, dimension)
    statement = select(column).where(DataValue.dataset_id == dataset.id).distinct().order_by(column)
    result = await session.execute(statement)
    values = [row[0] for row in result.all()]

    return {"dimension": dimension, "values": values}
