"""Dataset and DataValue models shared between platform and client.

These models represent the core data structures for economic datasets.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, Index, Integer
from sqlmodel import Field, Relationship, SQLModel


class DatasetBase(SQLModel):
    """Base model for datasets (without table definition).

    A dataset represents a collection of data from a specific source
    (e.g., Eurostat GDP data, OECD inflation data).
    """

    code: str = Field(index=True, description="Dataset code (e.g., 'nama_10_gdp')")
    name: str = Field(description="Human-readable dataset name")
    source: str = Field(index=True, description="Data source (e.g., 'eurostat', 'oecd', 'fred')")
    description: str | None = Field(default=None, description="Dataset description")
    last_fetched: datetime | None = Field(
        default=None, description="Timestamp of last successful fetch"
    )
    record_count: int = Field(default=0, description="Number of data values in this dataset")
    content_hash: str | None = Field(
        default=None, description="SHA256 hash of dataset content for change detection"
    )
    source_last_update: str | None = Field(
        default=None,
        description="Last update timestamp from source metadata (e.g., Eurostat TOC '14.12.2024')",
    )
    extra_metadata: str | None = Field(
        default=None, description="Additional metadata as JSON string"
    )
    source_url: str | None = Field(
        default=None,
        description="URL to the original dataset page on the source website",
    )


class Dataset(DatasetBase, table=True):
    """Dataset table model.

    Inherits all fields from DatasetBase and adds primary key.
    This is the actual table that will be created in the database.
    """

    __tablename__ = "dataset"
    __table_args__ = (
        Index("idx_dataset_source_code", "source", "code"),
        Index("idx_dataset_last_fetched", "last_fetched"),
        Index("idx_dataset_source_last_update", "source_last_update"),
    )

    id: int | None = Field(default=None, primary_key=True)

    # Relationship to data values
    values: list["DataValue"] = Relationship(back_populates="dataset")


class DataValueBase(SQLModel):
    """Base model for data values (without table definition).

    Represents individual data points from a dataset.
    """

    geo: str = Field(index=True, description="Geographic area (e.g., 'EU27_2020', 'FR', 'DE')")
    time_period: str = Field(
        index=True, description="Time period (e.g., '2022', '2022-Q1', '2022-M01')"
    )
    indicator: str = Field(index=True, description="What is measured (e.g., 'GDP', 'HICP', 'B1GQ')")
    value: float = Field(description="The actual numeric value")
    unit: str | None = Field(
        default=None, description="Unit of measurement (e.g., 'EUR', 'MIO_EUR', 'PC')"
    )
    flags: str | None = Field(
        default=None, description="Data flags (e.g., 'e' for estimated, 'p' for provisional)"
    )


class DataValue(DataValueBase, table=True):
    """Data value table model.

    Inherits all fields from DataValueBase and adds primary key and foreign key.
    """

    __tablename__ = "datavalue"
    __table_args__ = (
        # Unique constraint for UPSERT operations (ON CONFLICT)
        Index(
            "uq_datavalue_dataset_geo_time_indicator",
            "dataset_id",
            "geo",
            "time_period",
            "indicator",
            unique=True,
        ),
    )

    # Use BigInteger for id to support >2.1B values (sequence was exhausted)
    # Uses Integer for SQLite (tests) and BigInteger for PostgreSQL (production)
    id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer().with_variant(BigInteger(), "postgresql"),
            primary_key=True,
        ),
    )
    dataset_id: int = Field(foreign_key="dataset.id", index=True)

    # Relationship to dataset
    dataset: Dataset | None = Relationship(back_populates="values")


class DatasetMetadata(SQLModel, table=True):
    """Metadata about datasets (dimensions, attributes, etc.).

    This table can store additional information about dataset structure,
    available dimensions, and other metadata.
    """

    __tablename__ = "datasetmetadata"

    id: int | None = Field(default=None, primary_key=True)
    dataset_id: int = Field(foreign_key="dataset.id", index=True)
    key: str = Field(description="Metadata key (e.g., 'dimension', 'attribute')")
    value: str = Field(description="Metadata value (JSON string)")
    created_at: datetime = Field(default_factory=datetime.now)
