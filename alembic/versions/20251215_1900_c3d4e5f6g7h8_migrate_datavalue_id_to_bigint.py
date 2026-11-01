"""migrate_datavalue_id_to_bigint

Fixes sequence overflow: datavalue_id_seq reached INTEGER max (2,147,483,647).
Migrates id column and sequence to BIGINT (max 9,223,372,036,854,775,807).

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-12-15 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: str | None = "b2c3d4e5f6g7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migrate datavalue.id from INTEGER to BIGINT.

    This is critical to fix the sequence overflow error:
    'nextval: reached maximum value of sequence "datavalue_id_seq" (2147483647)'
    """
    # Step 1: Alter the id column type from INTEGER to BIGINT
    op.alter_column(
        "datavalue",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )

    # Step 2: Alter the sequence to use BIGINT
    # This removes the max_value limit of 2147483647
    op.execute("ALTER SEQUENCE datavalue_id_seq AS BIGINT")


def downgrade() -> None:
    """Revert datavalue.id from BIGINT to INTEGER.

    WARNING: This will fail if any id values exceed 2147483647.
    """
    # Revert sequence to INTEGER type
    op.execute("ALTER SEQUENCE datavalue_id_seq AS INTEGER")

    # Revert column type
    op.alter_column(
        "datavalue",
        "id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
