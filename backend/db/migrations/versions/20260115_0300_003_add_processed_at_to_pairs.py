"""Add processed_at column to forecast_observation_pairs table.

Revision ID: 003
Revises: 002
Create Date: 2026-01-15

Adds processed_at timestamp column to track which pairs have been
processed into deviations. This enables idempotent processing:
- NULL: Pair not yet processed
- Timestamp: When pair was processed into deviation

This supports AC8 (Source Tracking) from story 3.2.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add processed_at column to forecast_observation_pairs."""
    op.add_column(
        "forecast_observation_pairs",
        sa.Column(
            "processed_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )

    # Add index for efficient querying of unprocessed pairs
    op.create_index(
        "idx_pairs_processed_at",
        "forecast_observation_pairs",
        ["processed_at"],
    )


def downgrade() -> None:
    """Remove processed_at column from forecast_observation_pairs."""
    op.drop_index("idx_pairs_processed_at", table_name="forecast_observation_pairs")
    op.drop_column("forecast_observation_pairs", "processed_at")
