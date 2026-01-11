"""Utility functions and classes for weather data collectors.

This module provides common utilities used across all collector implementations:
- Exponential backoff retry decorator for resilient API calls
- HTTP client wrapper with timeout and error handling
- Date/time parsing utilities for various formats

These utilities ensure consistent error handling and retry behavior
across all weather data sources (AROME, Meteo-Parapente, ROMMA, FFVL).
"""

import asyncio
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

import httpx

# Constants
DEFAULT_TIMEOUT = 30.0  # seconds
MAX_RETRIES = 3
BASE_DELAY = 1.0  # seconds
MAX_DELAY = 60.0  # seconds

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
