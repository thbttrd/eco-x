"""Tests for Eurostat JSON-stat parser and models."""

import pytest

from ecox_platform.sources.eurostat.models import (
    EUROSTAT_MARKERS,
    ParsedDataValue,
    parse_jsonstat,
    parse_value,
)


class TestParseValue:
    """Tests for the parse_value helper function."""

    def test_parse_numeric_int(self) -> None:
        """Test parsing integer values."""
        value, flag = parse_value(42)
        assert value == 42.0
        assert flag is None

    def test_parse_numeric_float(self) -> None:
        """Test parsing float values."""
        value, flag = parse_value(3.14159)
        assert value == pytest.approx(3.14159)
        assert flag is None

    def test_parse_numeric_zero(self) -> None:
        """Test parsing zero value."""
        value, flag = parse_value(0)
        assert value == 0.0
        assert flag is None

    def test_parse_numeric_negative(self) -> None:
        """Test parsing negative values."""
        value, flag = parse_value(-100.5)
        assert value == pytest.approx(-100.5)
        assert flag is None

    def test_parse_none_value(self) -> None:
        """Test parsing None returns None."""
        value, flag = parse_value(None)
        assert value is None
        assert flag is None

    def test_parse_string_numeric(self) -> None:
        """Test parsing numeric strings."""
        value, flag = parse_value("12345.67")
        assert value == pytest.approx(12345.67)
        assert flag is None

    def test_parse_string_with_whitespace(self) -> None:
        """Test parsing numeric strings with whitespace."""
        value, flag = parse_value("  100.5  ")
        assert value == pytest.approx(100.5)
        assert flag is None

    # Special markers tests
    @pytest.mark.parametrize("marker", list(EUROSTAT_MARKERS))
    def test_parse_special_markers(self, marker: str) -> None:
        """Test that all known special markers are handled correctly."""
        value, flag = parse_value(marker)
        assert value is None
        assert flag == marker

    def test_parse_colon_m_missing(self) -> None:
        """Test parsing :m (missing) marker."""
        value, flag = parse_value(":m")
        assert value is None
        assert flag == ":m"

    def test_parse_colon_marker(self) -> None:
        """Test parsing : marker (not available)."""
        value, flag = parse_value(":")
        assert value is None
        assert flag == ":"

    def test_parse_marker_with_colon_prefix(self) -> None:
        """Test parsing unknown markers starting with colon."""
        value, flag = parse_value(":unknown")
        assert value is None
        assert flag == ":unknown"

    # Time duration tests (HH:MM format)
    def test_parse_time_duration_simple(self) -> None:
        """Test parsing HH:MM time duration to decimal hours."""
        value, flag = parse_value("11:37")
        assert value == pytest.approx(11 + 37 / 60.0)  # 11.6167
        assert flag is None

    def test_parse_time_duration_zero_minutes(self) -> None:
        """Test parsing time duration with zero minutes."""
        value, flag = parse_value("8:00")
        assert value == pytest.approx(8.0)
        assert flag is None

    def test_parse_time_duration_full_hour(self) -> None:
        """Test parsing time duration like 10:00."""
        value, flag = parse_value("10:00")
        assert value == pytest.approx(10.0)
        assert flag is None

    def test_parse_time_duration_half_hour(self) -> None:
        """Test parsing time duration with 30 minutes."""
        value, flag = parse_value("5:30")
        assert value == pytest.approx(5.5)
        assert flag is None

    def test_parse_time_duration_padded(self) -> None:
        """Test parsing time duration with zero-padded values."""
        value, flag = parse_value("08:05")
        assert value == pytest.approx(8 + 5 / 60.0)
        assert flag is None

    # Unparseable values
    def test_parse_unparseable_string(self) -> None:
        """Test parsing unparseable string values."""
        value, flag = parse_value("not_a_number")
        assert value is None
        assert flag is not None
        assert flag.startswith("unparseable:")


