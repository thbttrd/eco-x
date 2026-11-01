"""add_dataset_record_count

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-12-14 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add record_count column to dataset table and backfill existing data."""
    # Add the column with server default for new rows
    op.add_column(
        "dataset",
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # Backfill existing datasets with actual counts from datavalue table
    # This may take a while on large databases
    op.execute(
        """
        UPDATE dataset
        SET record_count = (
            SELECT COUNT(*)
            FROM datavalue
            WHERE datavalue.dataset_id = dataset.id
        )
        """
    )

    # Remove server default after backfill (let application handle defaults)
    op.alter_column("dataset", "record_count", server_default=None)


def downgrade() -> None:
    """Remove record_count column from dataset table."""
    op.drop_column("dataset", "record_count")
