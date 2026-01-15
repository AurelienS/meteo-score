"""Tests for collection metrics endpoint.

Tests verify:
- MetricsRegistry singleton behavior
- Collection recording and success rate calculation
- Aberrant value tracking
- Circuit breaker status exposure
- API endpoint response format
"""

import pytest
from fastapi.testclient import TestClient

from api.routes.metrics import MetricsRegistry, get_metrics_registry
from collectors.utils import CircuitBreaker
from main import app


@pytest.fixture
def client():
    """Provide FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def metrics_registry():
    """Provide a fresh MetricsRegistry for testing."""
    registry = get_metrics_registry()
    registry.reset()
    return registry


# =============================================================================
# Test: MetricsRegistry
# =============================================================================


class TestMetricsRegistry:
    """Tests for MetricsRegistry class."""

    def test_singleton_pattern(self):
        """Test that MetricsRegistry is a singleton."""
        registry1 = MetricsRegistry()
        registry2 = MetricsRegistry()
        assert registry1 is registry2

    def test_record_collection_success(self, metrics_registry):
        """Test recording a successful collection."""
        metrics_registry.record_collection(
            collector_name="TestCollector",
            success=True,
            records_count=10,
            duration_seconds=1.5,
        )

        metrics = metrics_registry.get_metrics()
        assert metrics["collectors"]["TestCollector"]["total_attempts"] == 1
        assert metrics["collectors"]["TestCollector"]["successful_attempts"] == 1
        assert metrics["collectors"]["TestCollector"]["total_records"] == 10
        assert metrics["collectors"]["TestCollector"]["success_rate"] == 100.0

    def test_record_collection_failure(self, metrics_registry):
        """Test recording a failed collection."""
        metrics_registry.record_collection(
            collector_name="TestCollector",
            success=False,
            records_count=0,
            duration_seconds=0.5,
        )

        metrics = metrics_registry.get_metrics()
        assert metrics["collectors"]["TestCollector"]["total_attempts"] == 1
        assert metrics["collectors"]["TestCollector"]["successful_attempts"] == 0
        assert metrics["collectors"]["TestCollector"]["success_rate"] == 0.0

    def test_success_rate_calculation(self, metrics_registry):
        """Test success rate is calculated correctly."""
        # 2 successes, 1 failure = 66.67%
        metrics_registry.record_collection("Test", True, 10, 1.0)
        metrics_registry.record_collection("Test", True, 5, 1.0)
        metrics_registry.record_collection("Test", False, 0, 0.5)

        metrics = metrics_registry.get_metrics()
        assert metrics["collectors"]["Test"]["success_rate"] == 66.67

    def test_average_duration_calculation(self, metrics_registry):
        """Test average duration is calculated correctly."""
        metrics_registry.record_collection("Test", True, 10, 1.0)
        metrics_registry.record_collection("Test", True, 10, 2.0)
        metrics_registry.record_collection("Test", True, 10, 3.0)

        metrics = metrics_registry.get_metrics()
        # (1.0 + 2.0 + 3.0) / 3 = 2.0
        assert metrics["collectors"]["Test"]["average_duration_seconds"] == 2.0

    def test_record_aberrant_value(self, metrics_registry):
        """Test recording aberrant values."""
        metrics_registry.record_aberrant_value("MeteoParapente")
        metrics_registry.record_aberrant_value("MeteoParapente")
        metrics_registry.record_aberrant_value("AROME")

        metrics = metrics_registry.get_metrics()
        assert metrics["aberrant_values"]["MeteoParapente"] == 2
        assert metrics["aberrant_values"]["AROME"] == 1

    def test_register_circuit_breaker(self, metrics_registry):
        """Test registering circuit breakers."""
        breaker = CircuitBreaker("test_api")
        metrics_registry.register_circuit_breaker("test_api", breaker)

        metrics = metrics_registry.get_metrics()
        assert "test_api" in metrics["circuit_breakers"]
        assert metrics["circuit_breakers"]["test_api"]["state"] == "closed"

    def test_circuit_breaker_status_in_metrics(self, metrics_registry):
        """Test circuit breaker status is exposed in metrics."""
        breaker = CircuitBreaker("api", failure_threshold=2)
        metrics_registry.register_circuit_breaker("api", breaker)

        # Open the circuit
        breaker.record_failure()
        breaker.record_failure()

        metrics = metrics_registry.get_metrics()
        assert metrics["circuit_breakers"]["api"]["state"] == "open"
        assert metrics["circuit_breakers"]["api"]["failure_count"] == 2

    def test_overall_metrics(self, metrics_registry):
        """Test overall metrics are calculated."""
        metrics_registry.record_collection("A", True, 10, 1.0)
        metrics_registry.record_collection("B", True, 5, 1.0)
        metrics_registry.record_collection("A", False, 0, 0.5)

        metrics = metrics_registry.get_metrics()
        assert metrics["overall"]["total_collections"] == 3
        assert metrics["overall"]["successful_collections"] == 2
        assert metrics["overall"]["success_rate"] == 66.67

    def test_reset_clears_metrics(self, metrics_registry):
        """Test reset clears all metrics."""
        metrics_registry.record_collection("Test", True, 10, 1.0)
        metrics_registry.record_aberrant_value("Test")
        metrics_registry.reset()

        metrics = metrics_registry.get_metrics()
        assert metrics["collectors"] == {}
        assert metrics["aberrant_values"] == {}
        assert metrics["overall"]["total_collections"] == 0


# =============================================================================
# Test: API Endpoint
# =============================================================================


class TestMetricsEndpoint:
    """Tests for /api/metrics/collection endpoint."""

    def test_endpoint_returns_200(self, client, metrics_registry):
        """Test endpoint returns 200 OK."""
        response = client.get("/api/metrics/collection")
        assert response.status_code == 200

    def test_endpoint_returns_json(self, client, metrics_registry):
        """Test endpoint returns valid JSON."""
        response = client.get("/api/metrics/collection")
        data = response.json()
        assert "overall" in data
        assert "collectors" in data
        assert "circuitBreakers" in data
        assert "aberrantValues" in data

    def test_response_uses_camel_case(self, client, metrics_registry):
        """Test response uses camelCase per project convention."""
        metrics_registry.record_collection("Test", True, 10, 1.5)
        response = client.get("/api/metrics/collection")
        data = response.json()

        # Check top-level camelCase
        assert "circuitBreakers" in data
        assert "aberrantValues" in data

        # Check nested camelCase
        assert "totalCollections" in data["overall"]
        assert "successfulCollections" in data["overall"]
        assert "successRate" in data["overall"]
        assert "uptimeSince" in data["overall"]

        # Check collector metrics camelCase
        if "Test" in data["collectors"]:
            collector = data["collectors"]["Test"]
            assert "successRate" in collector
            assert "totalAttempts" in collector
            assert "successfulAttempts" in collector
            assert "totalRecords" in collector
            assert "averageDurationSeconds" in collector
            assert "lastCollectionTime" in collector
            assert "lastStatus" in collector

    def test_response_includes_uptime(self, client, metrics_registry):
        """Test response includes uptime_since timestamp."""
        response = client.get("/api/metrics/collection")
        data = response.json()

        assert "uptimeSince" in data["overall"]
        # Should be ISO format
        assert "T" in data["overall"]["uptimeSince"]

    def test_empty_metrics_returns_zeros(self, client, metrics_registry):
        """Test empty registry returns zero values."""
        response = client.get("/api/metrics/collection")
        data = response.json()

        assert data["overall"]["totalCollections"] == 0
        assert data["overall"]["successRate"] == 0
        assert data["collectors"] == {}
