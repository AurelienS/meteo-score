"""Storage service for persisting collected weather data.

This module provides functions for saving forecast and observation data
collected by the schedulers to the database.

All operations use upsert (INSERT ... ON CONFLICT DO NOTHING) for idempotency.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.data_models import ForecastData, ObservationData
from core.database import get_async_session_factory
from core.models import ExecutionLog, Forecast, Model, Observation

logger = logging.getLogger(__name__)


async def get_model_id_by_name(db: AsyncSession, name: str) -> int | None:
    """Look up model ID by name.

    Args:
        db: Database session.
        name: Model name (e.g., 'AROME', 'Meteo-Parapente').

    Returns:
        Model ID or None if not found.
    """
    result = await db.execute(select(Model.id).where(Model.name == name))
    row = result.scalar_one_or_none()
    return row


async def save_forecasts(
    forecasts: list[ForecastData],
    source_name: str,
) -> tuple[int, int]:
    """Save forecast data to database.

    Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.

    Args:
        forecasts: List of ForecastData to save.
        source_name: Name of the source (for logging).

    Returns:
        Tuple of (total_attempted, actually_inserted).
    """
    if not forecasts:
        return 0, 0

    async_session = get_async_session_factory()
    inserted = 0

    async with async_session() as db:
        try:
            for f in forecasts:
                # Build insert statement with ON CONFLICT DO NOTHING
                stmt = pg_insert(Forecast).values(
                    site_id=f.site_id,
                    model_id=f.model_id,
                    parameter_id=f.parameter_id,
                    forecast_run=f.forecast_run,
                    valid_time=f.valid_time,
                    value=f.value,
                ).on_conflict_do_nothing(
                    constraint="uq_forecasts_unique"
                )

                result = await db.execute(stmt)
                if result.rowcount > 0:
                    inserted += 1

            await db.commit()
            logger.info(
                f"[{source_name}] Saved {inserted}/{len(forecasts)} forecasts "
                f"({len(forecasts) - inserted} duplicates skipped)"
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"[{source_name}] Failed to save forecasts: {e}")
            raise

    return len(forecasts), inserted


async def save_observations(
    observations: list[ObservationData],
    source_name: str,
) -> tuple[int, int]:
    """Save observation data to database.

    Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.

    Args:
        observations: List of ObservationData to save.
        source_name: Name of the source (for logging).

    Returns:
        Tuple of (total_attempted, actually_inserted).
    """
    if not observations:
        return 0, 0

    async_session = get_async_session_factory()
    inserted = 0

    async with async_session() as db:
        try:
            for o in observations:
                # Build insert statement with ON CONFLICT DO NOTHING
                stmt = pg_insert(Observation).values(
                    site_id=o.site_id,
                    parameter_id=o.parameter_id,
                    observation_time=o.observation_time,
                    value=o.value,
                    source=source_name,
                ).on_conflict_do_nothing(
                    constraint="uq_observations_unique"
                )

                result = await db.execute(stmt)
                if result.rowcount > 0:
                    inserted += 1

            await db.commit()
            logger.info(
                f"[{source_name}] Saved {inserted}/{len(observations)} observations "
                f"({len(observations) - inserted} duplicates skipped)"
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"[{source_name}] Failed to save observations: {e}")
            raise

    return len(observations), inserted


async def save_execution_log(
    job_id: str,
    start_time: datetime,
    end_time: datetime,
    status: str,
    records_collected: int,
    records_persisted: int,
    errors: list[str] | None = None,
) -> None:
    """Save execution log to database.

    Args:
        job_id: Job identifier (e.g., "collect_forecasts").
        start_time: When job started.
        end_time: When job ended.
        status: Job status ("success", "partial", "failed").
        records_collected: Number of records collected.
        records_persisted: Number of records actually saved.
        errors: Optional list of error messages.
    """
    async_session = get_async_session_factory()

    async with async_session() as db:
        try:
            duration = (end_time - start_time).total_seconds()

            log = ExecutionLog(
                job_id=job_id,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration,
                status=status,
                records_collected=records_collected,
                records_persisted=records_persisted,
                errors=errors,
            )
            db.add(log)
            await db.commit()

            logger.info(f"Saved execution log for {job_id}: {status}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to save execution log: {e}")
            # Don't raise - execution log failure shouldn't break collection


async def get_execution_history(
    job_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get execution history for a job from database.

    Args:
        job_id: Job identifier.
        limit: Maximum records to return.

    Returns:
        List of execution records, most recent first.
    """
    async_session = get_async_session_factory()

    async with async_session() as db:
        result = await db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.job_id == job_id)
            .order_by(ExecutionLog.start_time.desc())
            .limit(limit)
        )
        logs = result.scalars().all()

        return [
            {
                "start_time": log.start_time.isoformat(),
                "end_time": log.end_time.isoformat(),
                "duration_seconds": log.duration_seconds,
                "status": log.status,
                "records_collected": log.records_collected,
                "records_persisted": log.records_persisted,
                "errors": log.errors,
            }
            for log in logs
        ]


