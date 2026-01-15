"""Services module for MétéoScore business logic.

This module contains service classes that implement core business logic:
- MatchingService: Matches forecasts with observations within time tolerance
- DeviationService: Calculates deviations from forecast-observation pairs
- MetricsService: Calculates statistical accuracy metrics (MAE, bias, CI)
"""

from services.deviation_service import (
    DeviationService,
    _normalize_datetime as normalize_datetime_for_db,
)
from services.matching_service import (
    MatchingService,
    calculate_horizon,
    calculate_time_diff_minutes,
    is_within_tolerance,
)
from services.metrics_service import (
    AccuracyMetrics,
    MetricsService,
)

__all__ = [
    "AccuracyMetrics",
    "DeviationService",
    "MatchingService",
    "MetricsService",
    "calculate_horizon",
    "calculate_time_diff_minutes",
    "is_within_tolerance",
    "normalize_datetime_for_db",
]
