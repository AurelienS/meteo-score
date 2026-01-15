"""Forecast-observation matching service for MétéoScore.

This module provides the MatchingService class that matches weather forecasts
with actual observations within a configurable time tolerance window.

The matching pipeline:
1. Query forecasts in date range
2. For each forecast, find observations within ±TIME_TOLERANCE_MINUTES
3. If multiple observations match, select the closest to valid_time
4. Create ForecastObservationPair records with horizon calculation
5. Handle idempotency via UNIQUE constraint
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    Forecast,
    ForecastObservationPair,
    Observation,
)

logger = logging.getLogger(__name__)


def _normalize_datetime(dt: datetime) -> datetime:
    """Normalize datetime to naive UTC for comparison.

    SQLite strips timezone info, so we need to handle mixed
    timezone-aware and naive datetimes consistently.

    Args:
        dt: The datetime to normalize.

    Returns:
        A timezone-naive datetime (assumed UTC).
    """
    if dt.tzinfo is not None:
        # Convert to UTC and strip timezone
        from datetime import timezone as tz

        return dt.astimezone(tz.utc).replace(tzinfo=None)
    return dt


def is_within_tolerance(
    forecast_valid_time: datetime,
    observation_time: datetime,
    tolerance_minutes: int,
) -> bool:
    """Check if observation is within tolerance of forecast valid_time.

    Args:
        forecast_valid_time: The forecast's valid time.
        observation_time: The observation's timestamp.
        tolerance_minutes: Acceptable time difference in minutes.

    Returns:
        True if the observation is within tolerance, False otherwise.
    """
    # Normalize both datetimes to handle SQLite timezone stripping
    norm_forecast = _normalize_datetime(forecast_valid_time)
    norm_observation = _normalize_datetime(observation_time)

    diff = abs((norm_observation - norm_forecast).total_seconds())
    return diff <= tolerance_minutes * 60


def calculate_horizon(forecast_run: datetime, valid_time: datetime) -> int:
    """Calculate forecast horizon in hours.

    Args:
        forecast_run: When the forecast was generated.
        valid_time: When the forecast is valid for.

    Returns:
        The horizon in hours (integer).
    """
    # Normalize both datetimes to handle SQLite timezone stripping
    norm_run = _normalize_datetime(forecast_run)
    norm_valid = _normalize_datetime(valid_time)

    diff = norm_valid - norm_run
    return int(diff.total_seconds() / 3600)


def calculate_time_diff_minutes(
    forecast_valid_time: datetime,
    observation_time: datetime,
) -> int:
    """Calculate time difference in minutes between forecast and observation.

    Args:
        forecast_valid_time: The forecast's valid time.
        observation_time: The observation's timestamp.

    Returns:
        The absolute time difference in minutes.
    """
    # Normalize both datetimes to handle SQLite timezone stripping
    norm_forecast = _normalize_datetime(forecast_valid_time)
    norm_observation = _normalize_datetime(observation_time)

    diff = abs((norm_observation - norm_forecast).total_seconds())
    return int(diff / 60)


class MatchingService:
    """Service for matching forecasts with observations.

    Matches weather forecasts with actual observations within a configurable
    time tolerance window. Creates ForecastObservationPair records for
    downstream deviation calculation.

    Attributes:
        TIME_TOLERANCE_MINUTES: Maximum time difference for matching (default: 30).
        BATCH_SIZE: Number of pairs to process in each batch (default: 1000).
    """

    TIME_TOLERANCE_MINUTES: int = 30
    BATCH_SIZE: int = 1000

    async def match_forecasts_to_observations(
        self,
        db: AsyncSession,
        site_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[ForecastObservationPair]:
        """Match forecasts with observations within time tolerance.

        For each forecast in the date range:
        1. Find observations within ±TIME_TOLERANCE_MINUTES of valid_time
        2. If multiple observations match, select the closest
        3. Create a ForecastObservationPair record

        Args:
            db: Async database session.
            site_id: ID of the site to match forecasts for.
            start_date: Start of the date range.
            end_date: End of the date range.

        Returns:
            List of created ForecastObservationPair records.

        Raises:
            ValueError: If start_date >= end_date or site_id <= 0.
        """
        # Input validation (M4 fix)
        if site_id <= 0:
            raise ValueError(f"site_id must be positive, got {site_id}")
        if start_date >= end_date:
            raise ValueError(
                f"start_date must be before end_date: {start_date} >= {end_date}"
            )

        created_pairs: List[ForecastObservationPair] = []

        # Query forecasts in date range for the site
        forecast_query = (
            select(Forecast)
            .where(
                and_(
                    Forecast.site_id == site_id,
                    Forecast.valid_time >= start_date,
                    Forecast.valid_time <= end_date,
                )
            )
            .order_by(Forecast.valid_time)
        )

        result = await db.execute(forecast_query)
        forecasts = result.scalars().all()

        logger.debug(
            f"Found {len(forecasts)} forecasts for site {site_id} "
            f"between {start_date} and {end_date}"
        )

        # Get tolerance window for observation query
        tolerance_delta = timedelta(minutes=self.TIME_TOLERANCE_MINUTES)

        # Query observations in the extended date range
        obs_start = start_date - tolerance_delta
        obs_end = end_date + tolerance_delta

        observation_query = (
            select(Observation)
            .where(
                and_(
                    Observation.site_id == site_id,
                    Observation.observation_time >= obs_start,
                    Observation.observation_time <= obs_end,
                )
            )
            .order_by(Observation.observation_time)
        )

        result = await db.execute(observation_query)
        observations = result.scalars().all()

        logger.debug(f"Found {len(observations)} observations in range")

        # H1 FIX: Pre-group observations by parameter_id for O(n+m) instead of O(n*m)
        observations_by_param: Dict[int, List[Observation]] = defaultdict(list)
        for obs in observations:
            observations_by_param[obs.parameter_id].append(obs)

        # Get existing pairs to avoid duplicates (check before insert instead of catch)
        existing_pairs_query = select(
            ForecastObservationPair.forecast_id,
            ForecastObservationPair.observation_id,
        ).where(ForecastObservationPair.site_id == site_id)
        result = await db.execute(existing_pairs_query)
        existing_pairs = {(row[0], row[1]) for row in result.fetchall()}

        # Match each forecast with observations
        unmatched_count = 0
        pairs_to_create: List[ForecastObservationPair] = []

        for forecast in forecasts:
            # H1 FIX: Only look at observations for this parameter
            param_observations = observations_by_param.get(forecast.parameter_id, [])

            # Find observations within tolerance
            matching_observations = [
                obs
                for obs in param_observations
                if is_within_tolerance(
                    forecast.valid_time,
                    obs.observation_time,
                    self.TIME_TOLERANCE_MINUTES,
                )
            ]

            if not matching_observations:
                unmatched_count += 1
                logger.debug(
                    f"No matching observation for forecast {forecast.id} "
                    f"(valid_time={forecast.valid_time})"
                )
                continue

            # Select closest observation if multiple matches
            norm_valid = _normalize_datetime(forecast.valid_time)
            closest_obs = min(
                matching_observations,
                key=lambda o: abs(
                    (_normalize_datetime(o.observation_time) - norm_valid).total_seconds()
                ),
            )

            # M2 FIX: Check existence before creating (instead of catching IntegrityError)
            if (forecast.id, closest_obs.id) in existing_pairs:
                logger.debug(
                    f"Pair already exists for forecast {forecast.id}, "
                    f"observation {closest_obs.id}"
                )
                continue

            # Calculate derived values
            horizon = calculate_horizon(forecast.forecast_run, forecast.valid_time)
            time_diff = calculate_time_diff_minutes(
                forecast.valid_time, closest_obs.observation_time
            )

            # Create the pair
            pair = ForecastObservationPair(
                forecast_id=forecast.id,
                observation_id=closest_obs.id,
                site_id=site_id,
                model_id=forecast.model_id,
                parameter_id=forecast.parameter_id,
                forecast_run=forecast.forecast_run,
                valid_time=forecast.valid_time,
                horizon=horizon,
                forecast_value=forecast.value,
                observed_value=closest_obs.value,
                time_diff_minutes=time_diff,
            )

            pairs_to_create.append(pair)

            # M1 FIX: Batch processing - flush every BATCH_SIZE pairs
            if len(pairs_to_create) >= self.BATCH_SIZE:
                for p in pairs_to_create:
                    db.add(p)
                await db.flush()
                created_pairs.extend(pairs_to_create)
                pairs_to_create = []

        # Flush remaining pairs
        if pairs_to_create:
            for p in pairs_to_create:
                db.add(p)
            await db.flush()
            created_pairs.extend(pairs_to_create)

        # Commit all created pairs
        if created_pairs:
            await db.commit()

        logger.debug(
            f"Created {len(created_pairs)} new pairs, "
            f"{unmatched_count} forecasts unmatched"
        )

        return created_pairs
