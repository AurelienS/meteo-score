"""Scheduler instance and lifecycle management.

This module provides the APScheduler instance with lifecycle management
functions for integration with FastAPI's lifespan.

Usage:
    from scheduler.scheduler import start_scheduler, stop_scheduler

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await start_scheduler()
        yield
        await stop_scheduler()
"""

import logging
from functools import lru_cache

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from scheduler.config import get_scheduler_config, scheduler_config

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


def reset_scheduler() -> None:
    """Reset the scheduler singleton for testing.

    This function is primarily for use in tests to ensure
    a fresh scheduler instance between tests.
    """
    global _scheduler
    if _scheduler is not None:
        if _scheduler.running:
            try:
                _scheduler.shutdown(wait=False)
            except RuntimeError:
                # Event loop might be closed, ignore
                pass
        _scheduler = None
    get_scheduler.cache_clear()


@lru_cache
def get_scheduler() -> AsyncIOScheduler:
    """Get or create the scheduler singleton.

    Returns:
        AsyncIOScheduler instance configured for UTC timezone.
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # Combine missed jobs into one
                "max_instances": 1,  # Only one instance per job
                "misfire_grace_time": 1800,  # 30 minute grace period
            },
        )
    return _scheduler


def register_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register collection jobs with the scheduler.

    Adds forecast and observation collection jobs with CronTriggers
    based on configuration.

    Args:
        scheduler: The AsyncIOScheduler instance to register jobs with.
    """
    from scheduler.jobs import collect_all_forecasts, collect_all_observations

    config = get_scheduler_config()

    # Create comma-separated hour string for cron
    forecast_hours = ",".join(str(h) for h in config.forecast_hours)
    observation_hours = ",".join(str(h) for h in config.observation_hours)

    # Register forecast collection job (4x daily by default)
    scheduler.add_job(
        collect_all_forecasts,
        CronTrigger(hour=forecast_hours, minute=0, timezone="UTC"),
        id="collect_forecasts",
        name="Collect Forecasts",
        replace_existing=True,
    )
    logger.info(f"Registered forecast collection job at hours: {forecast_hours} UTC")

    # Register observation collection job (6x daily by default)
    scheduler.add_job(
        collect_all_observations,
        CronTrigger(hour=observation_hours, minute=0, timezone="UTC"),
        id="collect_observations",
        name="Collect Observations",
        replace_existing=True,
    )
    logger.info(f"Registered observation collection job at hours: {observation_hours} UTC")


async def start_scheduler() -> None:
    """Start the scheduler if enabled.

    Registers jobs and starts the scheduler. Does nothing if
    scheduler is disabled via configuration.
    """
    config = get_scheduler_config()

    if not config.enabled:
        logger.info("Scheduler is disabled via configuration")
        return

    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("Scheduler is already running")
        return

    # Register jobs before starting
    register_jobs(scheduler)

    scheduler.start()
    logger.info("Scheduler started successfully")


async def stop_scheduler() -> None:
    """Stop the scheduler gracefully.

    Shuts down the scheduler, waiting for running jobs to complete.
    """
    scheduler = get_scheduler()

    if not scheduler.running:
        logger.info("Scheduler is not running")
        return

    # Use wait=False to avoid blocking the event loop
    # The scheduler will stop immediately, any running jobs will complete
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped successfully")
