"""Eurostat-specific models and JSON-stat 2.0 parser.

This module provides models and parsers for Eurostat's JSON-stat 2.0 format,
which is used by the Eurostat REST API.
"""

from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# Eurostat special markers (indicate missing/provisional/confidential data)
EUROSTAT_MARKERS = frozenset({":", ":m", "p", "e", "b", "c", "d", "s", "n", "u"})


def parse_value(raw_value: Any) -> tuple[float | None, str | None]:
    """Parse a JSON-stat value, handling special markers and time strings.

    Eurostat JSON-stat data can contain:
    - Numeric values (int/float)
    - Special markers like ':m' (missing), 'p' (provisional), etc.
    - Time duration strings in HH:MM format (from time-use surveys)

    Args:
        raw_value: The raw value from JSON-stat data

    Returns:
        Tuple of (numeric_value, flag_to_append)
        - For normal values: (float_value, None)
        - For special markers: (None, marker)
        - For time strings HH:MM: (decimal_hours, None)
    """
    # Already numeric
    if isinstance(raw_value, (int, float)):
        return float(raw_value), None

    # String value - check for special markers and time strings
    if isinstance(raw_value, str):
        stripped = raw_value.strip()

        # Special marker (missing/provisional/etc.)
        if stripped in EUROSTAT_MARKERS or stripped.startswith(":"):
            return None, stripped

        # Time duration string HH:MM -> convert to decimal hours
        # Used in time-use survey datasets (tus_*)
        if ":" in stripped and len(stripped) <= 5:
            try:
                parts = stripped.split(":")
                if len(parts) == 2:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    return hours + minutes / 60.0, None
            except ValueError:
                pass

        # Try direct float conversion as fallback
        try:
            return float(stripped), None
        except ValueError:
            logger.warning("Unrecognized value format", value=stripped[:50])
            return None, f"unparseable:{stripped[:20]}"

    # None or other types
    return None, None


class JsonStatDimension(BaseModel):
    """Represents a dimension in JSON-stat format."""

    label: str
    category: dict[str, Any]


class JsonStatExtension(BaseModel):
    """Extension information in JSON-stat format."""

    pass


class JsonStatDataset(BaseModel):
    """JSON-stat 2.0 dataset structure.

    This model represents the structure of Eurostat API responses.
    """

    version: str = Field(description="JSON-stat version")
    class_: str = Field(alias="class", description="Class type (usually 'dataset')")
    label: str | None = Field(default=None, description="Dataset label")
    source: str | None = Field(default=None, description="Data source")
    updated: str | None = Field(default=None, description="Last update timestamp")
    id: list[str] = Field(description="Dimension IDs")
    size: list[int] = Field(description="Size of each dimension")
    dimension: dict[str, dict[str, Any]] = Field(description="Dimension metadata")
    value: dict[str, float | None] = Field(description="Data values (index -> value)")
    status: dict[str, str] | None = Field(default=None, description="Status flags")
    extension: dict[str, Any] | None = Field(default=None, description="Extensions")


class ParsedDataValue(BaseModel):
    """Parsed data value with all dimensions.

    This represents a single data point extracted from JSON-stat format.
    """

    geo: str
    time_period: str
    indicator: str
    value: float
    unit: str | None = None
    flags: str | None = None


