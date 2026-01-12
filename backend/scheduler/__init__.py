"""Scheduler module for automated weather data collection.

Exports:
    - SchedulerConfig: Configuration for scheduler jobs
    - get_scheduler: Get the AsyncIOScheduler singleton
    - start_scheduler: Start the scheduler
    - stop_scheduler: Stop the scheduler
    - register_jobs: Register collection jobs
    - collect_all_forecasts: Manually trigger forecast collection
    - collect_all_observations: Manually trigger observation collection
    - get_last_execution: Get last job execution details
"""

from scheduler.config import SchedulerConfig, get_scheduler_config, scheduler_config
from scheduler.jobs import (
    collect_all_forecasts,
    collect_all_observations,
    get_all_job_statuses,
    get_last_execution,
    get_site_configs,
)
from scheduler.scheduler import (
    get_scheduler,
    register_jobs,
    reset_scheduler,
    start_scheduler,
    stop_scheduler,
)

__all__ = [
    # Configuration
    "SchedulerConfig",
    "get_scheduler_config",
    "scheduler_config",
    # Scheduler lifecycle
    "get_scheduler",
    "register_jobs",
    "reset_scheduler",
    "start_scheduler",
    "stop_scheduler",
    # Job functions
    "collect_all_forecasts",
    "collect_all_observations",
    "get_site_configs",
    # Status tracking
    "get_last_execution",
    "get_all_job_statuses",
]
