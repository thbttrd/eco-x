"""SourceMetadata model for tracking data source information.

This model stores metadata about data sources, including cached
table of contents (TOC) for efficient dataset discovery.
"""

from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class SourceMetadata(SQLModel, table=True):
    """Metadata and cache for a data source (e.g., Eurostat TOC).

    Used to store:
    - Total number of available datasets
    - Cached table of contents for efficient browsing
    - Last update timestamp for cache invalidation
    """

    __tablename__ = "sourcemetadata"

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(index=True, unique=True, description="Source code (e.g., 'eurostat')")
    total_datasets: int = Field(default=0, description="Total number of available datasets")
    cached_toc: str | None = Field(
        default=None, description="JSON string of cached Table of Contents"
    )
    last_updated: datetime = Field(default_factory=datetime.now)


class SkippedDataset(SQLModel, table=True):
    """Datasets that were skipped during fetching.

    Used to track large datasets that need special handling,
    or datasets skipped for other reasons.
    """

    __tablename__ = "skippeddataset"
    __table_args__ = (
        UniqueConstraint("source", "dataset_code", name="uq_skippeddataset_source_code"),
    )

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(index=True, description="Source code (e.g., 'eurostat')")
    dataset_code: str = Field(index=True, description="Dataset identifier")
    reason: str = Field(description="Reason for skipping (e.g., 'too_large')")
    values_count: int = Field(default=0, description="Number of values in the dataset")
    threshold: int = Field(default=0, description="Threshold that was exceeded")
    skipped_at: datetime = Field(default_factory=datetime.now)
