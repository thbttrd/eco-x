"""Cache models for storing API responses locally.

These models allow the client to cache platform API responses
to improve performance and enable offline viewing.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class ApiCacheEntry(SQLModel, table=True):
    """Cache entry for API responses.

    Stores API responses with TTL-based expiration.
    """

    __tablename__ = "api_cache"

    id: int | None = Field(default=None, primary_key=True)
    cache_key: str = Field(index=True, unique=True, description="Unique cache key")
    endpoint: str = Field(index=True, description="API endpoint path")
    response_data: str = Field(description="JSON response data")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(index=True, description="When this entry expires")

    @property
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return datetime.now() > self.expires_at
