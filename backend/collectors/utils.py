"""Utility functions and classes for weather data collectors.

This module provides common utilities used across all collector implementations:
- Exponential backoff retry decorator for resilient API calls
- Circuit breaker pattern for failing external APIs
- HTTP client wrapper with timeout and error handling
- Date/time parsing utilities for various formats

These utilities ensure consistent error handling and retry behavior
across all weather data sources (AROME, Meteo-Parapente, ROMMA, FFVL).
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

import httpx

# Constants
DEFAULT_TIMEOUT = 30.0  # seconds
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 60.0  # seconds

# Circuit breaker defaults
CIRCUIT_FAILURE_THRESHOLD = 5  # failures before opening
CIRCUIT_COOLDOWN_SECONDS = 300  # 5 minutes

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CollectorError(Exception):
    """Base exception for collector errors."""

    pass


class HttpClientError(CollectorError):
    """Exception raised for HTTP client errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize HttpClientError.

        Args:
            message: Error description.
            status_code: HTTP status code if available.
        """
        super().__init__(message)
        self.status_code = status_code


class RetryExhaustedError(CollectorError):
    """Exception raised when all retry attempts are exhausted."""

    def __init__(self, message: str, last_exception: Exception | None = None) -> None:
        """Initialize RetryExhaustedError.

        Args:
            message: Error description.
            last_exception: The last exception that caused the retry failure.
        """
        super().__init__(message)
        self.last_exception = last_exception


class CircuitBreakerOpenError(CollectorError):
    """Exception raised when circuit breaker is open."""

    def __init__(self, name: str, cooldown_remaining: float) -> None:
        """Initialize CircuitBreakerOpenError.

        Args:
            name: Name of the circuit breaker.
            cooldown_remaining: Seconds until circuit breaker allows retry.
        """
        super().__init__(
            f"Circuit breaker '{name}' is open. "
            f"Retry in {cooldown_remaining:.1f} seconds."
        )
        self.name = name
        self.cooldown_remaining = cooldown_remaining


class CircuitBreakerState(Enum):
    """States of a circuit breaker."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern for external API resilience.

    Prevents hammering failing APIs by tracking failures and temporarily
    blocking requests when failure threshold is exceeded.

    State transitions:
    - CLOSED -> OPEN: After failure_threshold consecutive failures
    - OPEN -> HALF_OPEN: After cooldown_seconds elapsed
    - HALF_OPEN -> CLOSED: On successful request
    - HALF_OPEN -> OPEN: On failed request

    Example:
        >>> breaker = CircuitBreaker("meteo_api")
        >>> async def fetch():
        ...     breaker.check()  # Raises if open
        ...     try:
        ...         result = await api_call()
        ...         breaker.record_success()
        ...         return result
        ...     except Exception as e:
        ...         breaker.record_failure()
        ...         raise
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = CIRCUIT_FAILURE_THRESHOLD,
        cooldown_seconds: float = CIRCUIT_COOLDOWN_SECONDS,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker (for logging).
            failure_threshold: Failures before opening circuit.
            cooldown_seconds: Seconds to wait before testing again.
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._success_count = 0

    @property
    def state(self) -> CircuitBreakerState:
        """Get current state, transitioning from OPEN to HALF_OPEN if cooldown elapsed."""
        if self._state == CircuitBreakerState.OPEN:
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.cooldown_seconds:
                    self._state = CircuitBreakerState.HALF_OPEN
                    logger.info(
                        f"Circuit breaker '{self.name}' entering HALF_OPEN state "
                        f"after {elapsed:.1f}s cooldown"
                    )
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (requests allowed)."""
        return self.state == CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (requests blocked)."""
        return self.state == CircuitBreakerState.OPEN

    def check(self) -> None:
        """Check if request is allowed.

        Raises:
            CircuitBreakerOpenError: If circuit is open.
        """
        if self.state == CircuitBreakerState.OPEN:
            elapsed = time.monotonic() - (self._last_failure_time or 0)
            remaining = self.cooldown_seconds - elapsed
            raise CircuitBreakerOpenError(self.name, max(0, remaining))

    def record_success(self) -> None:
        """Record a successful request."""
        if self._state == CircuitBreakerState.HALF_OPEN:
            logger.info(
                f"Circuit breaker '{self.name}' closing after successful request"
            )
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count += 1

    def record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Single failure in half-open reopens the circuit
            self._state = CircuitBreakerState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' reopened after failure in HALF_OPEN state"
            )
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitBreakerState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' opened after "
                f"{self._failure_count} consecutive failures"
            )

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._success_count = 0
        logger.info(f"Circuit breaker '{self.name}' reset to CLOSED state")

    def get_status(self) -> dict[str, Any]:
        """Get circuit breaker status for monitoring.

        Returns:
            Dict with state, failure_count, and timing info.
        """
        status = {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "success_count": self._success_count,
        }

        if self._last_failure_time is not None and self._state == CircuitBreakerState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            status["cooldown_remaining"] = max(0, self.cooldown_seconds - elapsed)

        return status