def parse_jsonstat(data: dict[str, Any]) -> list[ParsedDataValue]:
    """Parse JSON-stat 2.0 format data into a list of data values.

    Args:
        data: JSON-stat formatted data from Eurostat API

    Returns:
        List of parsed data values

    Raises:
        ValueError: If data format is invalid
    """
    try:
        # Validate basic structure
        if "class" not in data or data["class"] != "dataset":
            raise ValueError("Invalid JSON-stat format: missing or invalid 'class' field")

        dimension_ids = data["id"]
        dimension_sizes = data["size"]
        dimensions = data["dimension"]
        values = data.get("value", {})
        status_flags = data.get("status", {})

        logger.debug(
            "Parsing JSON-stat data",
            dimensions=dimension_ids,
            sizes=dimension_sizes,
            value_count=len(values),
        )

        # Parse values
        parsed_values: list[ParsedDataValue] = []

        for idx_str, value in values.items():
            # Parse the value, handling special markers and time strings
            numeric_value, value_flag = parse_value(value)
            if numeric_value is None:
                continue  # Skip records without numeric values

            idx = int(idx_str)

            # Calculate dimension indices
            dim_indices = _get_dimension_indices(idx, dimension_sizes)

            # Extract dimension values
            dim_values = {}
            for i, dim_id in enumerate(dimension_ids):
                dim_idx = dim_indices[i]
                dim_category = dimensions[dim_id]["category"]

                # Get the category index list
                if "index" in dim_category:
                    # index is a dict mapping labels to indices
                    index_map = dim_category["index"]
                    # Reverse the mapping to get label by index
                    reverse_map = {v: k for k, v in index_map.items()}
                    dim_value = reverse_map.get(dim_idx, str(dim_idx))
                else:
                    # Fallback to using the index directly
                    dim_value = str(dim_idx)

                dim_values[dim_id.lower()] = dim_value

            # Get status flag if available and combine with value-derived flag
            flag = status_flags.get(idx_str)
            if value_flag:
                flag = f"{flag},{value_flag}" if flag else value_flag

            # Extract standard dimensions
            parsed_value = ParsedDataValue(
                geo=dim_values.get("geo", "UNKNOWN"),
                time_period=dim_values.get("time", "UNKNOWN"),
                indicator=dim_values.get(
                    "na_item", dim_values.get("coicop", dim_values.get("nace_r2", "UNKNOWN"))
                ),
                value=numeric_value,
                unit=dim_values.get("unit"),
                flags=flag,
            )

            parsed_values.append(parsed_value)

        logger.info("JSON-stat data parsed", total_values=len(parsed_values))

        return parsed_values

    except Exception as e:
        logger.error("Failed to parse JSON-stat data", error=str(e))
        raise ValueError(f"Failed to parse JSON-stat data: {e}") from e


def _get_dimension_indices(flat_index: int, sizes: list[int]) -> list[int]:
    """Convert a flat index to dimension indices.

    Args:
        flat_index: Flat index in the value array
        sizes: Size of each dimension

    Returns:
        List of indices for each dimension
    """
    indices = []
    remaining = flat_index

    for size in reversed(sizes):
        indices.append(remaining % size)
        remaining //= size

    return list(reversed(indices))


def jsonstat_to_dataframe(data: dict[str, Any]) -> Any:
    """Convert JSON-stat data to a pandas DataFrame.

    Args:
        data: JSON-stat formatted data

    Returns:
        pandas DataFrame with parsed data

    Raises:
        ImportError: If pandas is not installed
        ValueError: If data format is invalid
    """
    try:
        import pandas as pd  # type: ignore
    except ImportError as e:
        raise ImportError("pandas is required for DataFrame conversion") from e

    parsed_values = parse_jsonstat(data)

    # Convert to list of dictionaries
    records = [value.model_dump() for value in parsed_values]

    df = pd.DataFrame(records)

    logger.info("JSON-stat data converted to DataFrame", shape=df.shape)

    return df


def export_to_markdown(
    data: dict[str, Any], dataset_code: str, filters: dict[str, Any] | None = None
) -> str:
    """Export JSON-stat data to Markdown format.

    Args:
        data: JSON-stat formatted data
        dataset_code: Dataset code
        filters: Filters used for the query

    Returns:
        Markdown-formatted string
    """
    parsed_values = parse_jsonstat(data)

    # Build markdown
    md_lines = [
        f"# Dataset: {dataset_code}",
        "",
        f"**Source:** {data.get('source', 'Eurostat')}",
        f"**Updated:** {data.get('updated', 'N/A')}",
        f"**Records:** {len(parsed_values)}",
        "",
    ]

    if filters:
        md_lines.append("**Filters:**")
        for key, value in filters.items():
            md_lines.append(f"- {key}: {value}")
        md_lines.append("")

    # Add data table
    if parsed_values:
        md_lines.extend(
            [
                "## Data",
                "",
                "| Geo | Time Period | Indicator | Value | Unit | Flags |",
                "|-----|-------------|-----------|-------|------|-------|",
            ]
        )

        for val in parsed_values[:100]:  # Limit to first 100 rows
            md_lines.append(
                f"| {val.geo} | {val.time_period} | {val.indicator} | "
                f"{val.value:.2f} | {val.unit or ''} | {val.flags or ''} |"
            )

        if len(parsed_values) > 100:
            md_lines.append(f"\n*Showing first 100 of {len(parsed_values)} records*")

    return "\n".join(md_lines)
