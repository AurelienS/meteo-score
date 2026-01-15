"""MetricsService for calculating forecast accuracy metrics.

This module provides the MetricsService class for calculating statistical
accuracy metrics (MAE, bias, confidence intervals) from deviation data.

Implements story 3.3: Statistical Metrics Calculator (MAE, Bias).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Tuple

from scipy import stats
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import AccuracyMetric, Deviation

logger = logging.getLogger(__name__)


@dataclass
class AccuracyMetrics:
    """Data class for calculated accuracy metrics."""

    model_id: int
    site_id: int
    parameter_id: int
    horizon: int
    mae: Decimal
    bias: Decimal
    std_dev: Decimal
    sample_size: int
    confidence_level: str  # 'insufficient', 'preliminary', 'validated'
    ci_lower: Optional[Decimal]
    ci_upper: Optional[Decimal]
    min_deviation: Decimal
    max_deviation: Decimal


class MetricsService:
    """Service for calculating forecast accuracy metrics.

    Calculates statistical metrics from deviation data including:
    - MAE (Mean Absolute Error)
    - Bias (systematic error)
    - Standard deviation
    - 95% Confidence intervals
    - Min/max deviation range

    Confidence levels indicate data reliability:
    - 'insufficient': < 30 samples, not statistically reliable
    - 'preliminary': 30-89 samples, trends visible but may change
    - 'validated': >= 90 samples, statistically significant
    """

    PRELIMINARY_THRESHOLD: int = 30  # days of data
    VALIDATED_THRESHOLD: int = 90  # days of data

    async def calculate_accuracy_metrics(
        self,
        db: AsyncSession,
        model_id: int,
        site_id: int,
        parameter_id: int,
        horizon: int,
    ) -> AccuracyMetrics:
        """Calculate MAE, bias, and confidence metrics from deviations.

        Args:
            db: Async database session.
            model_id: ID of the forecast model.
            site_id: ID of the site.
            parameter_id: ID of the parameter.
            horizon: Forecast horizon in hours.

        Returns:
            AccuracyMetrics dataclass with calculated values.

        Raises:
            ValueError: If no deviations found for the combination or invalid inputs.
        """
        # Input validation
        if model_id <= 0:
            raise ValueError("model_id must be positive")
        if site_id <= 0:
            raise ValueError("site_id must be positive")
        if parameter_id <= 0:
            raise ValueError("parameter_id must be positive")
        if horizon < 0:
            raise ValueError("horizon must be non-negative")

        # Query to calculate all metrics using SQL aggregation
        query = (
            select(
                func.avg(func.abs(Deviation.deviation)).label("mae"),
                func.avg(Deviation.deviation).label("bias"),
                func.count().label("sample_size"),
                func.min(Deviation.deviation).label("min_deviation"),
                func.max(Deviation.deviation).label("max_deviation"),
            )
            .where(
                Deviation.model_id == model_id,
                Deviation.site_id == site_id,
                Deviation.parameter_id == parameter_id,
                Deviation.horizon == horizon,
            )
        )

        result = await db.execute(query)
        row = result.one()

        # Check if any deviations were found
        if row.sample_size == 0 or row.mae is None:
            raise ValueError(
                f"No deviations found for model_id={model_id}, site_id={site_id}, "
                f"parameter_id={parameter_id}, horizon={horizon}"
            )

        sample_size = row.sample_size
        mae = Decimal(str(row.mae)).quantize(Decimal("0.0001"))
        bias = Decimal(str(row.bias)).quantize(Decimal("0.0001"))
        min_deviation = Decimal(str(row.min_deviation)).quantize(Decimal("0.0001"))
        max_deviation = Decimal(str(row.max_deviation)).quantize(Decimal("0.0001"))

        # Calculate standard deviation separately (need sample std dev, not population)
        # SQL stddev returns population std dev in SQLite, sample in PostgreSQL
        # For consistency, calculate in Python for small datasets
        std_dev = await self._calculate_std_dev(
            db, model_id, site_id, parameter_id, horizon, float(bias)
        )

        # Calculate confidence interval
        ci_lower_float, ci_upper_float = self.calculate_confidence_interval(
            bias=float(bias),
            std_dev=float(std_dev),
            sample_size=sample_size,
        )

        # Handle CI edge cases
        if std_dev == Decimal("0") or sample_size <= 1:
            ci_lower = bias
            ci_upper = bias
        else:
            ci_lower = Decimal(str(ci_lower_float)).quantize(Decimal("0.0001"))
            ci_upper = Decimal(str(ci_upper_float)).quantize(Decimal("0.0001"))

        # Determine confidence level
        confidence_level = self.determine_confidence_level(sample_size)

        logger.info(
            f"Calculated metrics for model={model_id}, site={site_id}, "
            f"param={parameter_id}, horizon={horizon}: "
            f"MAE={mae}, bias={bias}, n={sample_size}, conf={confidence_level}"
        )

        return AccuracyMetrics(
            model_id=model_id,
            site_id=site_id,
            parameter_id=parameter_id,
            horizon=horizon,
            mae=mae,
            bias=bias,
            std_dev=std_dev,
            sample_size=sample_size,
            confidence_level=confidence_level,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            min_deviation=min_deviation,
            max_deviation=max_deviation,
        )

    async def _calculate_std_dev(
        self,
        db: AsyncSession,
        model_id: int,
        site_id: int,
        parameter_id: int,
        horizon: int,
        mean: float,
    ) -> Decimal:
        """Calculate sample standard deviation.

        Uses Bessel's correction (n-1) for sample standard deviation.
        Returns 0 for single samples or identical values.
        """
        # Get all deviation values
        query = (
            select(Deviation.deviation)
            .where(
                Deviation.model_id == model_id,
                Deviation.site_id == site_id,
                Deviation.parameter_id == parameter_id,
                Deviation.horizon == horizon,
            )
        )
        result = await db.execute(query)
        values = [float(row[0]) for row in result.all()]

        if len(values) <= 1:
            return Decimal("0")

        # Calculate sample variance (Bessel's correction)
        squared_diffs = [(v - mean) ** 2 for v in values]
        variance = sum(squared_diffs) / (len(values) - 1)

        if variance <= 0:
            return Decimal("0")

        std_dev = variance ** 0.5
        return Decimal(str(std_dev)).quantize(Decimal("0.0001"))

    def determine_confidence_level(self, sample_size: int) -> str:
        """Determine data confidence based on sample size.

        Args:
            sample_size: Number of samples in the calculation.

        Returns:
            'insufficient' if < 30 samples
            'preliminary' if 30-89 samples
            'validated' if >= 90 samples
        """
        if sample_size < self.PRELIMINARY_THRESHOLD:
            return "insufficient"
        elif sample_size < self.VALIDATED_THRESHOLD:
            return "preliminary"
        else:
            return "validated"

    def calculate_confidence_interval(
        self,
        bias: float,
        std_dev: float,
        sample_size: int,
        confidence: float = 0.95,
    ) -> Tuple[float, float]:
        """Calculate confidence interval using t-distribution.

        Args:
            bias: The mean bias value.
            std_dev: Standard deviation of deviations.
            sample_size: Number of samples.
            confidence: Confidence level (default 0.95 for 95% CI).

        Returns:
            Tuple of (ci_lower, ci_upper) bounds.
        """
        # Handle edge cases
        if sample_size <= 1 or std_dev == 0:
            return (bias, bias)

        # Calculate t-statistic for given confidence level
        # degrees of freedom = sample_size - 1
        t_stat = stats.t.ppf((1 + confidence) / 2, sample_size - 1)

        # Standard error = std_dev / sqrt(n)
        se = std_dev / (sample_size ** 0.5)

        # Margin of error
        margin = t_stat * se

        return (bias - margin, bias + margin)

    async def save_metrics(
        self,
        db: AsyncSession,
        metrics: AccuracyMetrics,
    ) -> None:
        """Save or update metrics in database (upsert).

        Uses PostgreSQL ON CONFLICT DO UPDATE for upsert behavior.
        For SQLite (tests), falls back to query-then-insert/update.

        Args:
            db: Async database session.
            metrics: AccuracyMetrics to save.
        """
        # Check if using PostgreSQL (has ON CONFLICT support)
        dialect = db.bind.dialect.name if db.bind else "unknown"

        if dialect == "postgresql":
            # Use PostgreSQL upsert
            stmt = pg_insert(AccuracyMetric).values(
                model_id=metrics.model_id,
                site_id=metrics.site_id,
                parameter_id=metrics.parameter_id,
                horizon=metrics.horizon,
                mae=metrics.mae,
                bias=metrics.bias,
                std_dev=metrics.std_dev,
                sample_size=metrics.sample_size,
                confidence_level=metrics.confidence_level,
                ci_lower=metrics.ci_lower,
                ci_upper=metrics.ci_upper,
                min_deviation=metrics.min_deviation,
                max_deviation=metrics.max_deviation,
                calculated_at=datetime.now(tz=timezone.utc),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_accuracy_metrics_unique",
                set_={
                    "mae": stmt.excluded.mae,
                    "bias": stmt.excluded.bias,
                    "std_dev": stmt.excluded.std_dev,
                    "sample_size": stmt.excluded.sample_size,
                    "confidence_level": stmt.excluded.confidence_level,
                    "ci_lower": stmt.excluded.ci_lower,
                    "ci_upper": stmt.excluded.ci_upper,
                    "min_deviation": stmt.excluded.min_deviation,
                    "max_deviation": stmt.excluded.max_deviation,
                    "calculated_at": stmt.excluded.calculated_at,
                },
            )
            await db.execute(stmt)
            await db.commit()
        else:
            # SQLite fallback: query then insert/update
            query = select(AccuracyMetric).where(
                AccuracyMetric.model_id == metrics.model_id,
                AccuracyMetric.site_id == metrics.site_id,
                AccuracyMetric.parameter_id == metrics.parameter_id,
                AccuracyMetric.horizon == metrics.horizon,
            )
            result = await db.execute(query)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing record
                existing.mae = metrics.mae
                existing.bias = metrics.bias
                existing.std_dev = metrics.std_dev
                existing.sample_size = metrics.sample_size
                existing.confidence_level = metrics.confidence_level
                existing.ci_lower = metrics.ci_lower
                existing.ci_upper = metrics.ci_upper
                existing.min_deviation = metrics.min_deviation
                existing.max_deviation = metrics.max_deviation
                existing.calculated_at = datetime.now(tz=timezone.utc)
            else:
                # Insert new record
                new_metric = AccuracyMetric(
                    model_id=metrics.model_id,
                    site_id=metrics.site_id,
                    parameter_id=metrics.parameter_id,
                    horizon=metrics.horizon,
                    mae=metrics.mae,
                    bias=metrics.bias,
                    std_dev=metrics.std_dev,
                    sample_size=metrics.sample_size,
                    confidence_level=metrics.confidence_level,
                    ci_lower=metrics.ci_lower,
                    ci_upper=metrics.ci_upper,
                    min_deviation=metrics.min_deviation,
                    max_deviation=metrics.max_deviation,
                )
                db.add(new_metric)

            await db.commit()

        logger.info(
            f"Saved metrics for model={metrics.model_id}, site={metrics.site_id}, "
            f"param={metrics.parameter_id}, horizon={metrics.horizon}"
        )
