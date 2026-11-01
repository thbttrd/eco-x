"""add_datavalue_unique_constraint

Adds unique constraint on (dataset_id, geo, time_period, indicator)
to enable UPSERT operations with ON CONFLICT.

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2025-12-15 19:10:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6g7h8i9j0"
down_revision: str | None = "d4e5f6g7h8i9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add unique constraint for UPSERT operations.

    This constraint enables PostgreSQL ON CONFLICT to work correctly,
    allowing us to update existing rows instead of always deleting/inserting.
    """
    op.create_unique_constraint(
        "uq_datavalue_dataset_geo_time_indicator",
        "datavalue",
        ["dataset_id", "geo", "time_period", "indicator"],
    )


def downgrade() -> None:
    """Remove unique constraint."""
    op.drop_constraint(
        "uq_datavalue_dataset_geo_time_indicator",
        "datavalue",
        type_="unique",
    )
