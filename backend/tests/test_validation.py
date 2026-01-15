"""Tests for data validation module.

Tests verify:
- Forecast validation with aberrant value detection
- Observation validation with value range checks
- Timestamp validation (future/past bounds)
- ValidationResult structure and flags
- Custom threshold configuration
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from core.data_models import ForecastData, ObservationData
from core.validation import (
    DataValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationThresholds,
    validate_forecast,
    validate_observation,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def validator() -> DataValidator:
    """Provide a DataValidator with default thresholds."""
    return DataValidator()


@pytest.fixture
def valid_forecast() -> ForecastData:
    """Provide valid forecast data."""
    return ForecastData(
        site_id=1,
        model_id=1,
        parameter_id=1,  # wind_speed_avg
        forecast_run=datetime.now(timezone.utc),
        valid_time=datetime.now(timezone.utc) + timedelta(hours=6),
        horizon=6,
        value=Decimal("25.5"),
    )


@pytest.fixture
def valid_observation() -> ObservationData:
    """Provide valid observation data."""
    return ObservationData(
        site_id=1,
        parameter_id=1,  # wind_speed_avg
        observation_time=datetime.now(timezone.utc),
        value=Decimal("23.0"),
    )


# =============================================================================
# Test: ValidationResult
# =============================================================================


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_empty_result_is_valid(self):
        """Test new result has is_valid=True."""
        result = ValidationResult()
        assert result.is_valid is True
        assert result.is_aberrant is False
        assert len(result.issues) == 0

    def test_error_issue_sets_invalid(self):
        """Test ERROR severity sets is_valid=False."""
        from core.validation import ValidationIssue

        result = ValidationResult()
        result.add_issue(ValidationIssue(
            field="test",
            message="Test error",
            severity=ValidationSeverity.ERROR,
        ))
        assert result.is_valid is False

    def test_warning_issue_sets_aberrant(self):
        """Test WARNING severity sets is_aberrant=True."""
        from core.validation import ValidationIssue

        result = ValidationResult()
        result.add_issue(ValidationIssue(
            field="test",
            message="Test warning",
            severity=ValidationSeverity.WARNING,
        ))
        assert result.is_aberrant is True
        assert result.is_valid is True  # Warnings don't invalidate

    def test_info_issue_does_not_change_flags(self):
        """Test INFO severity doesn't change flags."""
        from core.validation import ValidationIssue

        result = ValidationResult()
        result.add_issue(ValidationIssue(
            field="test",
            message="Test info",
            severity=ValidationSeverity.INFO,
        ))
        assert result.is_valid is True
        assert result.is_aberrant is False


# =============================================================================
# Test: Forecast Validation
# =============================================================================


class TestForecastValidation:
    """Tests for forecast data validation."""

    def test_valid_forecast_passes(self, validator, valid_forecast):
        """Test valid forecast data passes validation."""
        result = validator.validate_forecast(valid_forecast)
        assert result.is_valid is True
        assert result.is_aberrant is False

    def test_missing_site_id_is_error(self, validator):
        """Test missing site_id is ERROR."""
        data = ForecastData(
            site_id=None,
            model_id=1,
            parameter_id=1,
            forecast_run=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            horizon=6,
            value=Decimal("10"),
        )
        result = validator.validate_forecast(data)
        assert result.is_valid is False
        assert any(i.field == "site_id" for i in result.issues)

    def test_missing_value_is_error(self, validator):
        """Test missing value is ERROR."""
        data = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            horizon=6,
            value=None,
        )
        result = validator.validate_forecast(data)
        assert result.is_valid is False
        assert any(i.field == "value" for i in result.issues)

    def test_wind_speed_above_max_is_aberrant(self, validator):
        """Test wind speed >200 km/h is flagged as aberrant."""
        data = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,  # wind_speed_avg
            forecast_run=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            horizon=6,
            value=Decimal("250"),  # >200 km/h
        )
        result = validator.validate_forecast(data)
        assert result.is_aberrant is True
        assert result.is_valid is True  # Still valid, just aberrant

    def test_wind_speed_negative_is_aberrant(self, validator):
        """Test negative wind speed is flagged as aberrant."""
        data = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            horizon=6,
            value=Decimal("-5"),
        )
        result = validator.validate_forecast(data)
        assert result.is_aberrant is True

    def test_temperature_above_max_is_aberrant(self, validator):
        """Test temperature >50°C is flagged as aberrant."""
        data = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=4,  # temperature
            forecast_run=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            horizon=6,
            value=Decimal("55"),  # >50°C
        )
        result = validator.validate_forecast(data)
        assert result.is_aberrant is True

    def test_temperature_below_min_is_aberrant(self, validator):
        """Test temperature <-50°C is flagged as aberrant."""
        data = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=4,
            forecast_run=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            horizon=6,
            value=Decimal("-60"),
        )
        result = validator.validate_forecast(data)
        assert result.is_aberrant is True

    def test_wind_direction_out_of_range_is_aberrant(self, validator):
        """Test wind direction outside 0-360 is flagged."""
        data = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=3,  # wind_direction
            forecast_run=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            horizon=6,
            value=Decimal("400"),  # >360
        )
        result = validator.validate_forecast(data)
        assert result.is_aberrant is True


