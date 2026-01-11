"""Async database connection utilities for MétéoScore.

This module provides the async SQLAlchemy engine, session factory, and
FastAPI dependency for database access.

All database operations MUST use async patterns:
- Use AsyncSession (not synchronous Session)
- Use select() with await session.execute() (not session.query())
- Use await for all database operations

Connection pool configuration:
- pool_size: 5 (minimum connections)
- max_overflow: 15 (additional connections when needed)
- Total maximum: 20 connections
"""

import os
from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Note: DATABASE_URL is read dynamically in get_database_url() to support testing


def get_database_url() -> str:
    """Get the database URL, ensuring async driver is used.

    Returns:
        Database URL with postgresql+asyncpg:// or sqlite+aiosqlite:// driver.

    Raises:
        ValueError: If DATABASE_URL is not configured.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Set it to postgresql+asyncpg://user:password@host:port/database"
        )

    # Ensure we're using the async driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    # Allow postgresql+asyncpg://, sqlite+aiosqlite://, etc.

    return url


def create_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine with connection pooling.

    Returns:
        Configured AsyncEngine. PostgreSQL uses pool_size=5, max_overflow=15.
        SQLite uses NullPool (no connection pooling).
    """
    url = get_database_url()

    # SQLite doesn't support connection pooling the same way
    if url.startswith("sqlite"):
        return create_async_engine(
            url,
            echo=False,
        )

    # PostgreSQL and other databases with proper pooling
    return create_async_engine(
        url,
        pool_pre_ping=True,  # Verify connections before use
        pool_size=5,  # Minimum connections
        max_overflow=15,  # Additional connections (total max = 20)
        echo=False,  # Set to True for SQL query logging
    )


# Global engine instance - created lazily
_engine: Optional[AsyncEngine] = None


def get_engine() -> AsyncEngine:
    """Get or create the global async engine.

    Returns:
        The global AsyncEngine instance.
    """
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get async session factory bound to the global engine.

    Returns:
        Configured async_sessionmaker for creating database sessions.
    """
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session.

    Provides an async database session for route handlers.
    Automatically commits on success or rolls back on exception.

    Yields:
        AsyncSession: Database session for the request.

    Example:
        @router.get("/sites")
        async def get_sites(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Site))
            return result.scalars().all()
    """
    async_session = get_async_session_factory()

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def test_connection() -> bool:
    """Test database connectivity.

    Attempts to connect to the database and execute a simple query.

    Returns:
        True if connection is successful.

    Raises:
        Exception: If connection fails.
    """
    from sqlalchemy import text

    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        return result.scalar() == 1


async def close_engine() -> None:
    """Close the global engine and release all connections.

    Should be called during application shutdown.
    """
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
