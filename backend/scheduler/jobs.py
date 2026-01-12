"""Scheduled job functions for data collection.

This module defines the async job functions that are executed by the scheduler
to collect forecast and observation data from various sources.

Usage:
    # Jobs are registered via scheduler.register_jobs()
    # But can also be called manually for testing:
    result = await collect_all_forecasts()
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from collectors import (
    AROMECollector,
    FFVLCollector,
    MeteoParapenteCollector,
    ROMMaCollector,
)
from core.data_models import ForecastData, ObservationData

logger = logging.getLogger(__name__)

# Job execution tracking
_job_executions: dict[str, dict[str, Any]] = {}


def get_last_execution(job_id: str) -> dict[str, Any] | None:
    """Get last execution details for a job.

    Args:
        job_id: The job identifier (e.g., "collect_forecasts").

    Returns:
        Dict with start_time, end_time, status, records_collected, or None.
    """
    return _job_executions.get(job_id)


def get_site_configs() -> list[dict[str, Any]]:
    """Get site configurations for collection.

    Returns configured sites with their IDs and coordinates.
    In MVP, this returns hardcoded sites. Future versions will
    load from database.

    Returns:
        List of site configuration dicts.
    """
    # TODO: Load from database in future
    return [
        {
            "site_id": 1,
            "name": "Passy Plaine Joux",
            "latitude": 45.9167,
            "longitude": 6.7,
            "romma_station_id": "PASSY",
            "ffvl_beacon_id": "123",
        },
        {
            "site_id": 2,
            "name": "Semnoz",
            "latitude": 45.8167,
            "longitude": 6.0833,
            "romma_station_id": "SEMNOZ",
            "ffvl_beacon_id": "456",
        },
    ]


async def collect_all_forecasts() -> list[ForecastData]:
    """Collect forecasts from all configured sources.

    Runs MeteoParapente and AROME collectors for all configured sites.
    Errors from individual collectors are logged but don't stop
    collection from other sources.

    Returns:
        Combined list of ForecastData from all sources.
    """
    job_id = "collect_forecasts"
    start_time = datetime.now(timezone.utc)
    all_data: list[ForecastData] = []
    status = "success"

    logger.info(f"Starting forecast collection at {start_time.isoformat()}")

    sites = get_site_configs()

    # Collect from MeteoParapente
    try:
        mp_collector = MeteoParapenteCollector()
        for site in sites:
            try:
                forecast_time = datetime.now(timezone.utc)
                data = await mp_collector.collect_forecast(
                    site_id=site["site_id"],
                    forecast_time=forecast_time,
                )
                all_data.extend(data)
                logger.info(
                    f"MeteoParapente: Collected {len(data)} records for {site['name']}"
                )
            except Exception as e:
                logger.error(
                    f"MeteoParapente collection failed for {site['name']}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                status = "partial"
    except Exception as e:
        logger.error(f"MeteoParapente collector initialization failed: {e}")
        status = "partial"

    # Collect from AROME
    try:
        arome_collector = AROMECollector()
        for site in sites:
            try:
                forecast_time = datetime.now(timezone.utc)
                data = await arome_collector.collect_forecast(
                    site_id=site["site_id"],
                    forecast_time=forecast_time,
                )
                all_data.extend(data)
                logger.info(f"AROME: Collected {len(data)} records for {site['name']}")
            except Exception as e:
                logger.error(
                    f"AROME collection failed for {site['name']}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                status = "partial"
    except Exception as e:
        logger.error(f"AROME collector initialization failed: {e}")
        status = "partial"

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Track execution
    _job_executions[job_id] = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "status": status,
        "records_collected": len(all_data),
    }

    logger.info(
        f"Forecast collection complete: {len(all_data)} records in {duration:.2f}s "
        f"(status: {status})"
    )

    return all_data


async def collect_all_observations() -> list[ObservationData]:
    """Collect observations from all configured sources.

    Runs ROMMA and FFVL collectors for all configured sites.
    Errors from individual collectors are logged but don't stop
    collection from other sources.

    Returns:
        Combined list of ObservationData from all sources.
    """
    job_id = "collect_observations"
    start_time = datetime.now(timezone.utc)
    all_data: list[ObservationData] = []
    status = "success"

    logger.info(f"Starting observation collection at {start_time.isoformat()}")

    sites = get_site_configs()

    # Collect from ROMMA
    try:
        romma_collector = ROMMaCollector()
        for site in sites:
            try:
                observation_time = datetime.now(timezone.utc)
                data = await romma_collector.collect_observation(
                    site_id=site["site_id"],
                    observation_time=observation_time,
                )
                all_data.extend(data)
                logger.info(f"ROMMA: Collected {len(data)} records for {site['name']}")
            except Exception as e:
                logger.error(
                    f"ROMMA collection failed for {site['name']}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                status = "partial"
    except Exception as e:
        logger.error(f"ROMMA collector initialization failed: {e}")
        status = "partial"

    # Collect from FFVL
    try:
        ffvl_collector = FFVLCollector()
        for site in sites:
            try:
                observation_time = datetime.now(timezone.utc)
                data = await ffvl_collector.collect_observation(
                    site_id=site["site_id"],
                    observation_time=observation_time,
                )
                all_data.extend(data)
                logger.info(f"FFVL: Collected {len(data)} records for {site['name']}")
            except Exception as e:
                logger.error(
                    f"FFVL collection failed for {site['name']}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                status = "partial"
    except Exception as e:
        logger.error(f"FFVL collector initialization failed: {e}")
        status = "partial"

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Track execution
    _job_executions[job_id] = {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "status": status,
        "records_collected": len(all_data),
    }

    logger.info(
        f"Observation collection complete: {len(all_data)} records in {duration:.2f}s "
        f"(status: {status})"
    )

    return all_data


def get_all_job_statuses() -> dict[str, dict[str, Any]]:
    """Get execution status for all jobs.

    Returns:
        Dict mapping job_id to last execution details.
    """
    return _job_executions.copy()
