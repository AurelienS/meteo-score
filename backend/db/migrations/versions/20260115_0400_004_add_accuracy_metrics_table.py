"""Add accuracy_metrics table for statistical metrics.

Revision ID: 004
Revises: 003
Create Date: 2026-01-15

Creates accuracy_metrics table to store calculated statistical metrics
(MAE, bias, standard deviation, confidence intervals) for each
model/site/parameter/horizon combination.

This supports story 3.3: Statistical Metrics Calculator (MAE, Bias).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create accuracy_metrics table with indexes."""
    op.create_table(
        "accuracy_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("parameter_id", sa.Integer(), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("mae", sa.DECIMAL(10, 4), nullable=False),
        sa.Column("bias", sa.DECIMAL(10, 4), nullable=False),
        sa.Column("std_dev", sa.DECIMAL(10, 4), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("confidence_level", sa.String(20), nullable=False),
        sa.Column("ci_lower", sa.DECIMAL(10, 4), nullable=True),
        sa.Column("ci_upper", sa.DECIMAL(10, 4), nullable=True),
        sa.Column("min_deviation", sa.DECIMAL(10, 4), nullable=False),
        sa.Column("max_deviation", sa.DECIMAL(10, 4), nullable=False),
        sa.Column(
            "calculated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["model_id"], ["models.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["parameter_id"], ["parameters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_id", "site_id", "parameter_id", "horizon",
            name="uq_accuracy_metrics_unique"
        ),
    )

    # Create indexes for efficient querying
    op.create_index(
        "idx_metrics_site_param",
        "accuracy_metrics",
        ["site_id", "parameter_id"],
    )
    op.create_index(
        "idx_metrics_confidence",
        "accuracy_metrics",
        ["confidence_level"],
    )
    op.create_index(
        "idx_metrics_model_horizon",
        "accuracy_metrics",
        ["model_id", "horizon"],
    )


def downgrade() -> None:
    """Drop accuracy_metrics table and indexes."""
    op.drop_index("idx_metrics_model_horizon", table_name="accuracy_metrics")
    op.drop_index("idx_metrics_confidence", table_name="accuracy_metrics")
    op.drop_index("idx_metrics_site_param", table_name="accuracy_metrics")
    op.drop_table("accuracy_metrics")
