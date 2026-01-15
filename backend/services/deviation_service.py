"""Deviation calculation service for MétéoScore.

This module provides the DeviationService class that calculates deviations
between forecast predictions and actual observations, storing them in the
deviations hypertable.

The deviation formula follows the epic convention:
    deviation = observed_value - forecast_value

Sign convention:
    - Positive deviation: forecast underestimated (observed > forecast)
    - Negative deviation: forecast overestimated (observed < forecast)
"""

import logging
from datetime import datetime, timezone as tz
from decimal import Decimal
from typing import List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import (
    Deviation,
    ForecastObservationPair,
    Parameter,
)

logger = logging.getLogger(__name__)


def _normalize_datetime(dt: datetime) -> datetime:
    """Normalize datetime to naive UTC for database compatibility.

    SQLite strips timezone info, so we need to ensure consistent
    datetime handling across test (SQLite) and production (PostgreSQL).

    Args:
        dt: The datetime to normalize.

    Returns:
        A timezone-naive datetime (assumed UTC).
    """
    if dt.tzinfo is not None:
        return dt.astimezone(tz.utc).replace(tzinfo=None)
    return dt


class DeviationService:
    """Service for calculating deviations from forecast-observation pairs.

    Processes matched forecast-observation pairs and creates deviation records
    in the hypertable for time-series analysis.

    Attributes:
        WIND_SPEED_OUTLIER_THRESHOLD: Max normal wind speed deviation (km/h).
        TEMPERATURE_OUTLIER_THRESHOLD: Max normal temperature deviation (°C).
        BATCH_SIZE: Number of deviations to process per batch.
    """

    WIND_SPEED_OUTLIER_THRESHOLD: Decimal = Decimal("50.0")
    TEMPERATURE_OUTLIER_THRESHOLD: Decimal = Decimal("15.0")
    BATCH_SIZE: int = 1000

    def calculate_deviation(
        self,
        observed_value: Decimal,
        forecast_value: Decimal,
    ) -> Decimal:
        """Calculate simple deviation: observed - forecast.

        Args:
            observed_value: The actual observed value.
            forecast_value: The forecasted value.

        Returns:
            The deviation (observed - forecast).
        """
        return observed_value - forecast_value

    def calculate_wind_direction_deviation(
        self,
        forecast_deg: Decimal,
        observed_deg: Decimal,
    ) -> Decimal:
        """Calculate shortest angular distance for wind direction.

        Wind direction is circular (0-360°), so we need to find the
        shortest path between two angles, which may cross the 0°/360°
        boundary.

        Args:
            forecast_deg: Forecasted wind direction in degrees.
            observed_deg: Observed wind direction in degrees.

        Returns:
            Angular distance in range [-180, 180].
        """
        diff = float(observed_deg - forecast_deg)

        # Normalize to [-180, 180]
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360

        return Decimal(str(diff))

    def is_outlier(
        self,
        deviation: Decimal,
        parameter_name: str,
    ) -> bool:
        """Check if deviation exceeds threshold for parameter type.

        Outliers are not rejected, just flagged for monitoring.
        Wind direction is never flagged as it uses angular distance.

        Args:
            deviation: The calculated deviation value.
            parameter_name: Name of the parameter (wind_speed, temperature, etc.).

        Returns:
            True if the deviation is an outlier, False otherwise.
        """
        abs_deviation = abs(deviation)

        if parameter_name == "wind_speed":
            if abs_deviation > self.WIND_SPEED_OUTLIER_THRESHOLD:
                logger.warning(
                    f"Wind speed outlier detected: deviation={deviation} km/h "
                    f"(threshold={self.WIND_SPEED_OUTLIER_THRESHOLD})"
                )
                return True
        elif parameter_name == "temperature":
            if abs_deviation > self.TEMPERATURE_OUTLIER_THRESHOLD:
                logger.warning(
                    f"Temperature outlier detected: deviation={deviation}°C "
                    f"(threshold={self.TEMPERATURE_OUTLIER_THRESHOLD})"
                )
                return True
        elif parameter_name == "wind_direction":
            # Wind direction uses angular distance, max is 180°
            # This is normal, not an outlier
            return False
        elif parameter_name:
            # Unknown parameter type - log for visibility but don't flag as outlier
            logger.debug(
                f"Unknown parameter type '{parameter_name}' - no outlier threshold defined"
            )

        return False

    async def process_pairs(
        self,
        db: AsyncSession,
        site_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """Process forecast-observation pairs and create deviations.

        Queries unprocessed pairs, calculates deviations, and stores them
        in the deviations hypertable. Marks pairs as processed to ensure
        idempotency.

        Args:
            db: Async database session.
            site_id: ID of the site to process pairs for.
            start_date: Start of the date range.
            end_date: End of the date range.

        Returns:
            Count of deviations created.

        Raises:
            ValueError: If site_id <= 0 or start_date >= end_date.
        """
        # Input validation
        if site_id <= 0:
            raise ValueError(f"site_id must be positive, got {site_id}")
        if start_date >= end_date:
            raise ValueError(
                f"start_date must be before end_date: {start_date} >= {end_date}"
            )

        # Query unprocessed pairs in date range
        pairs_query = (
            select(ForecastObservationPair)
            .where(
                and_(
                    ForecastObservationPair.site_id == site_id,
                    ForecastObservationPair.valid_time >= start_date,
                    ForecastObservationPair.valid_time <= end_date,
                    ForecastObservationPair.processed_at.is_(None),
                )
            )
            .order_by(ForecastObservationPair.valid_time)
        )

        result = await db.execute(pairs_query)
        pairs = result.scalars().all()

        logger.debug(
            f"Found {len(pairs)} unprocessed pairs for site {site_id} "
            f"between {start_date} and {end_date}"
        )

        if not pairs:
            return 0

        # Get parameter names for outlier detection
        param_ids = {p.parameter_id for p in pairs}
        param_query = select(Parameter).where(Parameter.id.in_(param_ids))
        result = await db.execute(param_query)
        parameters = {p.id: p.name for p in result.scalars().all()}

        # Process pairs and create deviations
        created_count = 0
        deviations_to_create: List[Deviation] = []
        now = datetime.now(tz.utc)

        for pair in pairs:
            param_name = parameters.get(pair.parameter_id, "")

            # Calculate deviation based on parameter type
            if param_name == "wind_direction":
                deviation_value = self.calculate_wind_direction_deviation(
                    forecast_deg=pair.forecast_value,
                    observed_deg=pair.observed_value,
                )
            else:
                deviation_value = self.calculate_deviation(
                    observed_value=pair.observed_value,
                    forecast_value=pair.forecast_value,
                )

            # Check for outliers (log warning but don't skip)
            self.is_outlier(deviation_value, param_name)

            # Create deviation record
            # Normalize timestamp for SQLite compatibility in tests
            deviation = Deviation(
                timestamp=_normalize_datetime(pair.valid_time),
                site_id=pair.site_id,
                model_id=pair.model_id,
                parameter_id=pair.parameter_id,
                horizon=pair.horizon,
                forecast_value=pair.forecast_value,
                observed_value=pair.observed_value,
                deviation=deviation_value,
            )
            deviations_to_create.append(deviation)

            # Mark pair as processed
            pair.processed_at = now

            # Batch processing
            if len(deviations_to_create) >= self.BATCH_SIZE:
                for d in deviations_to_create:
                    db.add(d)
                await db.flush()
                created_count += len(deviations_to_create)
                deviations_to_create = []

        # Flush remaining deviations
        if deviations_to_create:
            for d in deviations_to_create:
                db.add(d)
            await db.flush()
            created_count += len(deviations_to_create)

        # Commit all changes
        await db.commit()

        logger.debug(f"Created {created_count} deviations for site {site_id}")

        return created_count
