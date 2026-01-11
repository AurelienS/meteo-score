"""Health check endpoint for MétéoScore API.

Provides application health status including database connectivity.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Check application health status.

    Verifies database connectivity and returns overall health status.

    Args:
        db: Database session (injected).

    Returns:
        HealthResponse with status and database connectivity info.
    """
    try:
        # Test database connectivity
        await db.execute(text("SELECT 1"))
        db_status = "connected"
        status = "healthy"
    except Exception:
        db_status = "disconnected"
        status = "degraded"

    return HealthResponse(status=status, database=db_status)


@router.get("/", response_model=HealthResponse)
async def root_health() -> HealthResponse:
    """Root endpoint health check.

    Simple health check without database verification.
    Used by Docker healthcheck and load balancers.

    Returns:
        HealthResponse with healthy status.
    """
    return HealthResponse(status="healthy")
