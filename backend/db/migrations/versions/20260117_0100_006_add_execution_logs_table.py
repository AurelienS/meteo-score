"""Add execution_logs table and beacon IDs to sites.

Revision ID: 006
Revises: 005
Create Date: 2026-01-17

Creates:
- execution_logs table to persist job execution history across restarts
- Adds romma_beacon_id and ffvl_beacon_id columns to sites table

This supports story 6.8: Fix Data Collection Pipeline.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create execution_logs table and add beacon IDs to sites."""
    # Create execution_logs table
    op.create_table(
        "execution_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=100), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("records_collected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_persisted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index(
        "idx_execution_logs_job_id",
        "execution_logs",
        ["job_id"],
    )
    op.create_index(
        "idx_execution_logs_start_time",
        "execution_logs",
        [sa.text("start_time DESC")],
    )

    # Add beacon ID columns to sites table (primary and backup)
    op.add_column("sites", sa.Column("romma_beacon_id", sa.Integer(), nullable=True))
    op.add_column("sites", sa.Column("romma_beacon_id_backup", sa.Integer(), nullable=True))
    op.add_column("sites", sa.Column("ffvl_beacon_id", sa.Integer(), nullable=True))
    op.add_column("sites", sa.Column("ffvl_beacon_id_backup", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Drop execution_logs table and beacon ID columns."""
    # Remove beacon ID columns from sites (backup and primary)
    op.drop_column("sites", "ffvl_beacon_id_backup")
    op.drop_column("sites", "ffvl_beacon_id")
    op.drop_column("sites", "romma_beacon_id_backup")
    op.drop_column("sites", "romma_beacon_id")

    # Drop execution_logs table
    op.drop_index("idx_execution_logs_start_time", table_name="execution_logs")
    op.drop_index("idx_execution_logs_job_id", table_name="execution_logs")
    op.drop_table("execution_logs")
