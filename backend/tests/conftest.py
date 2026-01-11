"""Pytest configuration and fixtures for MétéoScore backend tests.

This module provides shared test fixtures including:
- Async test database setup and teardown
- Test database session fixture
- Sample data fixtures for sites, models, parameters

Test Database:
- Uses a separate test database (meteo_score_test or SQLite in-memory)
- Tables are created fresh for each test session
- All data is rolled back after each test function
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Set test database URL before importing models
# Use a separate test database to avoid polluting development data
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///:memory:"),
)

# Ensure async driver for PostgreSQL
if TEST_DATABASE_URL.startswith("postgresql://"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )

# Set environment for imports
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest_asyncio.fixture(scope="function")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create async engine for test database.

    Scope: session (one engine for all tests).
    Creates all tables at start, drops them at end.
    """
    # Import here to ensure DATABASE_URL is set
    from core.models import Base

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )

    # Create all tables
    async with engine.begin() as conn:
        # For PostgreSQL with TimescaleDB, create extension first
        if "postgresql" in TEST_DATABASE_URL:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))
            except Exception:
                # TimescaleDB might not be available in test environment
                pass

        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_db(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session for each test.

    Scope: function (new session for each test).
    Cleans up all data after each test.
    """
    from core.models import Deviation, Model, Parameter, Site

    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        try:
            yield session
        finally:
            # Rollback any pending changes from the test
            await session.rollback()

            # Clean up all data after test (order matters due to FKs)
            try:
                await session.execute(text("DELETE FROM deviations"))
                await session.execute(text("DELETE FROM sites"))
                await session.execute(text("DELETE FROM models"))
                await session.execute(text("DELETE FROM parameters"))
                await session.commit()
            except Exception:
                await session.rollback()


@pytest_asyncio.fixture
async def test_db_committed(
    test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session that commits (for integration tests).

    Scope: function.
    Use this when you need data to persist within a test.
    Cleans up data after the test.
    """
    from core.models import Deviation, Model, Parameter, Site

    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.commit()

        # Clean up all data after test
        await session.execute(text("DELETE FROM deviations"))
        await session.execute(text("DELETE FROM sites"))
        await session.execute(text("DELETE FROM models"))
        await session.execute(text("DELETE FROM parameters"))
        await session.commit()


# Sample data fixtures


@pytest.fixture
def sample_site_data() -> dict:
    """Sample site data for testing."""
    return {
        "name": "Test Site",
        "latitude": Decimal("45.500000"),
        "longitude": Decimal("6.500000"),
        "altitude": 1000,
    }


@pytest.fixture
def sample_model_data() -> dict:
    """Sample model data for testing."""
    return {
        "name": "Test Model",
        "source": "Test source for weather forecasts",
    }


@pytest.fixture
def sample_parameter_data() -> dict:
    """Sample parameter data for testing."""
    return {
        "name": "Test Parameter",
        "unit": "test_unit",
    }


@pytest.fixture
def passy_site_data() -> dict:
    """Passy Plaine Joux site data (production seed data)."""
    return {
        "name": "Passy Plaine Joux",
        "latitude": Decimal("45.916700"),
        "longitude": Decimal("6.700000"),
        "altitude": 1360,
    }


@pytest_asyncio.fixture
async def test_app(test_engine: AsyncEngine):
    """Create FastAPI app with test database dependency override.

    Provides a test app that uses the test database instead of production.
    """
    from core.database import get_db
    from main import app

    async_session = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db

    yield app

    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client for API testing.

    Uses test database via dependency override.
    Clears rate limiter state before each test.
    """
    # Clear rate limiter state before each test
    from main import request_counts
    request_counts.clear()

    # Clear settings cache to ensure consistent rate limit
    from core.config import get_settings
    get_settings.cache_clear()

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
        follow_redirects=True,
    ) as client:
        yield client

    # Clean up rate limiter state after test
    request_counts.clear()
