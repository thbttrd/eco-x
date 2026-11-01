"""Platform configuration using Pydantic Settings.

Configuration is loaded from environment variables with sensible defaults.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SourceConfig(BaseSettings):
    """Configuration for a single data source."""

    rate_limit: float = Field(default=2.0, description="Requests per second")
    max_concurrent: int = Field(default=3, description="Max concurrent fetches")
    refresh_hours: int = Field(default=24, description="Hours between refreshes")
    enabled: bool = Field(default=True, description="Whether this source is enabled")
    max_values: int = Field(
        default=10_000_000, description="Skip datasets with more values (0 = no limit)"
    )


class Settings(BaseSettings):
    """Platform configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="ECOX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://ecox:ecox@localhost:5432/ecox_platform",
        description="PostgreSQL connection URL",
    )

    # API
    api_host: str = Field(default="0.0.0.0", description="API host")  # nosec B104
    api_port: int = Field(default=8000, description="API port")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    # Per-source rate limits (can be overridden via env vars)
    eurostat_rate_limit: float = Field(default=2.0)
    eurostat_max_concurrent: int = Field(default=3)
    eurostat_refresh_hours: int = Field(default=24)
    eurostat_max_values: int = Field(default=10_000_000)

    fred_rate_limit: float = Field(default=2.0)
    fred_max_concurrent: int = Field(default=5)
    fred_refresh_hours: int = Field(default=12)
    fred_api_key: str | None = Field(default=None, description="FRED API key")

    oecd_rate_limit: float = Field(default=0.33)  # 1 request per 3 seconds to avoid 429
    oecd_max_concurrent: int = Field(default=2)
    oecd_refresh_hours: int = Field(default=24)

    nbs_rate_limit: float = Field(default=2.0)
    nbs_max_concurrent: int = Field(default=3)
    nbs_refresh_hours: int = Field(default=24)

    ons_rate_limit: float = Field(default=2.0)
    ons_max_concurrent: int = Field(default=3)
    ons_refresh_hours: int = Field(default=24)

    # News fetching settings (can be overridden via env vars)
    news_fetch_interval_minutes: int = Field(
        default=60, description="Default news fetch interval in minutes"
    )
    news_max_concurrent: int = Field(default=3, description="Max concurrent news fetches")
    news_rate_limit: float = Field(
        default=2.0, description="News fetch rate limit (requests per second per domain)"
    )
    news_fetch_on_startup: bool = Field(
        default=True, description="Whether to fetch news on startup"
    )
    news_startup_delay: int = Field(
        default=30, description="Delay before first news fetch on startup (seconds)"
    )
    news_retention_months: int = Field(
        default=12, description="How long to keep news articles (months)"
    )

    def get_source_config(self, source: str) -> SourceConfig:
        """Get configuration for a specific source."""
        configs = {
            "eurostat": SourceConfig(
                rate_limit=self.eurostat_rate_limit,
                max_concurrent=self.eurostat_max_concurrent,
                refresh_hours=self.eurostat_refresh_hours,
                max_values=self.eurostat_max_values,
            ),
            "fred": SourceConfig(
                rate_limit=self.fred_rate_limit,
                max_concurrent=self.fred_max_concurrent,
                refresh_hours=self.fred_refresh_hours,
            ),
            "oecd": SourceConfig(
                rate_limit=self.oecd_rate_limit,
                max_concurrent=self.oecd_max_concurrent,
                refresh_hours=self.oecd_refresh_hours,
            ),
            "nbs": SourceConfig(
                rate_limit=self.nbs_rate_limit,
                max_concurrent=self.nbs_max_concurrent,
                refresh_hours=self.nbs_refresh_hours,
            ),
            "ons": SourceConfig(
                rate_limit=self.ons_rate_limit,
                max_concurrent=self.ons_max_concurrent,
                refresh_hours=self.ons_refresh_hours,
            ),
        }
        return configs.get(source, SourceConfig())


# Global settings instance
settings = Settings()
