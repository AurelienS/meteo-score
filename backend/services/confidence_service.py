"""ConfidenceService for evaluating data reliability based on sample size.

This module provides confidence level assessment for accuracy metrics,
helping users understand when data is reliable vs. preliminary.

Implements story 3.5: Minimum Data Threshold Logic.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ConfidenceLevel(str, Enum):
    """Confidence level based on days of collected data."""

    INSUFFICIENT = "insufficient"
    PRELIMINARY = "preliminary"
    VALIDATED = "validated"


@dataclass
class ConfidenceMetadata:
    """Metadata about data confidence for UI display.

    Attributes:
        level: The confidence level classification.
        sample_size: Number of data points collected.
        days_of_data: Number of days covered by the data.
        label: Human-readable label for display.
        ui_color: Color hint for UI badges (red, orange, green).
        show_warning: Whether to display a warning indicator.
    """

    level: ConfidenceLevel
    sample_size: int
    days_of_data: int
    label: str
    ui_color: str
    show_warning: bool


class ConfidenceService:
    """Service for evaluating data confidence based on sample size and time range.

    Confidence levels are determined by the number of days of data:
    - < 30 days: INSUFFICIENT (not enough data for reliable metrics)
    - 30-89 days: PRELIMINARY (metrics are forming but not stable)
    - >= 90 days: VALIDATED (statistically reliable metrics)
    """

    PRELIMINARY_THRESHOLD = 30  # days
    VALIDATED_THRESHOLD = 90  # days

    def evaluate_confidence(
        self,
        sample_size: int,
        earliest_timestamp: datetime,
        latest_timestamp: datetime,
    ) -> ConfidenceMetadata:
        """Evaluate data confidence based on sample size and time range.

        Args:
            sample_size: Number of data points in the sample.
            earliest_timestamp: Timestamp of the earliest data point.
            latest_timestamp: Timestamp of the latest data point.

        Returns:
            ConfidenceMetadata with level, labels, and UI hints.
        """
        days_of_data = (latest_timestamp - earliest_timestamp).days

        if days_of_data < self.PRELIMINARY_THRESHOLD:
            return ConfidenceMetadata(
                level=ConfidenceLevel.INSUFFICIENT,
                sample_size=sample_size,
                days_of_data=days_of_data,
                label="Insufficient Data",
                ui_color="red",
                show_warning=True,
            )
        elif days_of_data < self.VALIDATED_THRESHOLD:
            return ConfidenceMetadata(
                level=ConfidenceLevel.PRELIMINARY,
                sample_size=sample_size,
                days_of_data=days_of_data,
                label="Preliminary",
                ui_color="orange",
                show_warning=True,
            )
        else:
            return ConfidenceMetadata(
                level=ConfidenceLevel.VALIDATED,
                sample_size=sample_size,
                days_of_data=days_of_data,
                label="Validated",
                ui_color="green",
                show_warning=False,
            )

    def get_confidence_message(self, metadata: ConfidenceMetadata) -> str:
        """Generate user-friendly confidence warning message.

        Args:
            metadata: ConfidenceMetadata from evaluate_confidence.

        Returns:
            Human-readable message explaining the confidence level.
        """
        if metadata.level == ConfidenceLevel.INSUFFICIENT:
            days_remaining = self.PRELIMINARY_THRESHOLD - metadata.days_of_data
            day_word = "day" if days_remaining == 1 else "days"
            return (
                f"Insufficient data ({metadata.days_of_data} days). "
                f"Collect {days_remaining} more {day_word} to reach preliminary status."
            )
        elif metadata.level == ConfidenceLevel.PRELIMINARY:
            days_remaining = self.VALIDATED_THRESHOLD - metadata.days_of_data
            day_word = "day" if days_remaining == 1 else "days"
            return (
                f"Results based on {metadata.days_of_data} days of data. "
                f"Metrics will stabilize after {days_remaining} more {day_word}."
            )
        else:
            return (
                f"Validated with {metadata.days_of_data} days of data. "
                f"These metrics are statistically reliable."
            )

    def get_confidence_with_metrics(
        self,
        metrics: Dict[str, Any],
        earliest_timestamp: datetime,
        latest_timestamp: datetime,
    ) -> Dict[str, Any]:
        """Combine accuracy metrics with confidence metadata.

        Args:
            metrics: Dictionary containing accuracy metrics (mae, bias, std_dev, sample_size).
            earliest_timestamp: Timestamp of the earliest data point.
            latest_timestamp: Timestamp of the latest data point.

        Returns:
            Dictionary containing both metrics and confidence information.
            Returns None for metrics if confidence level is INSUFFICIENT.
        """
        sample_size = metrics.get("sample_size", 0)
        confidence = self.evaluate_confidence(
            sample_size=sample_size,
            earliest_timestamp=earliest_timestamp,
            latest_timestamp=latest_timestamp,
        )
        message = self.get_confidence_message(confidence)

        return {
            "metrics": metrics if confidence.level != ConfidenceLevel.INSUFFICIENT else None,
            "confidence": {
                "level": confidence.level.value,
                "days_of_data": confidence.days_of_data,
                "label": confidence.label,
                "ui_color": confidence.ui_color,
                "show_warning": confidence.show_warning,
                "message": message,
            },
        }
