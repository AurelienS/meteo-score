"""Add TimescaleDB continuous aggregates for pre-computed metrics.

Revision ID: 005
Revises: 004
Create Date: 2026-01-15

Creates continuous aggregates for daily, weekly, and monthly accuracy metrics.
These pre-compute MAE, bias, std_dev from the deviations hypertable for fast queries.

IMPORTANT: This migration requires TimescaleDB extension and will fail on SQLite.
Run only on PostgreSQL with TimescaleDB enabled.

This supports story 3.4: TimescaleDB Continuous Aggregates.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create continuous aggregates and refresh policies."""
    connection = op.get_bind()

    # Check if TimescaleDB is available
    result = connection.execute(text(
        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
    ))
    has_timescaledb = result.scalar()

    if not has_timescaledb:
        print("WARNING: TimescaleDB not available, skipping continuous aggregates")
        return

    # Daily Aggregate - MAE, bias, std_dev per day
    connection.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS daily_accuracy_metrics
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('1 day', timestamp) AS bucket,
            site_id,
            model_id,
            parameter_id,
            horizon,
            AVG(ABS(deviation)) AS mae,
            AVG(deviation) AS bias,
            STDDEV(deviation) AS std_dev,
            COUNT(*) AS sample_size,
            MIN(deviation) AS min_deviation,
            MAX(deviation) AS max_deviation
        FROM deviations
        GROUP BY bucket, site_id, model_id, parameter_id, horizon
        WITH NO DATA;
    """))

    # Daily refresh policy - refresh every day, looking back 3 days
    connection.execute(text("""
        SELECT add_continuous_aggregate_policy('daily_accuracy_metrics',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 day',
            if_not_exists => TRUE);
    """))

    # Weekly Aggregate
    connection.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS weekly_accuracy_metrics
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('7 days', timestamp) AS bucket,
            site_id,
            model_id,
            parameter_id,
            horizon,
            AVG(ABS(deviation)) AS mae,
            AVG(deviation) AS bias,
            STDDEV(deviation) AS std_dev,
            COUNT(*) AS sample_size,
            MIN(deviation) AS min_deviation,
            MAX(deviation) AS max_deviation
        FROM deviations
        GROUP BY bucket, site_id, model_id, parameter_id, horizon
        WITH NO DATA;
    """))

    # Weekly refresh policy
    connection.execute(text("""
        SELECT add_continuous_aggregate_policy('weekly_accuracy_metrics',
            start_offset => INTERVAL '3 weeks',
            end_offset => INTERVAL '1 day',
            schedule_interval => INTERVAL '1 week',
            if_not_exists => TRUE);
    """))

    # Monthly Aggregate
    connection.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_accuracy_metrics
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket('30 days', timestamp) AS bucket,
            site_id,
            model_id,
            parameter_id,
            horizon,
            AVG(ABS(deviation)) AS mae,
            AVG(deviation) AS bias,
            STDDEV(deviation) AS std_dev,
            COUNT(*) AS sample_size,
            MIN(deviation) AS min_deviation,
            MAX(deviation) AS max_deviation
        FROM deviations
        GROUP BY bucket, site_id, model_id, parameter_id, horizon
        WITH NO DATA;
    """))

    # Monthly refresh policy
    connection.execute(text("""
        SELECT add_continuous_aggregate_policy('monthly_accuracy_metrics',
            start_offset => INTERVAL '3 months',
            end_offset => INTERVAL '1 day',
            schedule_interval => INTERVAL '30 days',
            if_not_exists => TRUE);
    """))

    print("Continuous aggregates created successfully")


def downgrade() -> None:
    """Drop continuous aggregates and their policies."""
    connection = op.get_bind()

    # Check if TimescaleDB is available
    result = connection.execute(text(
        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
    ))
    has_timescaledb = result.scalar()

    if not has_timescaledb:
        return

    # Remove policies first (if they exist)
    try:
        connection.execute(text(
            "SELECT remove_continuous_aggregate_policy('monthly_accuracy_metrics', if_exists => TRUE)"
        ))
        connection.execute(text(
            "SELECT remove_continuous_aggregate_policy('weekly_accuracy_metrics', if_exists => TRUE)"
        ))
        connection.execute(text(
            "SELECT remove_continuous_aggregate_policy('daily_accuracy_metrics', if_exists => TRUE)"
        ))
    except Exception:
        pass  # Policies might not exist

    # Drop materialized views
    connection.execute(text("DROP MATERIALIZED VIEW IF EXISTS monthly_accuracy_metrics CASCADE"))
    connection.execute(text("DROP MATERIALIZED VIEW IF EXISTS weekly_accuracy_metrics CASCADE"))
    connection.execute(text("DROP MATERIALIZED VIEW IF EXISTS daily_accuracy_metrics CASCADE"))