class TestParseJsonstat:
    """Tests for the parse_jsonstat function."""

    @pytest.fixture
    def sample_jsonstat_data(self) -> dict:
        """Create sample JSON-stat data for testing."""
        return {
            "class": "dataset",
            "version": "2.0",
            "label": "Test Dataset",
            "source": "Eurostat",
            "updated": "2024-01-15",
            "id": ["geo", "time", "na_item"],
            "size": [2, 2, 1],
            "dimension": {
                "geo": {
                    "label": "Geographic area",
                    "category": {
                        "index": {"DE": 0, "FR": 1},
                        "label": {"DE": "Germany", "FR": "France"},
                    },
                },
                "time": {
                    "label": "Time",
                    "category": {
                        "index": {"2022": 0, "2023": 1},
                        "label": {"2022": "2022", "2023": "2023"},
                    },
                },
                "na_item": {
                    "label": "National accounts item",
                    "category": {"index": {"B1GQ": 0}, "label": {"B1GQ": "GDP"}},
                },
            },
            "value": {
                "0": 3800000.0,  # DE, 2022, B1GQ
                "1": 3900000.0,  # DE, 2023, B1GQ
                "2": 2600000.0,  # FR, 2022, B1GQ
                "3": 2700000.0,  # FR, 2023, B1GQ
            },
            "status": {},
        }

    def test_parse_valid_jsonstat(self, sample_jsonstat_data: dict) -> None:
        """Test parsing valid JSON-stat data."""
        result = parse_jsonstat(sample_jsonstat_data)

        assert len(result) == 4
        assert all(isinstance(v, ParsedDataValue) for v in result)

    def test_parse_extracts_correct_values(self, sample_jsonstat_data: dict) -> None:
        """Test that values are extracted correctly."""
        result = parse_jsonstat(sample_jsonstat_data)

        values = {(v.geo, v.time_period): v.value for v in result}
        assert values[("DE", "2022")] == pytest.approx(3800000.0)
        assert values[("DE", "2023")] == pytest.approx(3900000.0)
        assert values[("FR", "2022")] == pytest.approx(2600000.0)
        assert values[("FR", "2023")] == pytest.approx(2700000.0)

    def test_parse_skips_special_markers(self, sample_jsonstat_data: dict) -> None:
        """Test that special markers are skipped."""
        data = sample_jsonstat_data.copy()
        data["value"] = {
            "0": 3800000.0,
            "1": ":m",  # Missing value - should be skipped
            "2": 2600000.0,
            "3": ":",  # Not available - should be skipped
        }

        result = parse_jsonstat(data)

        # Only 2 records with numeric values
        assert len(result) == 2
        geos = [v.geo for v in result]
        assert "DE" in geos
        assert "FR" in geos

    def test_parse_handles_time_duration_values(self, sample_jsonstat_data: dict) -> None:
        """Test that HH:MM time duration values are converted to decimal hours."""
        data = sample_jsonstat_data.copy()
        data["value"] = {
            "0": "8:30",  # 8.5 hours
            "1": "10:15",  # 10.25 hours
            "2": "6:00",  # 6.0 hours
            "3": "7:45",  # 7.75 hours
        }

        result = parse_jsonstat(data)

        assert len(result) == 4
        values = {(v.geo, v.time_period): v.value for v in result}
        assert values[("DE", "2022")] == pytest.approx(8.5)
        assert values[("DE", "2023")] == pytest.approx(10.25)
        assert values[("FR", "2022")] == pytest.approx(6.0)
        assert values[("FR", "2023")] == pytest.approx(7.75)

    def test_parse_preserves_status_flags(self, sample_jsonstat_data: dict) -> None:
        """Test that status flags are preserved."""
        data = sample_jsonstat_data.copy()
        data["status"] = {"0": "p", "2": "e"}  # provisional, estimated

        result = parse_jsonstat(data)

        flags_map = {(v.geo, v.time_period): v.flags for v in result}
        assert flags_map[("DE", "2022")] == "p"
        assert flags_map[("DE", "2023")] is None
        assert flags_map[("FR", "2022")] == "e"
        assert flags_map[("FR", "2023")] is None

    def test_parse_skips_none_values(self, sample_jsonstat_data: dict) -> None:
        """Test that None values are skipped."""
        data = sample_jsonstat_data.copy()
        data["value"] = {
            "0": 3800000.0,
            "1": None,  # Should be skipped
            "2": 2600000.0,
            "3": None,  # Should be skipped
        }

        result = parse_jsonstat(data)

        assert len(result) == 2

    def test_parse_invalid_class_raises(self) -> None:
        """Test that invalid class field raises ValueError."""
        invalid_data = {"class": "not_dataset", "version": "2.0"}

        with pytest.raises(ValueError, match="Invalid JSON-stat format"):
            parse_jsonstat(invalid_data)

    def test_parse_missing_class_raises(self) -> None:
        """Test that missing class field raises ValueError."""
        invalid_data = {"version": "2.0"}

        with pytest.raises(ValueError, match="Invalid JSON-stat format"):
            parse_jsonstat(invalid_data)
