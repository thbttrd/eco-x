"""Unit tests for OECD Pydantic models.

Tests cover:
- OecdDimensionValue handling of 'id' and 'value' fields
- Model validation and normalization
"""

from ecox_platform.sources.oecd.models import (
    OecdDataflow,
    OecdDimensionValue,
    OecdSeriesDimension,
)


class TestOecdDimensionValue:
    """Tests for OecdDimensionValue model."""

    def test_parse_with_id_field(self) -> None:
        """Test parsing dimension value with standard 'id' field."""
        value = OecdDimensionValue(id="FRA", name="France")

        assert value.id == "FRA"
        assert value.name == "France"

    def test_parse_with_value_field_instead_of_id(self) -> None:
        """Test parsing dimension value with 'value' field (alternative format).

        Some OECD datasets (e.g., regional data with TL2/TL3 codes) return
        'value' instead of 'id'. The model should handle this gracefully.
        """
        data = {"value": "FRA08001", "name": "Some Region"}
        value = OecdDimensionValue(**data)

        assert value.id == "FRA08001"
        assert value.name == "Some Region"

    def test_parse_with_value_only(self) -> None:
        """Test parsing dimension value with only 'value' field."""
        data = {"value": "USA"}
        value = OecdDimensionValue(**data)

        assert value.id == "USA"
        assert value.name is None

    def test_id_takes_precedence_over_value(self) -> None:
        """Test that 'id' takes precedence when both fields are present."""
        data = {"id": "DEU", "value": "DEU00001", "name": "Germany"}
        value = OecdDimensionValue(**data)

        assert value.id == "DEU"
        assert value.name == "Germany"

    def test_parse_with_order_field(self) -> None:
        """Test parsing dimension value with optional 'order' field."""
        value = OecdDimensionValue(id="GBR", name="United Kingdom", order=5)

        assert value.id == "GBR"
        assert value.order == 5

    def test_empty_id_allowed(self) -> None:
        """Test that empty 'id' string is allowed (default value)."""
        # This should not raise - empty string is the default
        value = OecdDimensionValue()
        assert value.id == ""

    def test_parse_from_dict(self) -> None:
        """Test parsing from dictionary (common SDMX-JSON format)."""
        raw_data = [
            {"id": "USA", "name": "United States"},
            {"id": "FRA", "name": "France"},
            {"id": "DEU", "name": "Germany"},
        ]

        values = [OecdDimensionValue(**d) for d in raw_data]

        assert len(values) == 3
        assert values[0].id == "USA"
        assert values[1].id == "FRA"
        assert values[2].id == "DEU"

    def test_parse_mixed_formats(self) -> None:
        """Test parsing a mix of 'id' and 'value' formats."""
        raw_data = [
            {"id": "USA", "name": "United States"},
            {"value": "FRA08001"},  # Alternative format
            {"id": "DEU", "value": "ignored", "name": "Germany"},
        ]

        values = [OecdDimensionValue(**d) for d in raw_data]

        assert values[0].id == "USA"
        assert values[1].id == "FRA08001"
        assert values[2].id == "DEU"  # 'id' takes precedence


class TestOecdSeriesDimension:
    """Tests for OecdSeriesDimension with nested OecdDimensionValue."""

    def test_parse_with_values_using_id(self) -> None:
        """Test parsing series dimension with standard 'id' format values."""
        data = {
            "id": "REF_AREA",
            "name": "Reference Area",
            "keyPosition": 0,
            "values": [
                {"id": "USA", "name": "United States"},
                {"id": "FRA", "name": "France"},
            ],
        }

        dim = OecdSeriesDimension(**data)

        assert dim.id == "REF_AREA"
        assert len(dim.values) == 2
        assert dim.values[0].id == "USA"
        assert dim.values[1].id == "FRA"

    def test_parse_with_values_using_value_field(self) -> None:
        """Test parsing series dimension with 'value' format (alternative)."""
        data = {
            "id": "REF_AREA",
            "values": [
                {"value": "FRA08001"},
                {"value": "DEU00001"},
            ],
        }

        dim = OecdSeriesDimension(**data)

        assert len(dim.values) == 2
        assert dim.values[0].id == "FRA08001"
        assert dim.values[1].id == "DEU00001"


class TestOecdDataflow:
    """Tests for OecdDataflow model."""

    def test_parse_dataflow(self) -> None:
        """Test parsing a dataflow definition."""
        data = {
            "id": "DSD_KEI@DF_KEI",
            "agencyID": "OECD.SDD.STES",
            "version": "4.0",
            "name": "Key Short-Term Economic Indicators",
        }

        df = OecdDataflow(**data)

        assert df.id == "DSD_KEI@DF_KEI"
        assert df.agencyID == "OECD.SDD.STES"
        assert df.version == "4.0"
        assert df.name == "Key Short-Term Economic Indicators"

    def test_parse_dataflow_minimal(self) -> None:
        """Test parsing dataflow with only required fields."""
        data = {
            "id": "DF_TEST",
            "agencyID": "OECD",
            "version": "1.0",
        }

        df = OecdDataflow(**data)

        assert df.id == "DF_TEST"
        assert df.name is None
        assert df.description is None
