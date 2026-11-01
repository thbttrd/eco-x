"""OECD API response models.

Pydantic models for parsing OECD SDMX-JSON API responses.
The OECD uses the SDMX 2.1 standard with JSON format.
"""

from typing import Any

from pydantic import BaseModel, Field, model_validator

# === Dataflow/Structure Models ===


class OecdDataflow(BaseModel):
    """Dataflow definition from structure response.

    A dataflow represents a dataset in OECD's SDMX terminology.
    """

    model_config = {"populate_by_name": True}

    id: str
    agencyID: str = Field(alias="agencyID")
    version: str
    name: str | None = None
    description: str | None = None
    structure: dict[str, Any] | None = None


class OecdDataflowsData(BaseModel):
    """Data section of dataflows response."""

    dataflows: list[OecdDataflow] = []


class OecdDataflowsResponse(BaseModel):
    """Response from /dataflow endpoint.

    Contains the list of all available dataflows (datasets).
    """

    meta: dict[str, Any] | None = None
    data: OecdDataflowsData


# === Data Response Models ===


class OecdDimensionValue(BaseModel):
    """A value in a dimension's values array.

    Handles both standard 'id' field and alternative 'value' field
    used by some OECD datasets (e.g., regional datasets with TL2/TL3 codes).
    """

    id: str = ""  # Populated from 'value' if not present
    name: str | None = None
    order: int | None = None

    @model_validator(mode="before")
    @classmethod
    def handle_value_field(cls, data: Any) -> Any:
        """Handle 'value' as alternative to 'id' field.

        Some OECD datasets return dimension values with 'value' instead of 'id'.
        This validator normalizes the input to always have 'id'.
        """
        if isinstance(data, dict):
            if "id" not in data and "value" in data:
                data["id"] = data["value"]
        return data


class OecdSeriesDimension(BaseModel):
    """Series dimension in data response structure."""

    id: str
    name: str | None = None
    keyPosition: int | None = None
    values: list[OecdDimensionValue] = []


class OecdObservationDimension(BaseModel):
    """Observation dimension (typically TIME_PERIOD) in data response."""

    id: str
    name: str | None = None
    values: list[OecdDimensionValue] = []


class OecdAttributeValue(BaseModel):
    """Attribute value in structure."""

    id: str | None = None
    name: str | None = None


class OecdStructureAttribute(BaseModel):
    """Attribute definition in structure."""

    id: str
    name: str | None = None
    values: list[OecdAttributeValue] = []
    relationship: dict[str, Any] | None = None


class OecdDimensions(BaseModel):
    """Dimensions section in structure."""

    series: list[OecdSeriesDimension] = []
    observation: list[OecdObservationDimension] = []


class OecdAttributes(BaseModel):
    """Attributes section in structure."""

    series: list[OecdStructureAttribute] = []
    observation: list[OecdStructureAttribute] = []


class OecdDataStructure(BaseModel):
    """Structure metadata in data response."""

    name: str | None = None
    description: str | None = None
    dimensions: OecdDimensions | None = None
    attributes: OecdAttributes | None = None


class OecdDataSet(BaseModel):
    """DataSet section containing series and observations."""

    action: str | None = None
    series: dict[str, dict[str, Any]] = {}


class OecdDataData(BaseModel):
    """Data section of the data response."""

    structures: list[OecdDataStructure] = []
    dataSets: list[OecdDataSet] = []


class OecdDataResponse(BaseModel):
    """Response from /data endpoint.

    Contains actual observations grouped by series.
    """

    meta: dict[str, Any] | None = None
    data: OecdDataData

    def get_structure(self) -> OecdDataStructure | None:
        """Get the first (usually only) structure from the response."""
        if self.data.structures:
            return self.data.structures[0]
        return None

    def get_dataset(self) -> OecdDataSet | None:
        """Get the first (usually only) dataset from the response."""
        if self.data.dataSets:
            return self.data.dataSets[0]
        return None


# === Simplified dataset metadata for TOC ===


class OecdDatasetInfo(BaseModel):
    """Simplified dataset information for table of contents.

    Extracted from dataflow listing for easier processing.
    """

    code: str  # Full dataflow ID: agencyID,id,version
    agency_id: str
    dataflow_id: str
    version: str
    name: str | None = None
    description: str | None = None

    @classmethod
    def from_dataflow(cls, df: OecdDataflow) -> "OecdDatasetInfo":
        """Create from OecdDataflow."""
        # Full code includes agency, id, and version
        code = f"{df.agencyID},{df.id},{df.version}"
        return cls(
            code=code,
            agency_id=df.agencyID,
            dataflow_id=df.id,
            version=df.version,
            name=df.name,
            description=df.description,
        )
