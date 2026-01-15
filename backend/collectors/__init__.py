"""Weather data collectors module.

Exports:
    - BaseCollector: Abstract base class for all collectors
    - MeteoParapenteCollector: Meteo-Parapente JSON API collector
    - AROMECollector: AROME GRIB2 forecast collector
    - ROMMaCollector: ROMMA beacon HTML scraping collector
    - FFVLCollector: FFVL beacon HTML scraping collector
    - CircuitBreaker: Circuit breaker pattern for API resilience
    - Utilities: HttpClient, retry decorator, date parsing
    - Exceptions: CollectorError, HttpClientError, RetryExhaustedError, CircuitBreakerOpenError
"""

from collectors.arome import AROMECollector
from collectors.base import BaseCollector
from collectors.ffvl import FFVLCollector
from collectors.meteo_parapente import MeteoParapenteCollector
from collectors.romma import ROMMaCollector
from collectors.utils import (
    BASE_DELAY,
    CIRCUIT_COOLDOWN_SECONDS,
    CIRCUIT_FAILURE_THRESHOLD,
    DEFAULT_TIMEOUT,
    MAX_DELAY,
    MAX_RETRIES,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
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
    # Collectors
    "MeteoParapenteCollector",
    "AROMECollector",
    "ROMMaCollector",
    "FFVLCollector",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerState",
    # HTTP client
    "HttpClient",
    # Exceptions
    "CollectorError",
    "HttpClientError",
    "RetryExhaustedError",
    "CircuitBreakerOpenError",
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
    "CIRCUIT_FAILURE_THRESHOLD",
    "CIRCUIT_COOLDOWN_SECONDS",
]
