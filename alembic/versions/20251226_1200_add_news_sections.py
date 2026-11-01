"""Add news sections and entries (US-5.9 to US-5.13).

This migration transforms the news schema from flat to hierarchical:
- NewsSource (with URL) → NewsSection (new table)
- NewsArticle → NewsEntry (renamed, FK changed to section_id)
- NewsSource now just a container for sections
- NewsFetchLog now references sections

Revision ID: 20251226_1200
Revises: fa608e11607b
Create Date: 2025-12-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251226_1200"
down_revision: str | None = "fa608e11607b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade to hierarchical news structure."""
    conn = op.get_bind()

    # Step 1: Create newssection table
    op.create_table(
        "newssection",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("parse_selector", sa.String(), nullable=True),
        sa.Column("parse_comment", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("fetch_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("last_fetched_at", sa.DateTime(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("last_fetch_status", sa.String(), nullable=True),
        sa.Column("last_fetch_error", sa.String(), nullable=True),
        sa.Column("add_date", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["newssource.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(op.f("ix_newssection_is_active"), "newssection", ["is_active"], unique=False)
    op.create_index(op.f("ix_newssection_source_id"), "newssection", ["source_id"], unique=False)

    # Step 2: Create newsentry table
    op.create_table(
        "newsentry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(), nullable=True),
        sa.Column("content_full", sa.Text(), nullable=True),
        sa.Column("content_preview", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["section_id"], ["newssection.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(
        op.f("ix_newsentry_discovered_at"), "newsentry", ["discovered_at"], unique=False
    )
    op.create_index(op.f("ix_newsentry_section_id"), "newsentry", ["section_id"], unique=False)

    # Step 3: Migrate data from newssource to newssection
    # For each source with a URL, create a corresponding section
    conn.execute(
        text(
            """
        INSERT INTO newssection (
            source_id, title, url, parse_selector, parse_comment,
            is_active, fetch_interval_minutes, last_fetched_at, last_checked_at,
            last_fetch_status, last_fetch_error, add_date
        )
        SELECT
            id, title, url, parse_selector, parse_comment,
            is_active, fetch_interval_minutes, last_fetched_at, last_checked_at,
            last_fetch_status, last_fetch_error, add_date
        FROM newssource
        WHERE url IS NOT NULL
    """
        )
    )

    # Step 4: Migrate articles to entries via section lookup
    # newsarticle.source_id → newsentry.section_id (via newssection lookup)
    conn.execute(
        text(
            """
        INSERT INTO newsentry (
            section_id, title, url, published_at, discovered_at, content_preview
        )
        SELECT
            ns.id, na.title, na.url, na.published_at, na.discovered_at, na.content_preview
        FROM newsarticle na
        JOIN newssource src ON na.source_id = src.id
        JOIN newssection ns ON ns.url = src.url
    """
        )
    )

    # Step 5: Add description column to newssource
    with op.batch_alter_table("newssource", schema=None) as batch_op:
        batch_op.add_column(sa.Column("description", sa.String(), nullable=True))

    # Step 6: Update newsfetchlog - add section_id, rename columns
    # First, add section_id column
    with op.batch_alter_table("newsfetchlog", schema=None) as batch_op:
        batch_op.add_column(sa.Column("section_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("entries_found", sa.Integer(), server_default="0"))
        batch_op.add_column(sa.Column("entries_new", sa.Integer(), server_default="0"))

    # Populate section_id from source_id via newssection lookup
    conn.execute(
        text(
            """
        UPDATE newsfetchlog
        SET section_id = (
            SELECT ns.id
            FROM newssource src
            JOIN newssection ns ON ns.url = src.url
            WHERE src.id = newsfetchlog.source_id
        )
    """
        )
    )

    # Copy articles_found/new to entries_found/new
    conn.execute(
        text(
            """
        UPDATE newsfetchlog
        SET entries_found = articles_found, entries_new = articles_new
    """
        )
    )

    # Create index and FK for section_id, then drop old columns
    with op.batch_alter_table("newsfetchlog", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_newsfetchlog_section_id"), ["section_id"], unique=False
        )
        batch_op.create_foreign_key(
            "newsfetchlog_section_id_fkey", "newssection", ["section_id"], ["id"]
        )
        batch_op.drop_constraint("newsfetchlog_source_id_fkey", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_newsfetchlog_source_id"))
        batch_op.drop_column("source_id")
        batch_op.drop_column("articles_found")
        batch_op.drop_column("articles_new")

    # Step 7: Drop old columns from newssource
    with op.batch_alter_table("newssource", schema=None) as batch_op:
        batch_op.drop_constraint("newssource_url_key", type_="unique")
        batch_op.drop_column("url")
        batch_op.drop_column("parse_selector")
        batch_op.drop_column("parse_comment")
        batch_op.drop_column("last_fetched_at")
        batch_op.drop_column("last_checked_at")
        batch_op.drop_column("last_fetch_status")
        batch_op.drop_column("last_fetch_error")

    # Step 8: Drop newsarticle table
    op.drop_table("newsarticle")


def downgrade() -> None:
    """Downgrade back to flat structure.

    WARNING: This will lose any sections created after the migration
    that don't correspond to original sources.
    """
    conn = op.get_bind()

    # Step 1: Recreate newsarticle table
    op.create_table(
        "newsarticle",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(), nullable=True),
        sa.Column("content_preview", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["newssource.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(
        op.f("ix_newsarticle_discovered_at"), "newsarticle", ["discovered_at"], unique=False
    )
    op.create_index(op.f("ix_newsarticle_source_id"), "newsarticle", ["source_id"], unique=False)

    # Step 2: Add back columns to newssource
    with op.batch_alter_table("newssource", schema=None) as batch_op:
        batch_op.add_column(sa.Column("url", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("parse_selector", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("parse_comment", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_fetched_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_checked_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("last_fetch_status", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("last_fetch_error", sa.String(), nullable=True))

    # Step 3: Restore newssource data from sections (first section per source)
    conn.execute(
        text(
            """
        UPDATE newssource
        SET url = (
            SELECT ns.url FROM newssection ns
            WHERE ns.source_id = newssource.id
            ORDER BY ns.id
            LIMIT 1
        ),
        parse_selector = (
            SELECT ns.parse_selector FROM newssection ns
            WHERE ns.source_id = newssource.id
            ORDER BY ns.id
            LIMIT 1
        ),
        parse_comment = (
            SELECT ns.parse_comment FROM newssection ns
            WHERE ns.source_id = newssource.id
            ORDER BY ns.id
            LIMIT 1
        ),
        last_fetched_at = (
            SELECT ns.last_fetched_at FROM newssection ns
            WHERE ns.source_id = newssource.id
            ORDER BY ns.id
            LIMIT 1
        ),
        last_checked_at = (
            SELECT ns.last_checked_at FROM newssection ns
            WHERE ns.source_id = newssource.id
            ORDER BY ns.id
            LIMIT 1
        ),
        last_fetch_status = (
            SELECT ns.last_fetch_status FROM newssection ns
            WHERE ns.source_id = newssource.id
            ORDER BY ns.id
            LIMIT 1
        ),
        last_fetch_error = (
            SELECT ns.last_fetch_error FROM newssection ns
            WHERE ns.source_id = newssource.id
            ORDER BY ns.id
            LIMIT 1
        )
    """
        )
    )

    # Add unique constraint on url
    with op.batch_alter_table("newssource", schema=None) as batch_op:
        batch_op.create_unique_constraint("newssource_url_key", ["url"])

    # Step 4: Restore newsfetchlog
    with op.batch_alter_table("newsfetchlog", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("articles_found", sa.Integer(), server_default="0"))
        batch_op.add_column(sa.Column("articles_new", sa.Integer(), server_default="0"))

    # Populate source_id from section_id via newssection lookup
    conn.execute(
        text(
            """
        UPDATE newsfetchlog
        SET source_id = (
            SELECT ns.source_id FROM newssection ns
            WHERE ns.id = newsfetchlog.section_id
        ),
        articles_found = entries_found,
        articles_new = entries_new
    """
        )
    )

    with op.batch_alter_table("newsfetchlog", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_newsfetchlog_source_id"), ["source_id"], unique=False)
        batch_op.create_foreign_key(
            "newsfetchlog_source_id_fkey", "newssource", ["source_id"], ["id"]
        )
        batch_op.drop_constraint("newsfetchlog_section_id_fkey", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_newsfetchlog_section_id"))
        batch_op.drop_column("section_id")
        batch_op.drop_column("entries_found")
        batch_op.drop_column("entries_new")

    # Step 5: Migrate entries back to articles
    conn.execute(
        text(
            """
        INSERT INTO newsarticle (
            source_id, title, url, published_at, discovered_at, content_preview
        )
        SELECT
            ns.source_id, ne.title, ne.url, ne.published_at, ne.discovered_at, ne.content_preview
        FROM newsentry ne
        JOIN newssection ns ON ne.section_id = ns.id
    """
        )
    )

    # Step 6: Drop description from newssource
    with op.batch_alter_table("newssource", schema=None) as batch_op:
        batch_op.drop_column("description")

    # Step 7: Drop newsentry and newssection tables
    op.drop_table("newsentry")
    op.drop_table("newssection")
