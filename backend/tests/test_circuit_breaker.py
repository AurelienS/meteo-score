"""Tests for circuit breaker pattern implementation.

Tests verify:
- State transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED)
- Failure threshold triggering
- Cooldown period behavior
- Success/failure recording
- Status reporting for monitoring
"""

import time
from unittest.mock import patch

import pytest

from collectors.utils import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerState,
)


# =============================================================================
# Test: Basic State Management
# =============================================================================


class TestCircuitBreakerBasicState:
    """Tests for basic circuit breaker state management."""

    def test_initial_state_is_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.is_closed is True
        assert breaker.is_open is False

    def test_check_passes_when_closed(self):
        """Test check() does not raise when closed."""
        breaker = CircuitBreaker("test")
        breaker.check()  # Should not raise

    def test_success_keeps_circuit_closed(self):
        """Test recording success keeps circuit closed."""
        breaker = CircuitBreaker("test")
        breaker.record_success()
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_single_failure_does_not_open_circuit(self):
        """Test single failure doesn't open circuit."""
        breaker = CircuitBreaker("test", failure_threshold=5)
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker._failure_count == 1


# =============================================================================
# Test: Failure Threshold
# =============================================================================


class TestCircuitBreakerFailureThreshold:
    """Tests for failure threshold behavior."""

    def test_opens_after_threshold_failures(self):
        """Test circuit opens after reaching failure threshold."""
        breaker = CircuitBreaker("test", failure_threshold=3)

        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.is_open is True

    def test_custom_failure_threshold(self):
        """Test custom failure threshold is respected."""
        breaker = CircuitBreaker("test", failure_threshold=10)

        for _ in range(9):
            breaker.record_failure()

        assert breaker.state == CircuitBreakerState.CLOSED

        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

    def test_success_resets_failure_count(self):
        """Test success resets the failure counter."""
        breaker = CircuitBreaker("test", failure_threshold=5)

        # Record 4 failures (one below threshold)
        for _ in range(4):
            breaker.record_failure()

        assert breaker._failure_count == 4

        # Success resets counter
        breaker.record_success()
        assert breaker._failure_count == 0
        assert breaker.state == CircuitBreakerState.CLOSED


# =============================================================================
# Test: Open State Behavior
# =============================================================================


class TestCircuitBreakerOpenState:
    """Tests for open circuit behavior."""

    def test_check_raises_when_open(self):
        """Test check() raises CircuitBreakerOpenError when open."""
        breaker = CircuitBreaker("test", failure_threshold=1, cooldown_seconds=60)
        breaker.record_failure()

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            breaker.check()

        assert exc_info.value.name == "test"
        assert exc_info.value.cooldown_remaining > 0

    def test_error_message_includes_name_and_cooldown(self):
        """Test error message includes circuit name and cooldown."""
        breaker = CircuitBreaker("my_api", failure_threshold=1, cooldown_seconds=60)
        breaker.record_failure()

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            breaker.check()

        error_msg = str(exc_info.value)
        assert "my_api" in error_msg
        assert "Retry in" in error_msg


# =============================================================================
# Test: Half-Open State and Recovery
# =============================================================================


class TestCircuitBreakerHalfOpen:
    """Tests for half-open state and recovery."""

    def test_transitions_to_half_open_after_cooldown(self):
        """Test circuit transitions to HALF_OPEN after cooldown."""
        breaker = CircuitBreaker("test", failure_threshold=1, cooldown_seconds=0.1)
        breaker.record_failure()

        assert breaker.state == CircuitBreakerState.OPEN

        # Wait for cooldown
        time.sleep(0.15)

        # Accessing state triggers transition
        assert breaker.state == CircuitBreakerState.HALF_OPEN

    def test_success_in_half_open_closes_circuit(self):
        """Test success in HALF_OPEN state closes circuit."""
        breaker = CircuitBreaker("test", failure_threshold=1, cooldown_seconds=0.1)
        breaker.record_failure()

        time.sleep(0.15)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        breaker.record_success()
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_failure_in_half_open_reopens_circuit(self):
        """Test failure in HALF_OPEN state reopens circuit."""
        breaker = CircuitBreaker("test", failure_threshold=1, cooldown_seconds=0.1)
        breaker.record_failure()

        time.sleep(0.15)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

    def test_check_passes_in_half_open(self):
        """Test check() passes in HALF_OPEN state to allow test request."""
        breaker = CircuitBreaker("test", failure_threshold=1, cooldown_seconds=0.1)
        breaker.record_failure()

        time.sleep(0.15)
        breaker.check()  # Should not raise in HALF_OPEN


