"""add_dataset_content_hash

Adds content_hash column to dataset table for change detection.
This allows skipping updates when dataset content hasn't changed.

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2025-12-15 19:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6g7h8i9"
down_revision: str | None = "c3d4e5f6g7h8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add content_hash column to dataset table."""
    op.add_column(
        "dataset",
        sa.Column(
            "content_hash",
            sa.String(length=64),  # SHA256 hex digest is 64 characters
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove content_hash column from dataset table."""
    op.drop_column("dataset", "content_hash")
