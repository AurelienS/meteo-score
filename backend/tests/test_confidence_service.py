"""Tests for ConfidenceService and confidence threshold logic.

Tests cover:
- Boundary cases for confidence levels (29, 30, 89, 90 days)
- Warning message generation for each level
- Edge cases (0 days, same timestamp, large values)
"""

from datetime import datetime, timedelta, timezone

import pytest

from services.confidence_service import (
    ConfidenceLevel,
    ConfidenceMetadata,
    ConfidenceService,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def confidence_service():
    """Create ConfidenceService instance for testing."""
    return ConfidenceService()


@pytest.fixture
def base_timestamp():
    """Base timestamp for calculating date ranges."""
    return datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


# =============================================================================
# Test ConfidenceLevel Enum
# =============================================================================


class TestConfidenceLevelEnum:
    """Tests for ConfidenceLevel enum."""

    def test_confidence_level_values(self):
        """Test ConfidenceLevel enum has correct string values."""
        assert ConfidenceLevel.INSUFFICIENT.value == "insufficient"
        assert ConfidenceLevel.PRELIMINARY.value == "preliminary"
        assert ConfidenceLevel.VALIDATED.value == "validated"

    def test_confidence_level_is_string_enum(self):
        """Test ConfidenceLevel values can be used as strings."""
        assert str(ConfidenceLevel.INSUFFICIENT) == "ConfidenceLevel.INSUFFICIENT"
        assert ConfidenceLevel.VALIDATED == "validated"


# =============================================================================
# Test ConfidenceMetadata Dataclass
# =============================================================================


class TestConfidenceMetadataDataclass:
    """Tests for ConfidenceMetadata dataclass."""

    def test_confidence_metadata_creation(self):
        """Test ConfidenceMetadata can be created with all fields."""
        metadata = ConfidenceMetadata(
            level=ConfidenceLevel.VALIDATED,
            sample_size=500,
            days_of_data=120,
            label="Validated",
            ui_color="green",
            show_warning=False,
        )

        assert metadata.level == ConfidenceLevel.VALIDATED
        assert metadata.sample_size == 500
        assert metadata.days_of_data == 120
        assert metadata.label == "Validated"
        assert metadata.ui_color == "green"
        assert metadata.show_warning is False


# =============================================================================
# Test Threshold Constants
# =============================================================================


class TestThresholdConstants:
    """Tests for service threshold constants."""

    def test_preliminary_threshold_is_30(self, confidence_service):
        """Test PRELIMINARY_THRESHOLD is 30 days."""
        assert confidence_service.PRELIMINARY_THRESHOLD == 30

    def test_validated_threshold_is_90(self, confidence_service):
        """Test VALIDATED_THRESHOLD is 90 days."""
        assert confidence_service.VALIDATED_THRESHOLD == 90


# =============================================================================
# Test Boundary Cases - INSUFFICIENT
# =============================================================================


class TestInsufficientConfidence:
    """Tests for INSUFFICIENT confidence level (< 30 days)."""

    def test_29_days_returns_insufficient(self, confidence_service, base_timestamp):
        """Test 29 days of data returns INSUFFICIENT."""
        earliest = base_timestamp - timedelta(days=29)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=100,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.level == ConfidenceLevel.INSUFFICIENT
        assert result.days_of_data == 29
        assert result.ui_color == "red"
        assert result.show_warning is True

    def test_0_days_returns_insufficient(self, confidence_service, base_timestamp):
        """Test 0 days (same timestamp) returns INSUFFICIENT."""
        result = confidence_service.evaluate_confidence(
            sample_size=10,
            earliest_timestamp=base_timestamp,
            latest_timestamp=base_timestamp,
        )

        assert result.level == ConfidenceLevel.INSUFFICIENT
        assert result.days_of_data == 0
        assert result.ui_color == "red"

    def test_1_day_returns_insufficient(self, confidence_service, base_timestamp):
        """Test 1 day of data returns INSUFFICIENT."""
        earliest = base_timestamp - timedelta(days=1)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=24,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.level == ConfidenceLevel.INSUFFICIENT
        assert result.days_of_data == 1


# =============================================================================
# Test Boundary Cases - PRELIMINARY
# =============================================================================


class TestPreliminaryConfidence:
    """Tests for PRELIMINARY confidence level (30-89 days)."""

    def test_30_days_returns_preliminary(self, confidence_service, base_timestamp):
        """Test 30 days of data returns PRELIMINARY (lower boundary)."""
        earliest = base_timestamp - timedelta(days=30)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=200,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.level == ConfidenceLevel.PRELIMINARY
        assert result.days_of_data == 30
        assert result.ui_color == "orange"
        assert result.show_warning is True

    def test_89_days_returns_preliminary(self, confidence_service, base_timestamp):
        """Test 89 days of data returns PRELIMINARY (upper boundary)."""
        earliest = base_timestamp - timedelta(days=89)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=500,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.level == ConfidenceLevel.PRELIMINARY
        assert result.days_of_data == 89
        assert result.ui_color == "orange"

    def test_45_days_returns_preliminary(self, confidence_service, base_timestamp):
        """Test 45 days (middle value) returns PRELIMINARY."""
        earliest = base_timestamp - timedelta(days=45)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=300,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.level == ConfidenceLevel.PRELIMINARY
        assert result.days_of_data == 45


# =============================================================================
# Test Boundary Cases - VALIDATED
# =============================================================================


class TestValidatedConfidence:
    """Tests for VALIDATED confidence level (>= 90 days)."""

    def test_90_days_returns_validated(self, confidence_service, base_timestamp):
        """Test 90 days of data returns VALIDATED (boundary)."""
        earliest = base_timestamp - timedelta(days=90)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=600,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.level == ConfidenceLevel.VALIDATED
        assert result.days_of_data == 90
        assert result.ui_color == "green"
        assert result.show_warning is False

    def test_120_days_returns_validated(self, confidence_service, base_timestamp):
        """Test 120 days of data returns VALIDATED."""
        earliest = base_timestamp - timedelta(days=120)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=800,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.level == ConfidenceLevel.VALIDATED
        assert result.days_of_data == 120
        assert result.label == "Validated"

    def test_365_days_returns_validated(self, confidence_service, base_timestamp):
        """Test 365 days (one year) returns VALIDATED."""
        earliest = base_timestamp - timedelta(days=365)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=2000,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.level == ConfidenceLevel.VALIDATED
        assert result.days_of_data == 365


# =============================================================================
# Test Warning Messages
# =============================================================================


class TestWarningMessages:
    """Tests for get_confidence_message method."""

    def test_insufficient_message(self, confidence_service):
        """Test warning message for INSUFFICIENT level."""
        metadata = ConfidenceMetadata(
            level=ConfidenceLevel.INSUFFICIENT,
            sample_size=50,
            days_of_data=15,
            label="Insufficient Data",
            ui_color="red",
            show_warning=True,
        )

        message = confidence_service.get_confidence_message(metadata)

        assert "Insufficient data (15 days)" in message
        assert "Collect 15 more days" in message
        assert "preliminary status" in message

    def test_preliminary_message(self, confidence_service):
        """Test warning message for PRELIMINARY level."""
        metadata = ConfidenceMetadata(
            level=ConfidenceLevel.PRELIMINARY,
            sample_size=300,
            days_of_data=45,
            label="Preliminary",
            ui_color="orange",
            show_warning=True,
        )

        message = confidence_service.get_confidence_message(metadata)

        assert "Results based on 45 days" in message
        assert "45 more days" in message
        assert "stabilize" in message

    def test_validated_message(self, confidence_service):
        """Test message for VALIDATED level."""
        metadata = ConfidenceMetadata(
            level=ConfidenceLevel.VALIDATED,
            sample_size=700,
            days_of_data=120,
            label="Validated",
            ui_color="green",
            show_warning=False,
        )

        message = confidence_service.get_confidence_message(metadata)

        assert "Validated with 120 days" in message
        assert "statistically reliable" in message

    def test_message_at_boundary_30_days(self, confidence_service):
        """Test message at 30 days boundary shows correct days remaining."""
        metadata = ConfidenceMetadata(
            level=ConfidenceLevel.PRELIMINARY,
            sample_size=200,
            days_of_data=30,
            label="Preliminary",
            ui_color="orange",
            show_warning=True,
        )

        message = confidence_service.get_confidence_message(metadata)

        assert "60 more days" in message  # 90 - 30 = 60

    def test_message_at_boundary_89_days(self, confidence_service):
        """Test message at 89 days boundary shows correct days remaining with singular grammar."""
        metadata = ConfidenceMetadata(
            level=ConfidenceLevel.PRELIMINARY,
            sample_size=500,
            days_of_data=89,
            label="Preliminary",
            ui_color="orange",
            show_warning=True,
        )

        message = confidence_service.get_confidence_message(metadata)

        assert "1 more day" in message  # 90 - 89 = 1, singular form


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_large_sample_size(self, confidence_service, base_timestamp):
        """Test with very large sample size."""
        earliest = base_timestamp - timedelta(days=100)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=1_000_000,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.sample_size == 1_000_000
        assert result.level == ConfidenceLevel.VALIDATED

    def test_sample_size_preserved(self, confidence_service, base_timestamp):
        """Test that sample_size is correctly preserved in metadata."""
        earliest = base_timestamp - timedelta(days=50)
        latest = base_timestamp

        result = confidence_service.evaluate_confidence(
            sample_size=42,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.sample_size == 42

    def test_timestamps_with_different_times(self, confidence_service):
        """Test with timestamps that have different hour components."""
        earliest = datetime(2026, 1, 1, 6, 0, 0, tzinfo=timezone.utc)
        latest = datetime(2026, 2, 1, 18, 0, 0, tzinfo=timezone.utc)  # 31 days later

        result = confidence_service.evaluate_confidence(
            sample_size=100,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.days_of_data == 31
        assert result.level == ConfidenceLevel.PRELIMINARY

    def test_naive_datetime_support(self, confidence_service):
        """Test with naive datetime objects (no timezone)."""
        earliest = datetime(2026, 1, 1, 0, 0, 0)
        latest = datetime(2026, 4, 1, 0, 0, 0)  # 90 days

        result = confidence_service.evaluate_confidence(
            sample_size=100,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.days_of_data == 90
        assert result.level == ConfidenceLevel.VALIDATED

    def test_negative_days_returns_insufficient(self, confidence_service, base_timestamp):
        """Test with reversed timestamps (negative days) returns INSUFFICIENT."""
        # When earliest is after latest, days_of_data will be negative
        earliest = base_timestamp
        latest = base_timestamp - timedelta(days=10)  # 10 days before

        result = confidence_service.evaluate_confidence(
            sample_size=50,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result.days_of_data == -10
        assert result.level == ConfidenceLevel.INSUFFICIENT


# =============================================================================
# Test get_confidence_with_metrics
# =============================================================================


class TestGetConfidenceWithMetrics:
    """Tests for get_confidence_with_metrics method."""

    def test_returns_metrics_for_validated(self, confidence_service, base_timestamp):
        """Test that metrics are returned when confidence is VALIDATED."""
        metrics = {"mae": 4.2, "bias": -1.5, "std_dev": 3.8, "sample_size": 500}
        earliest = base_timestamp - timedelta(days=100)
        latest = base_timestamp

        result = confidence_service.get_confidence_with_metrics(
            metrics=metrics,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result["metrics"] == metrics
        assert result["confidence"]["level"] == "validated"
        assert result["confidence"]["ui_color"] == "green"

    def test_returns_none_metrics_for_insufficient(self, confidence_service, base_timestamp):
        """Test that metrics are None when confidence is INSUFFICIENT."""
        metrics = {"mae": 4.2, "bias": -1.5, "std_dev": 3.8, "sample_size": 10}
        earliest = base_timestamp - timedelta(days=10)
        latest = base_timestamp

        result = confidence_service.get_confidence_with_metrics(
            metrics=metrics,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result["metrics"] is None
        assert result["confidence"]["level"] == "insufficient"
        assert result["confidence"]["show_warning"] is True

    def test_returns_metrics_for_preliminary(self, confidence_service, base_timestamp):
        """Test that metrics are returned when confidence is PRELIMINARY."""
        metrics = {"mae": 3.5, "bias": 0.5, "std_dev": 2.1, "sample_size": 200}
        earliest = base_timestamp - timedelta(days=50)
        latest = base_timestamp

        result = confidence_service.get_confidence_with_metrics(
            metrics=metrics,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert result["metrics"] == metrics
        assert result["confidence"]["level"] == "preliminary"
        assert "message" in result["confidence"]

    def test_includes_message_in_confidence(self, confidence_service, base_timestamp):
        """Test that confidence includes a message."""
        metrics = {"sample_size": 100}
        earliest = base_timestamp - timedelta(days=45)
        latest = base_timestamp

        result = confidence_service.get_confidence_with_metrics(
            metrics=metrics,
            earliest_timestamp=earliest,
            latest_timestamp=latest,
        )

        assert "message" in result["confidence"]
        assert "45 days" in result["confidence"]["message"]
