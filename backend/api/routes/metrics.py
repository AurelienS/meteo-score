"""Collection metrics API endpoint.

This module provides monitoring metrics for the data collection pipeline,
including success rates, collection durations, aberrant value counts,
and circuit breaker status.

Endpoints:
    GET /api/metrics/collection - Get comprehensive collection metrics
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from collectors.utils import CircuitBreaker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])


# =============================================================================
# Metrics Registry - Singleton to track metrics
# =============================================================================


class MetricsRegistry:
    """Singleton registry for collection metrics.

    Tracks per-collector success/failure rates, collection durations,
    and aberrant value counts.
    """

    _instance: Optional["MetricsRegistry"] = None

    def __new__(cls) -> "MetricsRegistry":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize metrics storage."""
        self._collector_stats: dict[str, dict[str, Any]] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._aberrant_counts: dict[str, int] = {}
        self._total_collections: int = 0
        self._successful_collections: int = 0
        self._start_time: datetime = datetime.now(timezone.utc)

    def record_collection(
        self,
        collector_name: str,
        success: bool,
        records_count: int,
        duration_seconds: float,
    ) -> None:
        """Record a collection attempt.

        Args:
            collector_name: Name of the collector (e.g., "MeteoParapente").
            success: Whether the collection succeeded.
            records_count: Number of records collected.
            duration_seconds: Duration of the collection.
        """
        if collector_name not in self._collector_stats:
            self._collector_stats[collector_name] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "total_records": 0,
                "total_duration_seconds": 0.0,
                "last_collection_time": None,
                "last_status": None,
            }

        stats = self._collector_stats[collector_name]
        stats["total_attempts"] += 1
        if success:
            stats["successful_attempts"] += 1
            self._successful_collections += 1
        stats["total_records"] += records_count
        stats["total_duration_seconds"] += duration_seconds
        stats["last_collection_time"] = datetime.now(timezone.utc).isoformat()
        stats["last_status"] = "success" if success else "failure"

        self._total_collections += 1

    def record_aberrant_value(self, collector_name: str) -> None:
        """Record detection of an aberrant value.

        Args:
            collector_name: Name of the collector that found the aberrant value.
        """
        if collector_name not in self._aberrant_counts:
            self._aberrant_counts[collector_name] = 0
        self._aberrant_counts[collector_name] += 1

    def register_circuit_breaker(
        self, name: str, circuit_breaker: CircuitBreaker
    ) -> None:
        """Register a circuit breaker for monitoring.

        Args:
            name: Identifier for the circuit breaker.
            circuit_breaker: The CircuitBreaker instance to monitor.
        """
        self._circuit_breakers[name] = circuit_breaker

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get a registered circuit breaker.

        Args:
            name: Identifier for the circuit breaker.

        Returns:
            The CircuitBreaker instance or None if not found.
        """
        return self._circuit_breakers.get(name)

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive metrics snapshot.

        Returns:
            Dict with collector stats, circuit breaker status, and aberrant counts.
        """
        # Calculate per-collector metrics
        collector_metrics = {}
        for name, stats in self._collector_stats.items():
            total = stats["total_attempts"]
            success_rate = (
                stats["successful_attempts"] / total if total > 0 else 0.0
            )
            avg_duration = (
                stats["total_duration_seconds"] / total if total > 0 else 0.0
            )

            collector_metrics[name] = {
                "success_rate": round(success_rate * 100, 2),
                "total_attempts": total,
                "successful_attempts": stats["successful_attempts"],
                "total_records": stats["total_records"],
                "average_duration_seconds": round(avg_duration, 3),
                "last_collection_time": stats["last_collection_time"],
                "last_status": stats["last_status"],
            }

        # Get circuit breaker statuses
        circuit_breaker_status = {
            name: cb.get_status() for name, cb in self._circuit_breakers.items()
        }

        # Calculate overall success rate
        overall_success_rate = (
            self._successful_collections / self._total_collections
            if self._total_collections > 0
            else 0.0
        )

        return {
            "overall": {
                "total_collections": self._total_collections,
                "successful_collections": self._successful_collections,
                "success_rate": round(overall_success_rate * 100, 2),
                "uptime_since": self._start_time.isoformat(),
            },
            "collectors": collector_metrics,
            "circuit_breakers": circuit_breaker_status,
            "aberrant_values": self._aberrant_counts.copy(),
        }

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        self._initialize()


def get_metrics_registry() -> MetricsRegistry:
    """Get the singleton MetricsRegistry instance.

    Returns:
        The MetricsRegistry singleton.
    """
    return MetricsRegistry()


# =============================================================================
# Response Schemas
# =============================================================================


class CollectorMetrics(BaseModel):
    """Metrics for a single collector."""

    model_config = ConfigDict(populate_by_name=True)

    success_rate: float = Field(alias="successRate")
    total_attempts: int = Field(alias="totalAttempts")
    successful_attempts: int = Field(alias="successfulAttempts")
    total_records: int = Field(alias="totalRecords")
    average_duration_seconds: float = Field(alias="averageDurationSeconds")
    last_collection_time: Optional[str] = Field(None, alias="lastCollectionTime")
    last_status: Optional[str] = Field(None, alias="lastStatus")


class CircuitBreakerStatus(BaseModel):
    """Status of a circuit breaker."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    state: str
    failure_count: int = Field(alias="failureCount")
    failure_threshold: int = Field(alias="failureThreshold")
    success_count: int = Field(alias="successCount")
    cooldown_remaining: Optional[float] = Field(None, alias="cooldownRemaining")


class OverallMetrics(BaseModel):
    """Overall collection metrics."""

    model_config = ConfigDict(populate_by_name=True)

    total_collections: int = Field(alias="totalCollections")
    successful_collections: int = Field(alias="successfulCollections")
    success_rate: float = Field(alias="successRate")
    uptime_since: str = Field(alias="uptimeSince")


class CollectionMetricsResponse(BaseModel):
    """Response schema for collection metrics endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    overall: OverallMetrics
    collectors: dict[str, CollectorMetrics]
    circuit_breakers: dict[str, CircuitBreakerStatus] = Field(alias="circuitBreakers")
    aberrant_values: dict[str, int] = Field(alias="aberrantValues")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/collection", response_model=CollectionMetricsResponse)
async def get_collection_metrics() -> dict[str, Any]:
    """Get comprehensive collection metrics.

    Returns metrics including:
    - Overall success rate and collection counts
    - Per-collector success rates, record counts, and durations
    - Circuit breaker status for each source
    - Aberrant value counts by collector

    Returns:
        CollectionMetricsResponse with all metrics.
    """
    registry = get_metrics_registry()
    return registry.get_metrics()