async def get_data_stats(days: int | None = None) -> dict[str, Any]:
    """Get total counts of all data in database.

    Args:
        days: Optional number of days to filter by. If None, returns all-time counts.

    Returns:
        Dict with total counts for forecasts, observations, deviations, pairs.
    """
    async_session = get_async_session_factory()

    async with async_session() as db:
        if days is None:
            # All-time counts
            result = await db.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM forecasts) as total_forecasts,
                    (SELECT COUNT(*) FROM observations) as total_observations,
                    (SELECT COUNT(*) FROM deviations) as total_deviations,
                    (SELECT COUNT(*) FROM forecast_observation_pairs) as total_pairs,
                    (SELECT COUNT(*) FROM sites) as total_sites
            """))
        else:
            # Counts for the last N days
            result = await db.execute(text("""
                SELECT
                    (SELECT COUNT(*) FROM forecasts WHERE created_at >= NOW() - INTERVAL :days_interval) as total_forecasts,
                    (SELECT COUNT(*) FROM observations WHERE created_at >= NOW() - INTERVAL :days_interval) as total_observations,
                    (SELECT COUNT(*) FROM deviations WHERE created_at >= NOW() - INTERVAL :days_interval) as total_deviations,
                    (SELECT COUNT(*) FROM forecast_observation_pairs WHERE created_at >= NOW() - INTERVAL :days_interval) as total_pairs,
                    (SELECT COUNT(*) FROM sites) as total_sites
            """), {"days_interval": f"{days} days"})

        row = result.fetchone()

        return {
            "total_forecasts": row[0] if row else 0,
            "total_observations": row[1] if row else 0,
            "total_deviations": row[2] if row else 0,
            "total_pairs": row[3] if row else 0,
            "total_sites": row[4] if row else 0,
        }


async def get_recent_data_preview(limit: int = 5) -> dict[str, Any]:
    """Get preview of recently collected data.

    Args:
        limit: Number of records per category.

    Returns:
        Dict with recent forecasts and observations grouped by source.
    """
    async_session = get_async_session_factory()

    async with async_session() as db:
        # Recent forecasts grouped by model
        forecast_result = await db.execute(
            select(Forecast)
            .order_by(Forecast.created_at.desc())
            .limit(limit * 3)  # Get more to have enough per model
        )
        forecasts = forecast_result.scalars().all()

        forecasts_by_model: dict[str, list[dict]] = {}
        for f in forecasts:
            model_name = f.model.name if f.model else f"Model {f.model_id}"
            if model_name not in forecasts_by_model:
                forecasts_by_model[model_name] = []
            if len(forecasts_by_model[model_name]) < limit:
                forecasts_by_model[model_name].append({
                    "id": f.id,
                    "site": f.site.name if f.site else f"Site {f.site_id}",
                    "parameter": f.parameter.name if f.parameter else f"Param {f.parameter_id}",
                    "valid_time": f.valid_time.isoformat(),
                    "value": float(f.value),
                    "created_at": f.created_at.isoformat(),
                })

        # Recent observations grouped by source
        observation_result = await db.execute(
            select(Observation)
            .order_by(Observation.created_at.desc())
            .limit(limit * 3)
        )
        observations = observation_result.scalars().all()

        observations_by_source: dict[str, list[dict]] = {}
        for o in observations:
            source = o.source or "Unknown"
            if source not in observations_by_source:
                observations_by_source[source] = []
            if len(observations_by_source[source]) < limit:
                observations_by_source[source].append({
                    "id": o.id,
                    "site": o.site.name if o.site else f"Site {o.site_id}",
                    "parameter": o.parameter.name if o.parameter else f"Param {o.parameter_id}",
                    "observation_time": o.observation_time.isoformat(),
                    "value": float(o.value),
                    "created_at": o.created_at.isoformat(),
                })

        return {
            "forecasts": forecasts_by_model,
            "observations": observations_by_source,
        }
