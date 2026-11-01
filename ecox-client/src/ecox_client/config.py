"""Client configuration using Pydantic Settings.

Configuration is loaded from environment variables with sensible defaults.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Client configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="ECOX_CLIENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Platform API
    platform_url: str = Field(
        default="http://localhost:8000",
        description="URL of the ecox-data-platform API",
    )
    platform_timeout: float = Field(
        default=30.0,
        description="Timeout for platform API requests in seconds",
    )

    # Database (SQLite for caching)
    database_url: str = Field(
        default="sqlite+aiosqlite:///./ecox_client.db",
        description="SQLite database URL for caching and preferences",
    )

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")  # nosec B104
    api_port: int = Field(default=8080, description="API port")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    # Cache settings
    cache_ttl_seconds: int = Field(
        default=300,
        description="TTL for API response cache in seconds (5 minutes)",
    )


# Global settings instance
settings = Settings()
