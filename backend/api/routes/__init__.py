"""API routes aggregation for MétéoScore.

This module aggregates all API routers under a common prefix.
"""

from fastapi import APIRouter

from api.routes.health import router as health_router
from api.routes.metrics import router as metrics_router
from api.routes.models import router as models_router
from api.routes.parameters import router as parameters_router
from api.routes.scheduler import router as scheduler_router
from api.routes.sites import router as sites_router

# Main API router with /api prefix
api_router = APIRouter(prefix="/api")

# Include all route modules
api_router.include_router(sites_router)
api_router.include_router(models_router)
api_router.include_router(parameters_router)
api_router.include_router(scheduler_router)
api_router.include_router(metrics_router)

__all__ = ["api_router", "health_router"]
