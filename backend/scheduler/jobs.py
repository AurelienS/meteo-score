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
from services.storage_service import (
    get_execution_history as db_get_execution_history,
)
from services.storage_service import (
    save_execution_log,
    save_forecasts,
    save_observations,
)

logger = logging.getLogger(__name__)


def get_last_execution(job_id: str) -> dict[str, Any] | None:
    """Get last execution details for a job from database.

    Args:
        job_id: The job identifier (e.g., "collect_forecasts").

    Returns:
        Dict with start_time, end_time, status, records_collected, or None.
    """
    import asyncio
    try:
        history = asyncio.get_event_loop().run_until_complete(
            db_get_execution_history(job_id, limit=1)
        )
        return history[0] if history else None
    except RuntimeError:
        # No event loop, return None
        return None


async def get_execution_history_async(job_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get execution history for a job from database (async version).

    Args:
        job_id: The job identifier (e.g., "collect_forecasts").
        limit: Maximum number of records to return (default 10).

    Returns:
        List of execution records, most recent first.
    """
    return await db_get_execution_history(job_id, limit=limit)


def get_execution_history(job_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Get execution history for a job from database.

    Args:
        job_id: The job identifier (e.g., "collect_forecasts").
        limit: Maximum number of records to return (default 10).

    Returns:
        List of execution records, most recent first.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use run_until_complete in running loop
            # Return empty for now, use async version instead
            return []
        return loop.run_until_complete(db_get_execution_history(job_id, limit=limit))
    except RuntimeError:
        return []


async def get_site_configs_async() -> list[dict[str, Any]]:
    """Get site configurations from database for collection.

    Returns configured sites with their IDs, coordinates, and beacon IDs.
    Loads from database to support dynamic site management.

    IMPORTANT: beacon IDs must be integers matching the actual beacon systems:
    - ROMMA: https://www.romma.fr/station_24.php?id=XX
    - FFVL: https://www.balisemeteo.com/balise.php?idBalise=XX

    Returns:
        List of site configuration dicts with keys:
        - site_id, name, latitude, longitude
        - romma_beacon_id, romma_beacon_id_backup
        - ffvl_beacon_id, ffvl_beacon_id_backup
    """
    from sqlalchemy import select

    from core.database import get_async_session_factory
    from core.models import Site

    async_session = get_async_session_factory()

    async with async_session() as db:
        result = await db.execute(select(Site))
        sites = result.scalars().all()

        return [
            {
                "site_id": site.id,
                "name": site.name,
                "latitude": float(site.latitude),
                "longitude": float(site.longitude),
                "romma_beacon_id": site.romma_beacon_id,
                "romma_beacon_id_backup": site.romma_beacon_id_backup,
                "ffvl_beacon_id": site.ffvl_beacon_id,
                "ffvl_beacon_id_backup": site.ffvl_beacon_id_backup,
            }
            for site in sites
        ]


def get_site_configs() -> list[dict[str, Any]]:
    """Synchronous wrapper for get_site_configs_async.

    For backwards compatibility with sync code paths.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use run_until_complete in running loop
            # Create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, get_site_configs_async())
                return future.result()
        return loop.run_until_complete(get_site_configs_async())
    except RuntimeError:
        return asyncio.run(get_site_configs_async())


async def collect_all_forecasts() -> dict[str, Any]:
    """Collect forecasts from all configured sources and persist to database.

    Runs MeteoParapente and AROME collectors for all configured sites.
    Errors from individual collectors are logged but don't stop
    collection from other sources.

    Returns:
        Dict with collection results: collected, persisted, status, errors.
    """
    job_id = "collect_forecasts"
    start_time = datetime.now(timezone.utc)
    all_data: list[ForecastData] = []
    status = "success"
    errors: list[str] = []
    total_persisted = 0

    logger.info(f"Starting forecast collection at {start_time.isoformat()}")

    sites = await get_site_configs_async()

    # Collect from MeteoParapente
    try:
        mp_collector = MeteoParapenteCollector()
        for site in sites:
            try:
                forecast_run = datetime.now(timezone.utc)
                data = await mp_collector.collect_forecast(
                    site_id=site["site_id"],
                    forecast_run=forecast_run,
                    latitude=site["latitude"],
                    longitude=site["longitude"],
                )
                if data:
                    # Save immediately after collection
                    _, persisted = await save_forecasts(data, "Meteo-Parapente")
                    total_persisted += persisted
                    all_data.extend(data)
                logger.info(
                    f"MeteoParapente: Collected {len(data)} records for {site['name']}"
                )
            except Exception as e:
                error_msg = f"MeteoParapente collection failed for {site['name']}: {e}"
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                errors.append(error_msg)
                status = "partial"
    except Exception as e:
        error_msg = f"MeteoParapente collector initialization failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        status = "partial"

    # Collect from AROME
    try:
        arome_collector = AROMECollector()
        for site in sites:
            try:
                forecast_run = datetime.now(timezone.utc)
                data = await arome_collector.collect_forecast(
                    site_id=site["site_id"],
                    forecast_run=forecast_run,
                    latitude=site["latitude"],
                    longitude=site["longitude"],
                )
                if data:
                    # Save immediately after collection
                    _, persisted = await save_forecasts(data, "AROME")
                    total_persisted += persisted
                    all_data.extend(data)
                logger.info(f"AROME: Collected {len(data)} records for {site['name']}")
            except Exception as e:
                error_msg = f"AROME collection failed for {site['name']}: {e}"
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                errors.append(error_msg)
                status = "partial"
    except Exception as e:
        error_msg = f"AROME collector initialization failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        status = "partial"

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Save execution log to database
    await save_execution_log(
        job_id=job_id,
        start_time=start_time,
        end_time=end_time,
        status=status,
        records_collected=len(all_data),
        records_persisted=total_persisted,
        errors=errors if errors else None,
    )

    logger.info(
        f"Forecast collection complete: {len(all_data)} collected, "
        f"{total_persisted} persisted in {duration:.2f}s (status: {status})"
    )

    return {
        "status": status,
        "records_collected": len(all_data),
        "records_persisted": total_persisted,
        "duration_seconds": duration,
        "errors": errors if errors else None,
    }


async def collect_all_observations() -> dict[str, Any]:
    """Collect observations from all configured sources and persist to database.

    Runs ROMMA and FFVL collectors for all configured sites.
    Errors from individual collectors are logged but don't stop
    collection from other sources.

    Returns:
        Dict with collection results: collected, persisted, status, errors.
    """
    job_id = "collect_observations"
    start_time = datetime.now(timezone.utc)
    all_data: list[ObservationData] = []
    status = "success"
    errors: list[str] = []
    total_persisted = 0

    logger.info(f"Starting observation collection at {start_time.isoformat()}")

    sites = await get_site_configs_async()

    # Collect from ROMMA (with backup beacon fallback)
    try:
        for site in sites:
            primary_beacon_id = site.get("romma_beacon_id")
            backup_beacon_id = site.get("romma_beacon_id_backup")
            collected = False

            # Try primary beacon first
            if primary_beacon_id:
                try:
                    romma_collector = ROMMaCollector(beacon_id=primary_beacon_id)
                    observation_time = datetime.now(timezone.utc)
                    data = await romma_collector.collect_observation(
                        site_id=site["site_id"],
                        observation_time=observation_time,
                        beacon_id=primary_beacon_id,
                    )
                    if data:
                        _, persisted = await save_observations(data, "ROMMA")
                        total_persisted += persisted
                        all_data.extend(data)
                        collected = True
                    logger.info(
                        f"ROMMA: Collected {len(data)} records for {site['name']} "
                        f"(primary beacon_id={primary_beacon_id})"
                    )
                except Exception as e:
                    error_msg = f"ROMMA primary beacon failed for {site['name']}: {e}"
                    logger.warning(error_msg)
                    if backup_beacon_id:
                        logger.info(f"Trying ROMMA backup beacon {backup_beacon_id}")
                    else:
                        logger.error(f"{error_msg}\n{traceback.format_exc()}")
                        errors.append(error_msg)
                        status = "partial"

            # Try backup beacon if primary failed or not configured
            if not collected and backup_beacon_id:
                try:
                    romma_collector = ROMMaCollector(beacon_id=backup_beacon_id)
                    observation_time = datetime.now(timezone.utc)
                    data = await romma_collector.collect_observation(
                        site_id=site["site_id"],
                        observation_time=observation_time,
                        beacon_id=backup_beacon_id,
                    )
                    if data:
                        _, persisted = await save_observations(data, "ROMMA")
                        total_persisted += persisted
                        all_data.extend(data)
                    logger.info(
                        f"ROMMA: Collected {len(data)} records for {site['name']} "
                        f"(backup beacon_id={backup_beacon_id})"
                    )
                except Exception as e:
                    error_msg = f"ROMMA backup beacon also failed for {site['name']}: {e}"
                    logger.error(f"{error_msg}\n{traceback.format_exc()}")
                    errors.append(error_msg)
                    status = "partial"

            # No beacons configured for this site
            if not primary_beacon_id and not backup_beacon_id:
                logger.warning(f"No ROMMA beacons configured for {site['name']}")
    except Exception as e:
        error_msg = f"ROMMA collector initialization failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        status = "partial"

    # Collect from FFVL (with backup beacon fallback)
    try:
        for site in sites:
            primary_beacon_id = site.get("ffvl_beacon_id")
            backup_beacon_id = site.get("ffvl_beacon_id_backup")
            collected = False

            # Try primary beacon first
            if primary_beacon_id:
                try:
                    ffvl_collector = FFVLCollector(beacon_id=primary_beacon_id)
                    observation_time = datetime.now(timezone.utc)
                    data = await ffvl_collector.collect_observation(
                        site_id=site["site_id"],
                        observation_time=observation_time,
                        beacon_id=primary_beacon_id,
                    )
                    if data:
                        _, persisted = await save_observations(data, "FFVL")
                        total_persisted += persisted
                        all_data.extend(data)
                        collected = True
                    logger.info(
                        f"FFVL: Collected {len(data)} records for {site['name']} "
                        f"(primary beacon_id={primary_beacon_id})"
                    )
                except Exception as e:
                    error_msg = f"FFVL primary beacon failed for {site['name']}: {e}"
                    logger.warning(error_msg)
                    if backup_beacon_id:
                        logger.info(f"Trying FFVL backup beacon {backup_beacon_id}")
                    else:
                        logger.error(f"{error_msg}\n{traceback.format_exc()}")
                        errors.append(error_msg)
                        status = "partial"

            # Try backup beacon if primary failed or not configured
            if not collected and backup_beacon_id:
                try:
                    ffvl_collector = FFVLCollector(beacon_id=backup_beacon_id)
                    observation_time = datetime.now(timezone.utc)
                    data = await ffvl_collector.collect_observation(
                        site_id=site["site_id"],
                        observation_time=observation_time,
                        beacon_id=backup_beacon_id,
                    )
                    if data:
                        _, persisted = await save_observations(data, "FFVL")
                        total_persisted += persisted
                        all_data.extend(data)
                    logger.info(
                        f"FFVL: Collected {len(data)} records for {site['name']} "
                        f"(backup beacon_id={backup_beacon_id})"
                    )
                except Exception as e:
                    error_msg = f"FFVL backup beacon also failed for {site['name']}: {e}"
                    logger.error(f"{error_msg}\n{traceback.format_exc()}")
                    errors.append(error_msg)
                    status = "partial"

            # No beacons configured for this site
            if not primary_beacon_id and not backup_beacon_id:
                logger.warning(f"No FFVL beacons configured for {site['name']}")
    except Exception as e:
        error_msg = f"FFVL collector initialization failed: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        status = "partial"

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    # Save execution log to database
    await save_execution_log(
        job_id=job_id,
        start_time=start_time,
        end_time=end_time,
        status=status,
        records_collected=len(all_data),
        records_persisted=total_persisted,
        errors=errors if errors else None,
    )

    logger.info(
        f"Observation collection complete: {len(all_data)} collected, "
        f"{total_persisted} persisted in {duration:.2f}s (status: {status})"
    )

    return {
        "status": status,
        "records_collected": len(all_data),
        "records_persisted": total_persisted,
        "duration_seconds": duration,
        "errors": errors if errors else None,
    }


async def get_all_job_statuses() -> dict[str, list[dict[str, Any]]]:
    """Get execution history for all jobs from database.

    Returns:
        Dict mapping job_id to list of execution records (most recent first).
    """
    forecast_history = await db_get_execution_history("collect_forecasts", limit=10)
    observation_history = await db_get_execution_history("collect_observations", limit=10)

    return {
        "collect_forecasts": forecast_history,
        "collect_observations": observation_history,
    }
