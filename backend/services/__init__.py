"""Services module for MétéoScore business logic.

This module contains service classes that implement core business logic:
- MatchingService: Matches forecasts with observations within time tolerance
"""

from services.matching_service import (
    MatchingService,
    calculate_horizon,
    calculate_time_diff_minutes,
    is_within_tolerance,
)

__all__ = [
    "MatchingService",
    "calculate_horizon",
    "calculate_time_diff_minutes",
    "is_within_tolerance",
]
