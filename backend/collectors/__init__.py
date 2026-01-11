"""Weather data collectors module.

Exports:
    - BaseCollector: Abstract base class for all collectors
    - Utilities: HttpClient, retry decorator, date parsing
    - Exceptions: CollectorError, HttpClientError, RetryExhaustedError
"""

from backend.collectors.base import BaseCollector
from backend.collectors.utils import (
    BASE_DELAY,
    DEFAULT_TIMEOUT,
    MAX_DELAY,
    MAX_RETRIES,
    CollectorError,
    HttpClient,
    HttpClientError,
    RetryExhaustedError,
    parse_datetime_flexible,
    parse_iso_datetime,
    parse_unix_timestamp,
    retry_with_backoff,
)

__all__ = [
    # Base class
    "BaseCollector",
    # HTTP client
    "HttpClient",
    # Exceptions
    "CollectorError",
    "HttpClientError",
    "RetryExhaustedError",
    # Retry decorator
    "retry_with_backoff",
    # Date parsing utilities
    "parse_iso_datetime",
    "parse_unix_timestamp",
    "parse_datetime_flexible",
    # Constants
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES",
    "BASE_DELAY",
    "MAX_DELAY",
]
