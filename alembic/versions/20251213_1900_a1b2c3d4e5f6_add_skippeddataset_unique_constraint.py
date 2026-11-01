"""add_skippeddataset_unique_constraint

Revision ID: a1b2c3d4e5f6
Revises: da35060794b5
Create Date: 2025-12-13 19:00:00.000000

"""

from collections.abc import Sequence

from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "da35060794b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add unique constraint on skippeddataset (source, dataset_code).

    Note: Skip if table doesn't exist (table may have been removed from models).
    """
    bind = op.get_bind()
    inspector = inspect(bind)
    if "skippeddataset" in inspector.get_table_names():
        op.create_unique_constraint(
            "uq_skippeddataset_source_code",
            "skippeddataset",
            ["source", "dataset_code"],
        )


def downgrade() -> None:
    """Remove unique constraint from skippeddataset."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if "skippeddataset" in inspector.get_table_names():
        op.drop_constraint(
            "uq_skippeddataset_source_code",
            "skippeddataset",
            type_="unique",
        )
