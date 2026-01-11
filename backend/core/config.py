"""Configuration management for MétéoScore backend.

This module provides environment-based configuration using Pydantic Settings.
All settings are validated on startup and accessible via the settings singleton.

Environment Variables:
    DATABASE_URL: Database connection string (must use asyncpg driver)
    FRONTEND_URL: Frontend application URL for CORS
    API_BASE_URL: API base URL
    ENVIRONMENT: Runtime environment (development/production)
    RATE_LIMIT_PER_MINUTE: API rate limit per IP
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings have sensible defaults for development.
    Production deployments should override via environment variables.

    Attributes:
        database_url: PostgreSQL connection string with asyncpg driver.
        frontend_url: Frontend origin for CORS configuration.
        api_base_url: API server base URL.
        environment: Runtime environment (development or production).
        rate_limit_per_minute: Maximum requests per minute per IP.
    """

    # Database configuration
    database_url: str = "postgresql+asyncpg://meteo_user:meteo_password@localhost:5432/meteo_score"

    # URL configuration
    frontend_url: str = "http://localhost:5173"
    api_base_url: str = "http://localhost:8000"

    # Environment
    environment: Literal["development", "production"] = "development"

    # Rate limiting
    rate_limit_per_minute: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses async driver.

        Args:
            v: The database URL to validate.

        Returns:
            The validated database URL with asyncpg driver.

        Raises:
            ValueError: If URL is empty or uses wrong driver.
        """
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")

        # Convert postgresql:// to postgresql+asyncpg://
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Validate it's using the correct async driver
        if v.startswith("postgresql") and "+asyncpg" not in v:
            raise ValueError(
                "DATABASE_URL must use asyncpg driver. "
                "Use postgresql+asyncpg://... instead of postgresql://..."
            )

        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings singleton.

    Uses LRU cache to ensure settings are only loaded once.

    Returns:
        The application settings instance.
    """
    return Settings()


# Convenience export for direct access
settings = get_settings()
