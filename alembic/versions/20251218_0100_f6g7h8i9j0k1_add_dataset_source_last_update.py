"""Add source_last_update column to dataset table.

This column stores the source's last update timestamp (from TOC metadata).
Used for smart refresh: only re-fetch datasets when the source has updated.

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2025-12-18 01:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# Revision identifiers
revision: str = "f6g7h8i9j0k1"
down_revision: str | None = "e5f6g7h8i9j0"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add source_last_update column and index."""
    op.add_column(
        "dataset",
        sa.Column("source_last_update", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "idx_dataset_source_last_update",
        "dataset",
        ["source_last_update"],
    )


def downgrade() -> None:
    """Remove source_last_update column and index."""
    op.drop_index("idx_dataset_source_last_update", table_name="dataset")
    op.drop_column("dataset", "source_last_update")