# =============================================================================
# Test: Observation Validation
# =============================================================================


class TestObservationValidation:
    """Tests for observation data validation."""

    def test_valid_observation_passes(self, validator, valid_observation):
        """Test valid observation data passes validation."""
        result = validator.validate_observation(valid_observation)
        assert result.is_valid is True
        assert result.is_aberrant is False

    def test_missing_site_id_is_error(self, validator):
        """Test missing site_id is ERROR."""
        data = ObservationData(
            site_id=None,
            parameter_id=1,
            observation_time=datetime.now(timezone.utc),
            value=Decimal("10"),
        )
        result = validator.validate_observation(data)
        assert result.is_valid is False

    def test_aberrant_wind_speed_flagged(self, validator):
        """Test aberrant wind speed is flagged."""
        data = ObservationData(
            site_id=1,
            parameter_id=1,
            observation_time=datetime.now(timezone.utc),
            value=Decimal("220"),  # >200 km/h
        )
        result = validator.validate_observation(data)
        assert result.is_aberrant is True

    def test_old_observation_flagged(self, validator):
        """Test observation older than 24h is flagged."""
        data = ObservationData(
            site_id=1,
            parameter_id=1,
            observation_time=datetime.now(timezone.utc) - timedelta(hours=48),
            value=Decimal("15"),
        )
        result = validator.validate_observation(data)
        # Old observations get a warning
        assert any(i.field == "observation_time" for i in result.issues)


# =============================================================================
# Test: Custom Thresholds
# =============================================================================


class TestCustomThresholds:
    """Tests for custom validation thresholds."""

    def test_custom_wind_speed_threshold(self):
        """Test custom wind speed threshold is respected."""
        thresholds = ValidationThresholds(wind_speed_max=Decimal("100"))
        validator = DataValidator(thresholds)

        data = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=1,
            forecast_run=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            horizon=6,
            value=Decimal("120"),  # >100 with custom threshold
        )
        result = validator.validate_forecast(data)
        assert result.is_aberrant is True

    def test_custom_temperature_threshold(self):
        """Test custom temperature threshold is respected."""
        thresholds = ValidationThresholds(temperature_max=Decimal("40"))
        validator = DataValidator(thresholds)

        data = ForecastData(
            site_id=1,
            model_id=1,
            parameter_id=4,
            forecast_run=datetime.now(timezone.utc),
            valid_time=datetime.now(timezone.utc),
            horizon=6,
            value=Decimal("45"),  # >40 with custom threshold
        )
        result = validator.validate_forecast(data)
        assert result.is_aberrant is True


# =============================================================================
# Test: Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
    """Tests for validate_forecast and validate_observation functions."""

    def test_validate_forecast_function(self, valid_forecast):
        """Test validate_forecast convenience function."""
        result = validate_forecast(valid_forecast)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    def test_validate_observation_function(self, valid_observation):
        """Test validate_observation convenience function."""
        result = validate_observation(valid_observation)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
