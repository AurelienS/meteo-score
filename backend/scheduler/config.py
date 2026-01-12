"""Scheduler configuration for automated data collection.

This module provides configuration for APScheduler job scheduling.
All settings can be overridden via environment variables.

Environment Variables:
    SCHEDULER_FORECAST_HOURS: Comma-separated hours for forecast collection (default: 0,6,12,18)
    SCHEDULER_OBSERVATION_HOURS: Comma-separated hours for observation collection (default: 8,10,12,14,16,18)
    SCHEDULER_ENABLED: Enable/disable scheduler (default: true)
"""

import os
from functools import lru_cache


class SchedulerConfig:
    """Configuration for scheduler jobs.

    Attributes:
        forecast_hours: Hours (UTC) when forecast collection runs.
        observation_hours: Hours (UTC) when observation collection runs.
        enabled: Whether scheduler is enabled.
        timezone: Timezone for scheduling (always UTC).
    """

    def __init__(self) -> None:
        """Initialize scheduler configuration from environment."""
        self.forecast_hours = self._parse_hours(
            os.environ.get("SCHEDULER_FORECAST_HOURS", "0,6,12,18")
        )
        self.observation_hours = self._parse_hours(
            os.environ.get("SCHEDULER_OBSERVATION_HOURS", "8,10,12,14,16,18")
        )
        self.enabled = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"
        self.timezone = "UTC"

    def _parse_hours(self, hours_str: str) -> list[int]:
        """Parse comma-separated hours string to list of integers.

        Args:
            hours_str: Comma-separated hour values (e.g., "0,6,12,18").

        Returns:
            List of hour integers.
        """
        return [int(h.strip()) for h in hours_str.split(",") if h.strip()]


@lru_cache
def get_scheduler_config() -> SchedulerConfig:
    """Get cached scheduler configuration.

    Returns:
        SchedulerConfig instance.
    """
    return SchedulerConfig()


# Convenience export
scheduler_config = get_scheduler_config()
