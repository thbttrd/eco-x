"""User preference models for the client application.

These models store user-specific settings like language,
theme, and favorite datasets.
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class UserPreference(SQLModel, table=True):
    """User preferences stored locally.

    Stores user settings like language and theme preferences.
    """

    __tablename__ = "user_preferences"

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(unique=True, description="Preference key")
    value: str = Field(description="Preference value (JSON string for complex values)")
    updated_at: datetime = Field(default_factory=datetime.now)


class FavoriteDataset(SQLModel, table=True):
    """User's favorite datasets for quick access.

    Allows users to bookmark frequently accessed datasets.
    """

    __tablename__ = "favorite_datasets"

    id: int | None = Field(default=None, primary_key=True)
    source: str = Field(index=True, description="Data source code")
    dataset_code: str = Field(description="Dataset code")
    display_name: str | None = Field(default=None, description="Custom display name")
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        """Unique constraint on source + dataset_code."""

        # SQLModel doesn't support composite unique directly,
        # but we'll handle this in migrations
        pass


class SourceActivation(SQLModel, table=True):
    """Tracks which data sources are activated by the user.

    Activated sources appear in the Data Sources tab and are available
    as filter options in the Datasets tab. Deactivated sources are hidden.
    Sources not in this table are treated as activated by default.
    """

    __tablename__ = "source_activations"

    id: int | None = Field(default=None, primary_key=True)
    source_code: str = Field(unique=True, index=True, description="Data source code")
    activated: bool = Field(default=True, description="Whether source is active")
    updated_at: datetime = Field(default_factory=datetime.now)
