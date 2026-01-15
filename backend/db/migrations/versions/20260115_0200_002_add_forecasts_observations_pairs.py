"""Add forecasts, observations, and forecast_observation_pairs tables.

Revision ID: 002
Revises: 001
Create Date: 2026-01-15

Creates intermediate storage tables for the matching engine:
- forecasts: Individual forecast predictions from weather models
- observations: Actual observed values from weather beacons
- forecast_observation_pairs: Staging table for matched forecast-observation pairs

This enables the matching pipeline:
Collectors -> forecasts/observations -> MatchingService -> pairs -> DeviationService -> deviations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create forecasts table
    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("parameter_id", sa.Integer(), nullable=False),
        sa.Column(
            "forecast_run",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "valid_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("value", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["models.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parameter_id"],
            ["parameters.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "site_id", "model_id", "parameter_id", "forecast_run", "valid_time",
            name="uq_forecasts_unique"
        ),
    )

    # Create indexes for forecasts table
    op.create_index(
        "idx_forecasts_site_model_param",
        "forecasts",
        ["site_id", "model_id", "parameter_id"],
    )
    op.create_index(
        "idx_forecasts_valid_time",
        "forecasts",
        ["valid_time"],
    )

    # Create observations table
    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("parameter_id", sa.Integer(), nullable=False),
        sa.Column(
            "observation_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("value", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parameter_id"],
            ["parameters.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "site_id", "parameter_id", "observation_time", "source",
            name="uq_observations_unique"
        ),
    )

    # Create indexes for observations table
    op.create_index(
        "idx_observations_site_param",
        "observations",
        ["site_id", "parameter_id"],
    )
    op.create_index(
        "idx_observations_time",
        "observations",
        ["observation_time"],
    )

    # Create forecast_observation_pairs staging table
    op.create_table(
        "forecast_observation_pairs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("forecast_id", sa.Integer(), nullable=False),
        sa.Column("observation_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("parameter_id", sa.Integer(), nullable=False),
        sa.Column(
            "forecast_run",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "valid_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("forecast_value", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("observed_value", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("time_diff_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["forecast_id"],
            ["forecasts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["observations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["models.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parameter_id"],
            ["parameters.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "forecast_id", "observation_id",
            name="uq_pairs_forecast_observation"
        ),
    )

    # Create indexes for forecast_observation_pairs table
    op.create_index(
        "idx_pairs_site_model_param",
        "forecast_observation_pairs",
        ["site_id", "model_id", "parameter_id"],
    )
    op.create_index(
        "idx_pairs_valid_time",
        "forecast_observation_pairs",
        ["valid_time"],
    )
    op.create_index(
        "idx_pairs_horizon",
        "forecast_observation_pairs",
        ["horizon"],
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes for forecast_observation_pairs
    op.drop_index("idx_pairs_horizon", table_name="forecast_observation_pairs")
    op.drop_index("idx_pairs_valid_time", table_name="forecast_observation_pairs")
    op.drop_index("idx_pairs_site_model_param", table_name="forecast_observation_pairs")

    # Drop forecast_observation_pairs table
    op.drop_table("forecast_observation_pairs")

    # Drop indexes for observations
    op.drop_index("idx_observations_time", table_name="observations")
    op.drop_index("idx_observations_site_param", table_name="observations")

    # Drop observations table
    op.drop_table("observations")

    # Drop indexes for forecasts
    op.drop_index("idx_forecasts_valid_time", table_name="forecasts")
    op.drop_index("idx_forecasts_site_model_param", table_name="forecasts")

    # Drop forecasts table
    op.drop_table("forecasts")
