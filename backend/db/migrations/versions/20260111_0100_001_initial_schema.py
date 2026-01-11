"""Initial schema with TimescaleDB hypertable.

Revision ID: 001
Revises:
Create Date: 2026-01-11

Creates the core database schema for MétéoScore:
- sites: Weather observation/forecast locations
- models: Weather forecast model sources
- parameters: Weather parameters (wind, temp, etc.)
- deviations: Time-series hypertable for forecast-observation comparisons

TimescaleDB-specific:
- Creates TimescaleDB extension
- Converts deviations to hypertable with 7-day chunk interval
- Creates optimized indexes for time-series queries
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create TimescaleDB extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    # Create sites table (reference data)
    op.create_table(
        "sites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.DECIMAL(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.DECIMAL(precision=9, scale=6), nullable=False),
        sa.Column("altitude", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create models table (reference data)
    op.create_table(
        "models",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create parameters table (reference data)
    op.create_table(
        "parameters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create deviations table (time-series data)
    # Composite primary key with timestamp first (required for hypertable)
    op.create_table(
        "deviations",
        sa.Column(
            "timestamp",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("parameter_id", sa.Integer(), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("forecast_value", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("observed_value", sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column("deviation", sa.DECIMAL(precision=10, scale=2), nullable=False),
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
        sa.PrimaryKeyConstraint(
            "timestamp", "site_id", "model_id", "parameter_id", "horizon"
        ),
    )

    # Convert deviations to TimescaleDB hypertable
    # chunk_time_interval = 7 days as specified in acceptance criteria
    op.execute("""
        SELECT create_hypertable(
            'deviations',
            'timestamp',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE
        )
    """)

    # Create indexes for optimized queries
    # idx_deviations_site_model: For filtering by site and model
    op.create_index(
        "idx_deviations_site_model",
        "deviations",
        ["site_id", "model_id"],
    )

    # idx_deviations_parameter: For filtering by parameter
    op.create_index(
        "idx_deviations_parameter",
        "deviations",
        ["parameter_id"],
    )

    # idx_deviations_timestamp: For time-based queries (DESC for recent-first)
    op.create_index(
        "idx_deviations_timestamp",
        "deviations",
        [sa.text("timestamp DESC")],
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes first
    op.drop_index("idx_deviations_timestamp", table_name="deviations")
    op.drop_index("idx_deviations_parameter", table_name="deviations")
    op.drop_index("idx_deviations_site_model", table_name="deviations")

    # Drop tables in reverse order (respect foreign keys)
    op.drop_table("deviations")
    op.drop_table("parameters")
    op.drop_table("models")
    op.drop_table("sites")

    # Note: We don't drop the TimescaleDB extension as other tables might use it
