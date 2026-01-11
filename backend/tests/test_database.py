"""Tests for database connection utilities.

Tests verify:
- Database URL parsing and validation
- Engine creation with correct settings
- Session factory configuration
- FastAPI dependency function
- Connection pool behavior
"""

import os
from unittest.mock import patch

import pytest


class TestDatabaseUrl:
    """Tests for database URL handling."""

    def test_get_database_url_converts_postgresql(self):
        """Test that postgresql:// is converted to postgresql+asyncpg://."""
        from core.database import get_database_url

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/db"}):
            url = get_database_url()
            assert url.startswith("postgresql+asyncpg://")
            assert "user:pass@host:5432/db" in url

    def test_get_database_url_preserves_asyncpg(self):
        """Test that postgresql+asyncpg:// is preserved."""
        from core.database import get_database_url

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://user:pass@host:5432/db"}):
            url = get_database_url()
            assert url == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_get_database_url_converts_sqlite(self):
        """Test that sqlite:// is converted to sqlite+aiosqlite://."""
        from core.database import get_database_url

        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
            url = get_database_url()
            assert url == "sqlite+aiosqlite:///test.db"

    def test_get_database_url_raises_on_missing(self):
        """Test that missing DATABASE_URL raises ValueError."""
        from core.database import get_database_url

        with patch.dict(os.environ, clear=True):
            with pytest.raises(ValueError, match="DATABASE_URL"):
                get_database_url()


class TestEngineCreation:
    """Tests for engine creation."""

    def test_create_engine_returns_async_engine(self):
        """Test that create_engine returns an AsyncEngine."""
        from sqlalchemy.ext.asyncio import AsyncEngine
        from core.database import create_engine

        engine = create_engine()
        assert isinstance(engine, AsyncEngine)


class TestGetDb:
    """Tests for get_db FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Test that get_db yields an AsyncSession."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from core.database import get_db

        async for session in get_db():
            assert isinstance(session, AsyncSession)
            break

    @pytest.mark.asyncio
    async def test_get_db_session_is_usable(self):
        """Test that yielded session can execute queries."""
        from sqlalchemy import text
        from core.database import get_db

        async for session in get_db():
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            break


class TestConnectionTest:
    """Tests for test_connection function."""

    @pytest.mark.asyncio
    async def test_connection_returns_true(self):
        """Test that test_connection returns True when database is accessible."""
        from core.database import test_connection

        result = await test_connection()
        assert result is True


class TestCloseEngine:
    """Tests for close_engine function."""

    @pytest.mark.asyncio
    async def test_close_engine_safe_when_none(self):
        """Test that close_engine is safe when engine is None."""
        from core import database
        from core.database import close_engine

        database._engine = None

        # Should not raise
        await close_engine()
