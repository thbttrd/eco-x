"""FetchLog model for tracking data fetch operations.

This model is used by the platform for audit logging and by the
client to display fetch history.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class FetchLog(SQLModel, table=True):
    """Log of data fetch operations.

    Tracks when data was fetched, from which source, and any errors.
    Used for auditing, debugging, and displaying fetch history to users.
    """

    __tablename__ = "fetchlog"

    id: int | None = Field(default=None, primary_key=True)
    dataset_code: str = Field(index=True, description="Dataset code that was fetched")
    source: str = Field(index=True, description="Data source (e.g., 'eurostat')")
    status: str = Field(description="Status: 'success', 'error', 'partial'")
    records_fetched: int | None = Field(default=None, description="Number of records fetched")
    error_message: str | None = Field(default=None, description="Error message if failed")
    filters: str | None = Field(default=None, description="Filters used (JSON string)")
    started_at: datetime = Field(default_factory=datetime.now, index=True)
    completed_at: datetime | None = Field(default=None)
    duration_seconds: float | None = Field(default=None, description="Fetch duration in seconds")
