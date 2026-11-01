"""Add source_url column to dataset table.

This column stores the URL to the original dataset page on the source website.
Used for displaying "View on source website" links in the dataset detail modal.

Revision ID: 20251228_0100
Revises: 20251226_1200
Create Date: 2025-12-28 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251228_0100"
down_revision: str | None = "20251226_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add source_url column to dataset table."""
    op.add_column(
        "dataset",
        sa.Column("source_url", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    """Remove source_url column from dataset table."""
    op.drop_column("dataset", "source_url")
