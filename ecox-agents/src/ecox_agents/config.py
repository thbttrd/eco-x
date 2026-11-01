"""Configuration settings for ecox-agents service."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Agent service configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ECOX_AGENTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Server
    api_host: str = Field(default="0.0.0.0", description="API host")  # nosec B104
    api_port: int = Field(default=8001, description="API port")

    # LLM Configuration
    llm_provider: Literal["anthropic", "openai", "ollama"] = Field(
        default="anthropic", description="LLM provider"
    )
    llm_model: str = Field(default="claude-sonnet-4-5", description="Model name")
    anthropic_api_key: str | None = Field(default=None, description="Anthropic API key")

    # Platform Communication
    platform_url: str = Field(default="http://localhost:8000", description="Platform API URL")
    platform_timeout: float = Field(default=30.0, description="Platform API timeout")

    # Redis for Conversation Memory
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    conversation_ttl: int = Field(default=1800, description="Conversation TTL in seconds (30 min)")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")


# Global settings instance
settings = Settings()
