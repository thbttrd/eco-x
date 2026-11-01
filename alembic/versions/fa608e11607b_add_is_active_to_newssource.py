"""add is_active to newssource

Revision ID: fa608e11607b
Revises: 93aa5793c847
Create Date: 2025-12-22 18:31:02.702874
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel  # noqa: F401 - Required for SQLModel column types

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fa608e11607b"
down_revision: str | None = "93aa5793c847"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply migration changes."""
    # Add is_active column to newssource with default=False
    # This disables all existing sources until explicitly enabled
    with op.batch_alter_table("newssource", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_index(batch_op.f("ix_newssource_is_active"), ["is_active"], unique=False)


def downgrade() -> None:
    """Revert migration changes."""
    with op.batch_alter_table("newssource", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_newssource_is_active"))
        batch_op.drop_column("is_active")