def retry_with_backoff(
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    max_delay: float = MAX_DELAY,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for exponential backoff retry logic.

    Retries an async function with exponential backoff when specified
    exceptions occur. The delay doubles after each failure up to max_delay.

    Args:
        max_retries: Maximum number of retry attempts (default: 3).
        base_delay: Initial delay in seconds before first retry (default: 1.0).
        max_delay: Maximum delay in seconds between retries (default: 60.0).
        exceptions: Tuple of exception types to catch and retry on.

    Returns:
        Decorated async function with retry logic.

    Example:
        >>> @retry_with_backoff(max_retries=3, base_delay=1.0)
        ... async def fetch_data():
        ...     response = await client.get(url)
        ...     return response.json()
    """

    def decorator(
        func: Callable[..., Awaitable[T]],
    ) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            delay = base_delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for "
                            f"{func.__name__}: {e}. Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, max_delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for "
                            f"{func.__name__}: {e}"
                        )

            raise RetryExhaustedError(
                f"All {max_retries + 1} attempts failed for {func.__name__}",
                last_exception=last_exception,
            )

        return wrapper

    return decorator


class HttpClient:
    """Async HTTP client wrapper with timeout and error handling.

    Provides a consistent interface for making HTTP requests with
    automatic timeout handling, error conversion, and logging.

    Attributes:
        timeout: Request timeout in seconds.
        headers: Default headers to include in all requests.

    Example:
        >>> async with HttpClient(timeout=30.0) as client:
        ...     data = await client.get("https://api.example.com/data")
        ...     print(data)
    """

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize HttpClient.

        Args:
            timeout: Request timeout in seconds (default: 30.0).
            headers: Default headers to include in all requests.
        """
        self.timeout = timeout
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HttpClient":
        """Enter async context manager."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=self.headers,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """Make GET request and return JSON response.

        Args:
            url: Request URL.
            **kwargs: Additional arguments passed to httpx.get().

        Returns:
            Parsed JSON response as dictionary.

        Raises:
            HttpClientError: If request fails or response is not valid JSON.
        """
        if not self._client:
            raise HttpClientError("Client not initialized. Use 'async with' context.")

        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HttpClientError(
                f"HTTP {e.response.status_code} error for {url}: {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise HttpClientError(f"Request failed for {url}: {e}") from e
        except ValueError as e:
            raise HttpClientError(f"Invalid JSON response from {url}: {e}") from e

    async def get_text(self, url: str, **kwargs: Any) -> str:
        """Make GET request and return text response.

        Args:
            url: Request URL.
            **kwargs: Additional arguments passed to httpx.get().

        Returns:
            Response body as text.

        Raises:
            HttpClientError: If request fails.
        """
        if not self._client:
            raise HttpClientError("Client not initialized. Use 'async with' context.")

        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            raise HttpClientError(
                f"HTTP {e.response.status_code} error for {url}: {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise HttpClientError(f"Request failed for {url}: {e}") from e

    async def get_bytes(self, url: str, **kwargs: Any) -> bytes:
        """Make GET request and return binary response.

        Useful for downloading GRIB2 files or other binary data.

        Args:
            url: Request URL.
            **kwargs: Additional arguments passed to httpx.get().

        Returns:
            Response body as bytes.

        Raises:
            HttpClientError: If request fails.
        """
        if not self._client:
            raise HttpClientError("Client not initialized. Use 'async with' context.")

        try:
            response = await self._client.get(url, **kwargs)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as e:
            raise HttpClientError(
                f"HTTP {e.response.status_code} error for {url}: {e.response.text}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise HttpClientError(f"Request failed for {url}: {e}") from e


def parse_iso_datetime(value: str) -> datetime:
    """Parse ISO 8601 datetime string to timezone-aware datetime.

    Handles various ISO 8601 formats including:
    - 2026-01-11T12:00:00Z
    - 2026-01-11T12:00:00+00:00
    - 2026-01-11T12:00:00

    Args:
        value: ISO 8601 datetime string.

    Returns:
        Timezone-aware datetime object (UTC if no timezone specified).

    Raises:
        ValueError: If the string cannot be parsed as ISO 8601.

    Example:
        >>> parse_iso_datetime("2026-01-11T12:00:00Z")
        datetime.datetime(2026, 1, 11, 12, 0, tzinfo=datetime.timezone.utc)
    """
    # Handle Z suffix
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(value)
    except ValueError as e:
        raise ValueError(f"Cannot parse datetime: {value}") from e

    # Ensure timezone awareness (assume UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def parse_unix_timestamp(value: int | float) -> datetime:
    """Parse Unix timestamp to timezone-aware datetime.

    Args:
        value: Unix timestamp (seconds since epoch).

    Returns:
        Timezone-aware datetime object in UTC.

    Example:
        >>> parse_unix_timestamp(1768132800)
        datetime.datetime(2026, 1, 11, 12, 0, tzinfo=datetime.timezone.utc)
    """
    return datetime.fromtimestamp(value, tz=timezone.utc)


def parse_datetime_flexible(value: str | int | float) -> datetime:
    """Parse datetime from various formats.

    Attempts to parse the value as:
    1. ISO 8601 string (if string)
    2. Unix timestamp (if numeric or numeric string)

    Args:
        value: Datetime value in any supported format.

    Returns:
        Timezone-aware datetime object in UTC.

    Raises:
        ValueError: If the value cannot be parsed.

    Example:
        >>> parse_datetime_flexible("2026-01-11T12:00:00Z")
        datetime.datetime(2026, 1, 11, 12, 0, tzinfo=datetime.timezone.utc)
        >>> parse_datetime_flexible(1768132800)
        datetime.datetime(2026, 1, 11, 12, 0, tzinfo=datetime.timezone.utc)
    """
    if isinstance(value, (int, float)):
        return parse_unix_timestamp(value)

    # Try as numeric string
    try:
        return parse_unix_timestamp(float(value))
    except ValueError:
        pass

    # Try as ISO 8601
    return parse_iso_datetime(value)
