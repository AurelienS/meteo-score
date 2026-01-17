"""Admin authentication dependencies.

This module provides HTTP Basic Auth for admin-only endpoints.
Credentials are read from environment variables.

Includes rate limiting for failed auth attempts to prevent brute-force attacks.

Usage:
    from api.dependencies.auth import verify_admin

    router = APIRouter(dependencies=[Depends(verify_admin)])
"""

import logging
import os
import secrets
import time
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

logger = logging.getLogger(__name__)

security = HTTPBasic()

# Rate limiting for failed auth attempts (stricter than general API rate limit)
_failed_attempts: dict[str, list[float]] = defaultdict(list)
_ADMIN_RATE_LIMIT = 5  # Max failed attempts per window
_ADMIN_RATE_WINDOW = 60  # Window in seconds


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(client_ip: str) -> None:
    """Check if client has exceeded failed auth rate limit.

    Args:
        client_ip: The client's IP address.

    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded.
    """
    now = time.time()

    # Clean old attempts outside the window
    _failed_attempts[client_ip] = [
        t for t in _failed_attempts[client_ip] if now - t < _ADMIN_RATE_WINDOW
    ]

    if len(_failed_attempts[client_ip]) >= _ADMIN_RATE_LIMIT:
        logger.warning(f"Admin auth rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed authentication attempts. Please try again later.",
            headers={"Retry-After": str(_ADMIN_RATE_WINDOW)},
        )


def _record_failed_attempt(client_ip: str) -> None:
    """Record a failed authentication attempt."""
    _failed_attempts[client_ip].append(time.time())


def get_admin_credentials() -> tuple[str, str]:
    """Get admin credentials from environment variables.

    Returns:
        Tuple of (username, password) from environment.
        Defaults to ("admin", "changeme") for development.
    """
    return (
        os.getenv("ADMIN_USERNAME", "admin"),
        os.getenv("ADMIN_PASSWORD", "changeme"),
    )


def verify_admin(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    """Verify admin credentials using HTTP Basic Auth.

    Includes rate limiting for failed attempts to prevent brute-force attacks.

    Args:
        request: The FastAPI request object (for IP extraction).
        credentials: HTTP Basic credentials from request header.

    Returns:
        The authenticated username.

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid.
        HTTPException: 429 Too Many Requests if rate limit exceeded.
    """
    client_ip = _get_client_ip(request)

    # Check rate limit before attempting auth
    _check_rate_limit(client_ip)

    username, password = get_admin_credentials()

    # Use constant-time comparison to prevent timing attacks
    is_username_correct = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        username.encode("utf-8"),
    )
    is_password_correct = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        password.encode("utf-8"),
    )

    if not (is_username_correct and is_password_correct):
        _record_failed_attempt(client_ip)
        logger.warning(f"Failed admin auth attempt from IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
