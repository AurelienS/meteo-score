"""MétéoScore API - Weather forecast accuracy comparison platform.

This module provides the FastAPI application with:
- CORS middleware for frontend communication
- Rate limiting middleware (100 req/min per IP)
- API routes for sites, models, and parameters
- Health check endpoints
- Application lifecycle management
"""

from collections import defaultdict
from contextlib import asynccontextmanager
from time import time
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import api_router, health_router
from core.config import get_settings, settings
from core.database import close_engine
from scheduler.scheduler import start_scheduler, stop_scheduler

# Rate limiting state (simple in-memory implementation)
request_counts: dict[str, list[float]] = defaultdict(list)
_last_cleanup: float = 0.0
_CLEANUP_INTERVAL: int = 300  # Cleanup every 5 minutes


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Start scheduler for automated data collection
    - Shutdown: Stop scheduler and close database engine

    Args:
        app: FastAPI application instance.

    Yields:
        None during application runtime.
    """
    # Startup
    await start_scheduler()
    yield
    # Shutdown
    await stop_scheduler()
    await close_engine()


app = FastAPI(
    title="MétéoScore API",
    description="Weather forecast accuracy comparison platform for paragliding pilots",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple sliding window rate limiter.

    Limits requests to RATE_LIMIT_PER_MINUTE per IP address.
    Includes periodic cleanup of stale entries to prevent memory leaks.

    Args:
        request: Incoming request.
        call_next: Next middleware/handler.

    Returns:
        Response from next handler or 429 if rate limited.
    """
    global _last_cleanup

    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/"]:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time()
    window = 60  # 1 minute

    # Periodic cleanup of all stale entries (every 5 minutes)
    if now - _last_cleanup > _CLEANUP_INTERVAL:
        stale_ips = [
            ip for ip, times in request_counts.items()
            if not times or (now - max(times)) > window
        ]
        for ip in stale_ips:
            del request_counts[ip]
        _last_cleanup = now

    # Clean old requests outside the window for current IP
    request_counts[client_ip] = [
        t for t in request_counts[client_ip] if now - t < window
    ]

    # Check rate limit (use get_settings() for testability)
    if len(request_counts[client_ip]) >= get_settings().rate_limit_per_minute:
        return JSONResponse(
            status_code=429,
            content={
                "error": "RateLimitError",
                "detail": "Rate limit exceeded. Please try again later.",
                "statusCode": 429,
            },
        )

    # Record this request
    request_counts[client_ip].append(now)
    return await call_next(request)


# Include routers
app.include_router(health_router)  # /health and / endpoints
app.include_router(api_router)  # /api/* endpoints


if __name__ == "__main__":
    # Run with uvicorn for Docker container
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
