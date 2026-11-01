"""News aggregation models for storing news sources, sections, and entries.

These models support the news fetching and parsing feature (Epic 5).

Hierarchy:
- NewsCategory: Groups related sources (e.g., "Central Banks")
- NewsSource: A conceptual news source (e.g., "ECB Monetary Policy")
- NewsSection: A specific page/feed within a source (e.g., "Monetary policy decisions")
- NewsEntry: An individual article/entry discovered from a section
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


def _utc_now() -> datetime:
    """Return current UTC time as naive datetime for database compatibility."""

    return datetime.now(UTC).replace(tzinfo=None)


class NewsCategory(SQLModel, table=True):
    """Category for organizing news sources.

    Categories group related news sources (e.g., "Central Banks", "National Statistics").
    Supports hierarchical structure via parent_id for subcategories.
    """

    __tablename__ = "newscategory"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Category name")
    parent_id: int | None = Field(
        default=None,
        foreign_key="newscategory.id",
        description="Parent category for hierarchical structure",
    )
    fetch_interval_minutes: int | None = Field(
        default=None,
        description="Override fetch interval for all sources in this category",
    )
    add_date: datetime = Field(
        default_factory=_utc_now,
        description="When this category was added",
    )


class NewsSource(SQLModel, table=True):
    """A news source container for sections.

    Sources are conceptual groupings (e.g., "ECB Monetary Policy") that contain
    one or more sections. Each section has its own URL and fetch configuration.

    US-5.9: URL-related fields moved to NewsSection.
    """

    __tablename__ = "newssource"

    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(description="Human-readable source title")
    description: str | None = Field(
        default=None,
        description="Source description for display in UI",
    )
    category_id: int | None = Field(
        default=None,
        foreign_key="newscategory.id",
        index=True,
        description="Category this source belongs to",
    )

    # Activation control
    is_active: bool = Field(
        default=True,
        index=True,
        description="Whether this source is enabled for fetching",
    )

    # Fetch scheduling (default for child sections)
    fetch_interval_minutes: int | None = Field(
        default=None,
        description="Default fetch interval for sections (inherits from category/global if None)",
    )

    add_date: datetime = Field(
        default_factory=_utc_now,
        description="When this source was added",
    )


class NewsSection(SQLModel, table=True):
    """A section within a news source.

    Sections represent specific pages/feeds within a source (e.g., "Monetary policy
    decisions", "Press releases"). Each section has its own URL and can be fetched
    independently.

    US-5.9: New model to support hierarchical news structure.
    US-5.13: Includes section-level fetch status tracking.
    """

    __tablename__ = "newssection"

    id: int | None = Field(default=None, primary_key=True)
    source_id: int = Field(
        foreign_key="newssource.id",
        index=True,
        description="Parent source this section belongs to",
    )
    title: str = Field(description="Section title (e.g., 'Monetary policy decisions')")
    url: str = Field(unique=True, description="Section URL to fetch")

    # Parsing configuration
    parse_selector: str | None = Field(
        default=None,
        description="CSS selector or 'xpath:...' for entry extraction",
    )
    parse_comment: str | None = Field(
        default=None,
        description="Human-readable notes about how to parse this section",
    )

    # Activation control
    is_active: bool = Field(
        default=True,
        index=True,
        description="Whether this section is enabled for fetching",
    )

    # Fetch scheduling
    fetch_interval_minutes: int | None = Field(
        default=None,
        description="Override fetch interval (inherits from source/category/global if None)",
    )

    # Fetch status tracking (US-5.13)
    last_fetched_at: datetime | None = Field(
        default=None,
        description="Last successful fetch timestamp",
    )
    last_checked_at: datetime | None = Field(
        default=None,
        description="Last fetch attempt timestamp (success or failure)",
    )
    last_fetch_status: str | None = Field(
        default=None,
        description="Last fetch status: 'success' or 'error'",
    )
    last_fetch_error: str | None = Field(
        default=None,
        description="Error message from last failed fetch",
    )

    add_date: datetime = Field(
        default_factory=_utc_now,
        description="When this section was added",
    )


class NewsEntry(SQLModel, table=True):
    """A news entry discovered from a section.

    Entries are individual articles/items found on a section's page.
    Deduplicated by URL. Stores full content for in-app reading.

    US-5.10: content_full stores complete article text.
    Renamed from NewsArticle, source_id changed to section_id.
    """

    __tablename__ = "newsentry"

    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(
        foreign_key="newssection.id",
        index=True,
        description="Section this entry was found in",
    )
    title: str = Field(description="Entry headline/title")
    url: str = Field(unique=True, description="Entry URL (used for deduplication)")
    published_at: datetime | None = Field(
        default=None,
        description="Publication date (if parseable from source)",
    )
    discovered_at: datetime = Field(
        default_factory=_utc_now,
        index=True,
        description="When we first found this entry",
    )
    # US-5.10: Full content storage
    # Note: No index on content_full by design. TEXT columns use too much space
    # for B-tree indexes. If full-text search is needed in the future, use
    # PostgreSQL's GIN index with tsvector or an external search engine (e.g., MeiliSearch).
    content_full: str | None = Field(
        default=None,
        description="Complete article text content",
    )
    content_preview: str | None = Field(
        default=None,
        description="First 500 chars of content (computed from content_full)",
    )


class NewsFetchLog(SQLModel, table=True):
    """Log of news fetch operations.

    Tracks fetch attempts for monitoring and debugging.
    US-5.13: Added section_id for section-level tracking.
    """

    __tablename__ = "newsfetchlog"

    id: int | None = Field(default=None, primary_key=True)
    section_id: int = Field(
        foreign_key="newssection.id",
        index=True,
        description="Section that was fetched",
    )
    status: str = Field(description="Status: 'success' or 'error'")
    entries_found: int = Field(default=0, description="Total entries parsed")
    entries_new: int = Field(default=0, description="New entries added to DB")
    error_message: str | None = Field(
        default=None,
        description="Error details if fetch failed",
    )
    started_at: datetime = Field(
        default_factory=_utc_now,
        index=True,
        description="Fetch start time",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Fetch completion time",
    )
    duration_seconds: float | None = Field(
        default=None,
        description="Fetch duration in seconds",
    )
