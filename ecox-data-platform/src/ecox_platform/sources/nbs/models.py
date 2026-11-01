"""Pydantic models for NBS China API responses.

The NBS API uses a custom JSON format with nested structures for
hierarchical data organization. Key concepts:
- dbcode: Database code (hgnd=annual, hgyd=monthly, fsnd=regional)
- wdcode: Dimension code (zb=indicator, sj=time)
- valuecode: Value within a dimension
"""

from pydantic import BaseModel, Field


class NbsTreeNode(BaseModel):
    """A node in the NBS indicator tree (TOC).

    The tree is hierarchical with categories containing sub-categories
    and leaf nodes representing actual datasets/indicators.
    """

    id: str = Field(..., description="Node ID (e.g., 'A02' for National Accounts)")
    name: str = Field(..., description="Display name in English")
    dbcode: str = Field(..., description="Database code (hgnd, hgyd, etc.)")
    wdcode: str = Field(..., description="Dimension code (usually 'zb' for indicator)")
    pid: str = Field(default="", description="Parent node ID (empty for root)")
    isParent: bool = Field(default=False, description="True if node has children")


class NbsDataPoint(BaseModel):
    """A single data observation from QueryData response."""

    data: float | None = Field(None, description="Numeric value")
    hasdata: bool = Field(default=True, description="Whether data is available")
    strdata: str = Field(default="", description="String representation of value")
    dotcount: int = Field(default=0, description="Decimal places")


class NbsDimension(BaseModel):
    """A dimension value (time period or indicator code)."""

    wdcode: str = Field(..., description="Dimension type (zb=indicator, sj=time)")
    valuecode: str = Field(..., description="Value code (e.g., '2024', 'A020102')")


class NbsDataNode(BaseModel):
    """A data node containing observation value and dimension info."""

    code: str = Field(..., description="Composite code (e.g., 'zb.A020102_sj.2024')")
    data: NbsDataPoint = Field(..., description="The observation data")
    wds: list[NbsDimension] = Field(default_factory=list, description="Dimension values")


class NbsIndicatorMeta(BaseModel):
    """Metadata for an indicator from wdnodes."""

    code: str = Field(..., description="Indicator code (e.g., 'A020102')")
    name: str = Field(..., description="English name")
    cname: str = Field(default="", description="Chinese name")
    unit: str = Field(default="", description="Unit of measurement")
    exp: str = Field(default="", description="Explanation/description")
    dotcount: int = Field(default=0, description="Decimal places")
    memo: str = Field(default="", description="Additional notes")


class NbsTimePeriodMeta(BaseModel):
    """Metadata for a time period from wdnodes."""

    code: str = Field(..., description="Time period code (e.g., '2024')")
    name: str = Field(..., description="Display name")


class NbsWdNode(BaseModel):
    """A dimension node containing metadata for all values in that dimension."""

    wdcode: str = Field(..., description="Dimension code (zb or sj)")
    wdname: str = Field(..., description="Dimension name (Indicators or Year)")
    nodes: list[NbsIndicatorMeta | NbsTimePeriodMeta] = Field(
        default_factory=list, description="Metadata for each value"
    )


class NbsReturnData(BaseModel):
    """The returndata section of QueryData response."""

    datanodes: list[NbsDataNode] = Field(default_factory=list, description="Data observations")
    wdnodes: list[NbsWdNode] = Field(default_factory=list, description="Dimension metadata")
    hasdatacount: int = Field(default=0, description="Number of data points with values")
    freshsort: int = Field(default=0, description="Sort order indicator")


class NbsQueryDataResponse(BaseModel):
    """Response from QueryData endpoint."""

    returncode: int = Field(..., description="Return code (200 = success)")
    returndata: NbsReturnData = Field(..., description="The actual data")

    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return self.returncode == 200

    def get_indicator_metadata(self) -> dict[str, NbsIndicatorMeta]:
        """Extract indicator metadata as a dictionary keyed by code.

        After Pydantic validation, nodes are typed model instances.
        Only NbsIndicatorMeta nodes (from 'zb' dimension) are extracted.
        """
        result: dict[str, NbsIndicatorMeta] = {}
        for wdnode in self.returndata.wdnodes:
            if wdnode.wdcode == "zb":  # Indicator dimension
                for node in wdnode.nodes:
                    if isinstance(node, NbsIndicatorMeta):
                        result[node.code] = node
        return result
