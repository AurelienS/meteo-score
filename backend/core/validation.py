"""Data validation for weather forecasts and observations.

This module provides validation logic for detecting aberrant values
and ensuring data quality across all collected weather data.

Validation thresholds are based on physically reasonable ranges:
- Wind speed: 0-200 km/h (hurricane force is ~120 km/h)
- Temperature: -50°C to +50°C (extreme but possible)
- Wind direction: 0-360 degrees

Aberrant values are flagged but still stored to allow for review.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from core.data_models import ForecastData, ObservationData

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity level of validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """A single validation issue found in data."""

    field: str
    message: str
    severity: ValidationSeverity
    value: Any = None
    threshold: Any = None


@dataclass
class ValidationResult:
    """Result of data validation.

    Attributes:
        is_valid: True if no ERROR-level issues found.
        is_aberrant: True if any WARNING-level aberrant values found.
        issues: List of all validation issues.
        data: The validated data object.
    """

    is_valid: bool = True
    is_aberrant: bool = False
    issues: list[ValidationIssue] = field(default_factory=list)
    data: Optional[Any] = None

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue and update status flags."""
        self.issues.append(issue)
        if issue.severity == ValidationSeverity.ERROR:
            self.is_valid = False
        if issue.severity == ValidationSeverity.WARNING:
            self.is_aberrant = True


@dataclass
class ValidationThresholds:
    """Configurable thresholds for aberrant value detection.

    All thresholds are inclusive (min <= value <= max).
    """

    # Wind speed thresholds (km/h)
    wind_speed_min: Decimal = Decimal("0")
    wind_speed_max: Decimal = Decimal("200")

    # Temperature thresholds (°C)
    temperature_min: Decimal = Decimal("-50")
    temperature_max: Decimal = Decimal("50")

    # Wind direction thresholds (degrees)
    wind_direction_min: Decimal = Decimal("0")
    wind_direction_max: Decimal = Decimal("360")

    # Deviation threshold (absolute difference)
    deviation_max: Decimal = Decimal("100")

    # Timestamp thresholds
    max_future_hours: int = 168  # 7 days
    max_past_hours: int = 720  # 30 days


# Default thresholds instance
DEFAULT_THRESHOLDS = ValidationThresholds()


