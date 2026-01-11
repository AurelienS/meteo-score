"""Tests for configuration management.

Tests verify:
- Settings loading from environment
- Database URL validation and conversion
- Default values for all settings
- Environment detection helpers
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self):
        """Test that settings have correct default values."""
        from core.config import Settings

        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            assert settings.frontend_url == "http://localhost:5173"
            assert settings.api_base_url == "http://localhost:8000"
            assert settings.environment == "development"
            assert settings.rate_limit_per_minute == 100

    def test_database_url_converts_to_asyncpg(self):
        """Test that postgresql:// is converted to postgresql+asyncpg://."""
        from core.config import Settings

        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}
        ):
            settings = Settings()
            assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_database_url_preserves_asyncpg(self):
        """Test that postgresql+asyncpg:// is preserved."""
        from core.config import Settings

        url = "postgresql+asyncpg://user:pass@host:5432/db"
        with patch.dict(os.environ, {"DATABASE_URL": url}):
            settings = Settings()
            assert settings.database_url == url

    def test_database_url_empty_raises_error(self):
        """Test that empty DATABASE_URL raises validation error."""
        from core.config import Settings

        with patch.dict(os.environ, {"DATABASE_URL": ""}):
            with pytest.raises(ValidationError):
                Settings()

    def test_environment_literal_validation(self):
        """Test that environment must be development or production."""
        from core.config import Settings

        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            with pytest.raises(ValidationError):
                Settings()

    def test_environment_development(self):
        """Test development environment detection."""
        from core.config import Settings

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            settings = Settings()
            assert settings.is_development is True
            assert settings.is_production is False

    def test_environment_production(self):
        """Test production environment detection."""
        from core.config import Settings

        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            settings = Settings()
            assert settings.is_development is False
            assert settings.is_production is True

    def test_rate_limit_from_env(self):
        """Test rate limit can be set via environment."""
        from core.config import Settings

        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "50"}):
            settings = Settings()
            assert settings.rate_limit_per_minute == 50


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings returns a Settings instance."""
        from core.config import Settings, get_settings

        # Clear cache to ensure fresh settings
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_cached(self):
        """Test that get_settings returns the same instance."""
        from core.config import get_settings

        get_settings.cache_clear()
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2


class TestSettingsModule:
    """Tests for module-level settings export."""

    def test_settings_module_export(self):
        """Test that settings is exported at module level."""
        from core.config import settings

        assert settings is not None
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "frontend_url")