# =============================================================================
# Test: Reset
# =============================================================================


class TestCircuitBreakerReset:
    """Tests for circuit breaker reset."""

    def test_reset_closes_open_circuit(self):
        """Test reset() closes an open circuit."""
        breaker = CircuitBreaker("test", failure_threshold=1)
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

        breaker.reset()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker._failure_count == 0

    def test_reset_clears_all_counters(self):
        """Test reset() clears all internal counters."""
        breaker = CircuitBreaker("test", failure_threshold=5)

        # Build up some state
        for _ in range(3):
            breaker.record_failure()
        breaker.record_success()
        breaker.record_success()

        breaker.reset()

        assert breaker._failure_count == 0
        assert breaker._success_count == 0
        assert breaker._last_failure_time is None


# =============================================================================
# Test: Status Reporting
# =============================================================================


class TestCircuitBreakerStatus:
    """Tests for status reporting functionality."""

    def test_status_includes_basic_info(self):
        """Test status includes name, state, and counts."""
        breaker = CircuitBreaker("api_service", failure_threshold=5)
        breaker.record_success()
        breaker.record_failure()

        status = breaker.get_status()

        assert status["name"] == "api_service"
        assert status["state"] == "closed"
        assert status["failure_count"] == 1
        assert status["success_count"] == 1
        assert status["failure_threshold"] == 5

    def test_status_includes_cooldown_when_open(self):
        """Test status includes cooldown_remaining when open."""
        breaker = CircuitBreaker("test", failure_threshold=1, cooldown_seconds=60)
        breaker.record_failure()

        status = breaker.get_status()

        assert "cooldown_remaining" in status
        assert status["cooldown_remaining"] > 0
        assert status["cooldown_remaining"] <= 60

    def test_status_no_cooldown_when_closed(self):
        """Test status does not include cooldown_remaining when closed."""
        breaker = CircuitBreaker("test")
        status = breaker.get_status()

        assert "cooldown_remaining" not in status


# =============================================================================
# Test: Logging
# =============================================================================


class TestCircuitBreakerLogging:
    """Tests for circuit breaker logging."""

    def test_logs_when_opening(self, caplog):
        """Test warning is logged when circuit opens."""
        breaker = CircuitBreaker("test_api", failure_threshold=2)

        with caplog.at_level("WARNING"):
            breaker.record_failure()
            breaker.record_failure()

        assert "test_api" in caplog.text
        assert "opened" in caplog.text

    def test_logs_when_half_open(self, caplog):
        """Test info is logged when entering HALF_OPEN."""
        breaker = CircuitBreaker("test_api", failure_threshold=1, cooldown_seconds=0.1)
        breaker.record_failure()

        time.sleep(0.15)

        with caplog.at_level("INFO"):
            _ = breaker.state  # Triggers transition

        assert "HALF_OPEN" in caplog.text

    def test_logs_when_closing_after_recovery(self, caplog):
        """Test info is logged when circuit closes after recovery."""
        breaker = CircuitBreaker("test_api", failure_threshold=1, cooldown_seconds=0.1)
        breaker.record_failure()

        time.sleep(0.15)
        _ = breaker.state  # Enter HALF_OPEN

        with caplog.at_level("INFO"):
            breaker.record_success()

        assert "closing" in caplog.text


# =============================================================================
# Test: Thread Safety Considerations
# =============================================================================


class TestCircuitBreakerTimingEdgeCases:
    """Tests for timing edge cases."""

    def test_cooldown_remaining_is_zero_after_cooldown(self):
        """Test cooldown_remaining reaches zero after cooldown period."""
        breaker = CircuitBreaker("test", failure_threshold=1, cooldown_seconds=0.1)
        breaker.record_failure()

        time.sleep(0.15)

        # Force state to OPEN to test cooldown calculation
        breaker._state = CircuitBreakerState.OPEN
        status = breaker.get_status()

        assert status.get("cooldown_remaining", 0) == 0

    def test_monotonic_time_used_for_timing(self):
        """Test that time.monotonic is used (not affected by system time changes)."""
        breaker = CircuitBreaker("test", failure_threshold=1)

        with patch("collectors.utils.time.monotonic") as mock_monotonic:
            mock_monotonic.return_value = 1000.0
            breaker.record_failure()

            assert breaker._last_failure_time == 1000.0
