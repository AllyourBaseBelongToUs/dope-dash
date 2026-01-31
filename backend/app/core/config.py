"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Dope Dash API"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://dopedash:dopedash@localhost:5432/dopedash",
        description="PostgreSQL database URL with asyncpg driver",
    )
    database_echo: bool = Field(default=False, description="Log SQL queries")
    db_pool_size: int = Field(default=15, description="Database connection pool size (reduced for 4-service architecture)")
    db_max_overflow: int = Field(default=5, description="Max overflow connections (reduced for 4-service architecture)")
    db_pool_timeout: int = Field(default=30, description="Pool timeout in seconds")
    db_pool_recycle: int = Field(
        default=3600, description="Recycle connections after N seconds"
    )

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )

    # Agent Configuration
    agent_max_concurrent: int = Field(
        default=5, description="Maximum concurrent agent executions"
    )
    agent_timeout_seconds: int = Field(
        default=300, description="Default agent timeout in seconds"
    )
    agent_retries: int = Field(default=3, description="Default number of agent retries")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(
        default=60, description="Requests per minute per user"
    )
    rate_limit_burst: int = Field(
        default=10, description="Burst size for token bucket"
    )

    # Data Retention
    events_retention_days: int = Field(
        default=30, description="Retention period for events in days"
    )
    sessions_retention_days: int = Field(
        default=365, description="Retention period for sessions in days"
    )
    retention_cleanup_schedule: str = Field(
        default="daily", description="Schedule for retention cleanup (daily, weekly, monthly)"
    )
    retention_cleanup_hour: int = Field(
        default=2, description="Hour of day to run cleanup (0-23)"
    )
    retention_soft_delete_enabled: bool = Field(
        default=True, description="Enable soft delete before permanent deletion"
    )
    retention_warning_days: int = Field(
        default=7, description="Days before deletion to send warning"
    )

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses asyncpg driver."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                'Database URL must use "postgresql+asyncpg://" driver for async support'
            )
        return v

    @property
    def sync_database_url(self) -> str:
        """Convert async URL to sync for Alembic migrations."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
