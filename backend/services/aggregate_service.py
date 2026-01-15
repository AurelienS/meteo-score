"""AggregateService for querying TimescaleDB continuous aggregates.

This module provides the AggregateService class for querying pre-computed
accuracy metrics from TimescaleDB continuous aggregates.

Implements story 3.4: TimescaleDB Continuous Aggregates.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class AggregateMetrics:
    """Data class for aggregate metrics from continuous aggregates."""

    bucket: datetime
    site_id: int
    model_id: int
    parameter_id: int
    horizon: int
    mae: Decimal
    bias: Decimal
    std_dev: Optional[Decimal]
    sample_size: int
    min_deviation: Optional[Decimal]
    max_deviation: Optional[Decimal]


class AggregateService:
    """Service for querying TimescaleDB continuous aggregates.

    Provides methods to query pre-computed daily, weekly, and monthly
    accuracy metrics from continuous aggregates, and to manually refresh them.

    Note: This service requires PostgreSQL with TimescaleDB extension.
    Methods will raise RuntimeError if used with SQLite or PostgreSQL without TimescaleDB.
    """

    DAILY_VIEW = "daily_accuracy_metrics"
    WEEKLY_VIEW = "weekly_accuracy_metrics"
    MONTHLY_VIEW = "monthly_accuracy_metrics"

    async def _check_timescaledb(self, db: AsyncSession) -> bool:
        """Check if TimescaleDB extension is available.

        Returns:
            True if TimescaleDB is available, False otherwise.
        """
        dialect = db.bind.dialect.name if db.bind else "unknown"
        if dialect != "postgresql":
            logger.debug(f"TimescaleDB not available: dialect is '{dialect}', not 'postgresql'")
            return False

        result = await db.execute(text(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
        ))
        has_timescaledb = result.scalar() or False
        if not has_timescaledb:
            logger.warning("PostgreSQL detected but TimescaleDB extension not installed")
        return has_timescaledb

    async def _ensure_timescaledb(self, db: AsyncSession) -> None:
        """Ensure TimescaleDB is available, raise error if not."""
        if not await self._check_timescaledb(db):
            raise RuntimeError(
                "TimescaleDB extension required. "
                "This feature is only available on PostgreSQL with TimescaleDB."
            )

    async def query_daily_metrics(
        self,
        db: AsyncSession,
        site_id: int,
        model_id: Optional[int] = None,
        parameter_id: Optional[int] = None,
        horizon: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AggregateMetrics]:
        """Query daily pre-computed metrics from continuous aggregate.

        Args:
            db: Database session.
            site_id: Site ID to query (required).
            model_id: Optional model ID filter.
            parameter_id: Optional parameter ID filter.
            horizon: Optional horizon filter.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            limit: Maximum results to return.

        Returns:
            List of AggregateMetrics from daily aggregate.

        Raises:
            RuntimeError: If TimescaleDB is not available.
        """
        await self._ensure_timescaledb(db)
        return await self._query_aggregate(
            db, self.DAILY_VIEW, site_id, model_id, parameter_id,
            horizon, start_date, end_date, limit
        )

    async def query_weekly_metrics(
        self,
        db: AsyncSession,
        site_id: int,
        model_id: Optional[int] = None,
        parameter_id: Optional[int] = None,
        horizon: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AggregateMetrics]:
        """Query weekly pre-computed metrics from continuous aggregate."""
        await self._ensure_timescaledb(db)
        return await self._query_aggregate(
            db, self.WEEKLY_VIEW, site_id, model_id, parameter_id,
            horizon, start_date, end_date, limit
        )

    async def query_monthly_metrics(
        self,
        db: AsyncSession,
        site_id: int,
        model_id: Optional[int] = None,
        parameter_id: Optional[int] = None,
        horizon: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AggregateMetrics]:
        """Query monthly pre-computed metrics from continuous aggregate."""
        await self._ensure_timescaledb(db)
        return await self._query_aggregate(
            db, self.MONTHLY_VIEW, site_id, model_id, parameter_id,
            horizon, start_date, end_date, limit
        )

    async def _query_aggregate(
        self,
        db: AsyncSession,
        view_name: str,
        site_id: int,
        model_id: Optional[int],
        parameter_id: Optional[int],
        horizon: Optional[int],
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        limit: int,
    ) -> List[AggregateMetrics]:
        """Internal method to query a continuous aggregate view."""
        # Build query with filters
        query = f"""
            SELECT
                bucket,
                site_id,
                model_id,
                parameter_id,
                horizon,
                mae,
                bias,
                std_dev,
                sample_size,
                min_deviation,
                max_deviation
            FROM {view_name}
            WHERE site_id = :site_id
        """
        params = {"site_id": site_id}

        if model_id is not None:
            query += " AND model_id = :model_id"
            params["model_id"] = model_id

        if parameter_id is not None:
            query += " AND parameter_id = :parameter_id"
            params["parameter_id"] = parameter_id

        if horizon is not None:
            query += " AND horizon = :horizon"
            params["horizon"] = horizon

        if start_date is not None:
            query += " AND bucket >= :start_date"
            params["start_date"] = start_date

        if end_date is not None:
            query += " AND bucket <= :end_date"
            params["end_date"] = end_date

        query += " ORDER BY bucket DESC LIMIT :limit"
        params["limit"] = limit

        result = await db.execute(text(query), params)
        rows = result.fetchall()

        return [
            AggregateMetrics(
                bucket=row.bucket,
                site_id=row.site_id,
                model_id=row.model_id,
                parameter_id=row.parameter_id,
                horizon=row.horizon,
                mae=Decimal(str(row.mae)) if row.mae else Decimal("0"),
                bias=Decimal(str(row.bias)) if row.bias else Decimal("0"),
                std_dev=Decimal(str(row.std_dev)) if row.std_dev else None,
                sample_size=row.sample_size,
                min_deviation=Decimal(str(row.min_deviation)) if row.min_deviation else None,
                max_deviation=Decimal(str(row.max_deviation)) if row.max_deviation else None,
            )
            for row in rows
        ]

    async def refresh_aggregate(
        self,
        db: AsyncSession,
        aggregate_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> None:
        """Manually refresh a continuous aggregate.

        Args:
            db: Database session.
            aggregate_name: Name of the continuous aggregate view.
            start_time: Optional start of refresh window.
            end_time: Optional end of refresh window.

        Raises:
            RuntimeError: If TimescaleDB is not available.
            ValueError: If aggregate_name is invalid.
        """
        await self._ensure_timescaledb(db)

        valid_aggregates = {self.DAILY_VIEW, self.WEEKLY_VIEW, self.MONTHLY_VIEW}
        if aggregate_name not in valid_aggregates:
            raise ValueError(
                f"Invalid aggregate name: {aggregate_name}. "
                f"Must be one of: {valid_aggregates}"
            )

        if start_time and end_time:
            # Use parameterized query for datetime values to prevent injection
            await db.execute(
                text(
                    f"CALL refresh_continuous_aggregate('{aggregate_name}', "
                    ":start_time, :end_time)"
                ),
                {"start_time": start_time, "end_time": end_time}
            )
        else:
            await db.execute(text(
                f"CALL refresh_continuous_aggregate('{aggregate_name}', NULL, NULL)"
            ))
        await db.commit()

        logger.info(f"Refreshed continuous aggregate: {aggregate_name}")

    async def refresh_daily_aggregate(
        self,
        db: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> None:
        """Refresh the daily accuracy metrics aggregate."""
        await self.refresh_aggregate(db, self.DAILY_VIEW, start_time, end_time)

    async def refresh_all_aggregates(
        self,
        db: AsyncSession,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> None:
        """Refresh all continuous aggregates.

        Args:
            db: Database session.
            start_time: Optional start of refresh window.
            end_time: Optional end of refresh window.
        """
        await self._ensure_timescaledb(db)

        for aggregate in [self.DAILY_VIEW, self.WEEKLY_VIEW, self.MONTHLY_VIEW]:
            await self.refresh_aggregate(db, aggregate, start_time, end_time)

        logger.info("Refreshed all continuous aggregates")

    async def get_aggregate_info(
        self,
        db: AsyncSession,
    ) -> dict:
        """Get information about continuous aggregates.

        Returns dict with aggregate names and their row counts.
        """
        await self._ensure_timescaledb(db)

        info = {}
        for view in [self.DAILY_VIEW, self.WEEKLY_VIEW, self.MONTHLY_VIEW]:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {view}"))
            info[view] = result.scalar() or 0

        return info
