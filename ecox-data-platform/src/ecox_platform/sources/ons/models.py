"""ONS API data models.

This module provides Pydantic models for parsing responses from the
UK Office for National Statistics (ONS) API.
"""

from pydantic import BaseModel, Field


class OnsDatasetLinks(BaseModel):
    """Links within a dataset response."""

    editions: dict[str, str] | None = None
    latest_version: dict[str, str] | None = None
    self_link: dict[str, str] | None = Field(default=None, alias="self")
    taxonomy: dict[str, str] | None = None


class OnsDataset(BaseModel):
    """Metadata for an ONS dataset from /datasets endpoint."""

    id: str
    title: str
    description: str | None = None
    keywords: list[str] | None = None
    links: OnsDatasetLinks | None = None
    national_statistic: bool | None = None
    next_release: str | None = None
    release_frequency: str | None = None
    state: str | None = None
    unit_of_measure: str | None = None
    last_updated: str | None = None


class OnsDatasetsResponse(BaseModel):
    """Response structure for ONS /datasets endpoint."""

    items: list[OnsDataset]
    count: int
    offset: int
    limit: int
    total_count: int


class OnsDimension(BaseModel):
    """Dimension metadata within a dataset version."""

    name: str
    label: str | None = None
    description: str | None = None
    href: str | None = None
    id: str | None = None


class OnsVersionLinks(BaseModel):
    """Links within a dataset version response."""

    dataset: dict[str, str] | None = None
    edition: dict[str, str] | None = None
    self_link: dict[str, str] | None = Field(default=None, alias="self")


class OnsDatasetVersion(BaseModel):
    """Dataset version metadata from /datasets/{id}/editions/{edition}/versions/{version}."""

    id: str | None = None
    edition: str
    version: int
    dimensions: list[OnsDimension] | None = None
    downloads: dict[str, dict[str, str]] | None = None
    last_updated: str | None = None
    release_date: str | None = None
    state: str | None = None
    links: OnsVersionLinks | None = None
    unit_of_measure: str | None = None


class OnsEdition(BaseModel):
    """Edition metadata."""

    edition: str
    id: str | None = None
    links: dict[str, dict[str, str]] | None = None
    state: str | None = None


class OnsEditionsResponse(BaseModel):
    """Response for /datasets/{id}/editions endpoint."""

    items: list[OnsEdition]
    count: int
    offset: int
    limit: int
    total_count: int


class OnsDimensionOption(BaseModel):
    """A dimension option (selectable value)."""

    option: str
    label: str | None = None
    dimension: str | None = None


class OnsDimensionOptionsResponse(BaseModel):
    """Response for dimension options endpoint."""

    items: list[OnsDimensionOption]
    count: int
    offset: int
    limit: int
    total_count: int


class OnsObservationDimension(BaseModel):
    """Dimension value within an observation."""

    id: str
    label: str | None = None
    href: str | None = None


class OnsObservation(BaseModel):
    """A single observation from the observations endpoint."""

    observation: str  # Value as string
    dimensions: dict[str, OnsObservationDimension] | None = None


class OnsObservationsResponse(BaseModel):
    """Response structure for ONS observations endpoint."""

    observations: list[OnsObservation] | None = None
    dimensions: dict[str, dict[str, OnsObservationDimension]] | None = None
    limit: int | None = None
    offset: int | None = None
    total_observations: int | None = None
    unit_of_measure: str | None = None
    links: dict[str, dict[str, str]] | None = None