class DataValidator:
    """Validator for weather forecast and observation data.

    Validates data against configurable thresholds and flags
    aberrant values while still allowing them to be stored.

    Example:
        >>> validator = DataValidator()
        >>> result = validator.validate_forecast(forecast_data)
        >>> if result.is_aberrant:
        ...     logger.warning(f"Aberrant values detected: {result.issues}")
    """

    def __init__(self, thresholds: ValidationThresholds | None = None) -> None:
        """Initialize validator with thresholds.

        Args:
            thresholds: Custom thresholds or None for defaults.
        """
        self.thresholds = thresholds or DEFAULT_THRESHOLDS

    def validate_forecast(self, data: ForecastData) -> ValidationResult:
        """Validate forecast data.

        Checks:
        - Required fields are present
        - Value is within reasonable range for parameter type
        - Timestamps are valid and not too far in future/past

        Args:
            data: ForecastData to validate.

        Returns:
            ValidationResult with any issues found.
        """
        result = ValidationResult(data=data)

        # Check required fields
        if data.site_id is None:
            result.add_issue(ValidationIssue(
                field="site_id",
                message="site_id is required",
                severity=ValidationSeverity.ERROR,
            ))

        if data.model_id is None:
            result.add_issue(ValidationIssue(
                field="model_id",
                message="model_id is required",
                severity=ValidationSeverity.ERROR,
            ))

        if data.parameter_id is None:
            result.add_issue(ValidationIssue(
                field="parameter_id",
                message="parameter_id is required",
                severity=ValidationSeverity.ERROR,
            ))

        if data.value is None:
            result.add_issue(ValidationIssue(
                field="value",
                message="value is required",
                severity=ValidationSeverity.ERROR,
            ))
        else:
            # Check value ranges based on parameter_id
            # Parameter IDs: 1=wind_speed_avg, 2=wind_speed_max, 3=wind_direction, 4=temperature
            self._validate_value_range(result, data.value, data.parameter_id)

        # Check timestamps
        if data.valid_time is not None:
            self._validate_timestamp(result, data.valid_time, "valid_time")

        if data.forecast_run is not None:
            self._validate_timestamp(result, data.forecast_run, "forecast_run")

        # Log if aberrant
        if result.is_aberrant:
            logger.warning(
                f"Aberrant forecast value detected: site_id={data.site_id}, "
                f"model_id={data.model_id}, parameter_id={data.parameter_id}, "
                f"value={data.value}, issues={[i.message for i in result.issues]}"
            )

        return result

    def validate_observation(self, data: ObservationData) -> ValidationResult:
        """Validate observation data.

        Checks:
        - Required fields are present
        - Value is within reasonable range for parameter type
        - Observation time is recent (not too old or in future)

        Args:
            data: ObservationData to validate.

        Returns:
            ValidationResult with any issues found.
        """
        result = ValidationResult(data=data)

        # Check required fields
        if data.site_id is None:
            result.add_issue(ValidationIssue(
                field="site_id",
                message="site_id is required",
                severity=ValidationSeverity.ERROR,
            ))

        if data.parameter_id is None:
            result.add_issue(ValidationIssue(
                field="parameter_id",
                message="parameter_id is required",
                severity=ValidationSeverity.ERROR,
            ))

        if data.value is None:
            result.add_issue(ValidationIssue(
                field="value",
                message="value is required",
                severity=ValidationSeverity.ERROR,
            ))
        else:
            # Check value ranges
            self._validate_value_range(result, data.value, data.parameter_id)

        # Check observation time
        if data.observation_time is not None:
            self._validate_timestamp(
                result, data.observation_time, "observation_time", strict=True
            )

        # Log if aberrant
        if result.is_aberrant:
            logger.warning(
                f"Aberrant observation value detected: site_id={data.site_id}, "
                f"parameter_id={data.parameter_id}, value={data.value}, "
                f"issues={[i.message for i in result.issues]}"
            )

        return result

    def _validate_value_range(
        self,
        result: ValidationResult,
        value: Decimal,
        parameter_id: int | None,
    ) -> None:
        """Validate value is within acceptable range for parameter type.

        Args:
            result: ValidationResult to add issues to.
            value: Value to validate.
            parameter_id: Parameter type (1=wind_speed, 3=direction, 4=temp).
        """
        # Wind speed parameters (1=avg, 2=max)
        if parameter_id in (1, 2):
            if value < self.thresholds.wind_speed_min:
                result.add_issue(ValidationIssue(
                    field="value",
                    message=f"Wind speed {value} km/h is below minimum {self.thresholds.wind_speed_min}",
                    severity=ValidationSeverity.WARNING,
                    value=value,
                    threshold=self.thresholds.wind_speed_min,
                ))
            elif value > self.thresholds.wind_speed_max:
                result.add_issue(ValidationIssue(
                    field="value",
                    message=f"Wind speed {value} km/h exceeds maximum {self.thresholds.wind_speed_max}",
                    severity=ValidationSeverity.WARNING,
                    value=value,
                    threshold=self.thresholds.wind_speed_max,
                ))

        # Wind direction (3)
        elif parameter_id == 3:
            if value < self.thresholds.wind_direction_min:
                result.add_issue(ValidationIssue(
                    field="value",
                    message=f"Wind direction {value}° is below minimum {self.thresholds.wind_direction_min}",
                    severity=ValidationSeverity.WARNING,
                    value=value,
                    threshold=self.thresholds.wind_direction_min,
                ))
            elif value > self.thresholds.wind_direction_max:
                result.add_issue(ValidationIssue(
                    field="value",
                    message=f"Wind direction {value}° exceeds maximum {self.thresholds.wind_direction_max}",
                    severity=ValidationSeverity.WARNING,
                    value=value,
                    threshold=self.thresholds.wind_direction_max,
                ))

        # Temperature (4)
        elif parameter_id == 4:
            if value < self.thresholds.temperature_min:
                result.add_issue(ValidationIssue(
                    field="value",
                    message=f"Temperature {value}°C is below minimum {self.thresholds.temperature_min}",
                    severity=ValidationSeverity.WARNING,
                    value=value,
                    threshold=self.thresholds.temperature_min,
                ))
            elif value > self.thresholds.temperature_max:
                result.add_issue(ValidationIssue(
                    field="value",
                    message=f"Temperature {value}°C exceeds maximum {self.thresholds.temperature_max}",
                    severity=ValidationSeverity.WARNING,
                    value=value,
                    threshold=self.thresholds.temperature_max,
                ))

    def _validate_timestamp(
        self,
        result: ValidationResult,
        timestamp: datetime,
        field_name: str,
        strict: bool = False,
    ) -> None:
        """Validate timestamp is within acceptable range.

        Args:
            result: ValidationResult to add issues to.
            timestamp: Timestamp to validate.
            field_name: Name of the field being validated.
            strict: If True, use stricter bounds for observations.
        """
        now = datetime.now(timezone.utc)

        # Check for future timestamps
        max_future = timedelta(hours=self.thresholds.max_future_hours)
        if timestamp > now + max_future:
            result.add_issue(ValidationIssue(
                field=field_name,
                message=f"{field_name} is too far in the future: {timestamp.isoformat()}",
                severity=ValidationSeverity.WARNING,
                value=timestamp.isoformat(),
            ))

        # Check for old timestamps
        max_past = timedelta(hours=24 if strict else self.thresholds.max_past_hours)
        if timestamp < now - max_past:
            severity = ValidationSeverity.WARNING if strict else ValidationSeverity.INFO
            result.add_issue(ValidationIssue(
                field=field_name,
                message=f"{field_name} is older than expected: {timestamp.isoformat()}",
                severity=severity,
                value=timestamp.isoformat(),
            ))


def validate_forecast(data: ForecastData) -> ValidationResult:
    """Convenience function to validate forecast data with default thresholds.

    Args:
        data: ForecastData to validate.

    Returns:
        ValidationResult with any issues found.
    """
    return DataValidator().validate_forecast(data)


def validate_observation(data: ObservationData) -> ValidationResult:
    """Convenience function to validate observation data with default thresholds.

    Args:
        data: ObservationData to validate.

    Returns:
        ValidationResult with any issues found.
    """
    return DataValidator().validate_observation(data)
