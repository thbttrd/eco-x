"""Unit tests for OECD service layer.

Tests cover:
- SDMX-JSON data transformation
- Dimension extraction (geo, measure, unit, freq)
- Observation status flag handling
- Fallback to raw dict parsing
- Edge cases and error handling
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ecox_platform.sources.oecd.service import OecdService


@pytest.fixture
def mock_repository() -> MagicMock:
    """Create a mock OECD repository."""
    repo = MagicMock()
    repo.get_dataset = AsyncMock()
    repo.get_dataset_metadata = AsyncMock(return_value={})
    repo.fetch_toc = AsyncMock(return_value=[])
    repo.close = AsyncMock()
    return repo


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a mock cache."""
    cache = MagicMock()
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock()
    return cache


@pytest.fixture
def oecd_service(mock_repository: MagicMock, mock_cache: MagicMock) -> OecdService:
    """Create OECD service with mocked dependencies."""
    service = OecdService(repository=mock_repository, cache=mock_cache)
    return service


class TestTransformSdmxData:
    """Tests for _transform_sdmx_data method."""

    def test_transforms_basic_series(
        self,
        oecd_service: OecdService,
        sample_oecd_data_response: dict,
    ) -> None:
        """Test basic SDMX data transformation."""
        result = oecd_service._transform_sdmx_data(
            sample_oecd_data_response, "OECD.SDD.STES,DSD_KEI@DF_KEI,4.0"
        )

        # Should have data from 3 countries * 4 time periods = 12 records
        assert len(result) == 12

        # Check first record (USA, 2020)
        usa_2020 = next(r for r in result if r["geo"] == "USA" and r["time_period"] == "2020")
        assert usa_2020["value"] == -2.2
        assert usa_2020["indicator"] == "GDP_A"  # MEASURE_FREQ pattern
        assert usa_2020["unit"] == "GR"
        assert usa_2020["flags"] == "A"  # Normal status

    def test_extracts_geo_dimension(
        self,
        oecd_service: OecdService,
        sample_oecd_data_response: dict,
    ) -> None:
        """Test that REF_AREA is extracted as geo."""
        result = oecd_service._transform_sdmx_data(sample_oecd_data_response, "test")

        geos = {r["geo"] for r in result}
        assert geos == {"USA", "FRA", "DEU"}

    def test_extracts_time_periods(
        self,
        oecd_service: OecdService,
        sample_oecd_data_response: dict,
    ) -> None:
        """Test that TIME_PERIOD observation dimension is extracted."""
        result = oecd_service._transform_sdmx_data(sample_oecd_data_response, "test")

        time_periods = {r["time_period"] for r in result}
        assert time_periods == {"2020", "2021", "2022", "2023"}

    def test_builds_indicator_from_measure_and_freq(
        self,
        oecd_service: OecdService,
        sample_oecd_data_response: dict,
    ) -> None:
        """Test indicator is built as MEASURE_FREQ."""
        result = oecd_service._transform_sdmx_data(sample_oecd_data_response, "test")

        # All records should have GDP_A indicator (GDP + Annual)
        indicators = {r["indicator"] for r in result}
        assert "GDP_A" in indicators

    def test_handles_observation_status_flags(
        self,
        oecd_service: OecdService,
        sample_oecd_data_response: dict,
    ) -> None:
        """Test OBS_STATUS attribute is captured as flags."""
        result = oecd_service._transform_sdmx_data(sample_oecd_data_response, "test")

        # USA 2023 should have "E" (estimated) flag
        usa_2023 = next(r for r in result if r["geo"] == "USA" and r["time_period"] == "2023")
        assert usa_2023["flags"] == "E"

        # FRA 2023 should have "P" (provisional) flag
        fra_2023 = next(r for r in result if r["geo"] == "FRA" and r["time_period"] == "2023")
        assert fra_2023["flags"] == "P"

    def test_handles_empty_dataset(
        self,
        oecd_service: OecdService,
        sample_oecd_empty_data_response: dict,
    ) -> None:
        """Test transformation of empty dataset."""
        result = oecd_service._transform_sdmx_data(sample_oecd_empty_data_response, "test")

        assert result == []

    def test_handles_quarterly_data(
        self,
        oecd_service: OecdService,
        sample_oecd_quarterly_data_response: dict,
    ) -> None:
        """Test transformation with quarterly time periods."""
        result = oecd_service._transform_sdmx_data(sample_oecd_quarterly_data_response, "test")

        assert len(result) == 4
        time_periods = {r["time_period"] for r in result}
        assert time_periods == {"2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4"}

        # Check indicator includes quarterly freq
        indicators = {r["indicator"] for r in result}
        assert "GDP_Q" in indicators

    def test_skips_null_values(
        self,
        oecd_service: OecdService,
    ) -> None:
        """Test that null observation values are skipped."""
        data = {
            "data": {
                "structures": [
                    {
                        "dimensions": {
                            "series": [
                                {"id": "REF_AREA", "values": [{"id": "USA"}]},
                                {"id": "FREQ", "values": [{"id": "A"}]},
                            ],
                            "observation": [
                                {"id": "TIME_PERIOD", "values": [{"id": "2020"}, {"id": "2021"}]}
                            ],
                        },
                        "attributes": {"series": [], "observation": []},
                    }
                ],
                "dataSets": [
                    {
                        "series": {
                            "0:0": {
                                "observations": {
                                    "0": [None],  # Null value
                                    "1": [100.5],  # Valid value
                                }
                            }
                        }
                    }
                ],
            }
        }

        result = oecd_service._transform_sdmx_data(data, "test")

        # Should only have 1 record (null skipped)
        assert len(result) == 1
        assert result[0]["value"] == 100.5

    def test_defaults_geo_to_oecd_when_missing(
        self,
        oecd_service: OecdService,
    ) -> None:
        """Test that geo defaults to 'OECD' when REF_AREA is not in dimensions."""
        data = {
            "data": {
                "structures": [
                    {
                        "dimensions": {
                            "series": [
                                {"id": "MEASURE", "values": [{"id": "GDP"}]},
                            ],
                            "observation": [{"id": "TIME_PERIOD", "values": [{"id": "2020"}]}],
                        },
                        "attributes": {"series": [], "observation": []},
                    }
                ],
                "dataSets": [{"series": {"0": {"observations": {"0": [100.0]}}}}],
            }
        }

        result = oecd_service._transform_sdmx_data(data, "test")

        assert len(result) == 1
        assert result[0]["geo"] == "OECD"


class TestTransformSdmxDataRaw:
    """Tests for _transform_sdmx_data_raw fallback method."""

    def test_fallback_handles_raw_dict_format(
        self,
        oecd_service: OecdService,
    ) -> None:
        """Test raw dict transformation when Pydantic parsing fails."""
        # This is the raw dict format (not using Pydantic models)
        data = {
            "data": {
                "structures": [
                    {
                        "dimensions": {
                            "series": [
                                {"id": "REF_AREA", "values": [{"id": "USA"}]},
                                {"id": "FREQ", "values": [{"id": "A"}]},
                                {"id": "MEASURE", "values": [{"id": "GDP"}]},
                            ],
                            "observation": [{"id": "TIME_PERIOD", "values": [{"id": "2020"}]}],
                        },
                    }
                ],
                "dataSets": [{"series": {"0:0:0": {"observations": {"0": [123.4]}}}}],
            }
        }

        result = oecd_service._transform_sdmx_data_raw(data, "test")

        assert len(result) == 1
        assert result[0]["geo"] == "USA"
        assert result[0]["time_period"] == "2020"
        assert result[0]["value"] == 123.4
        assert result[0]["indicator"] == "GDP_A"

    def test_fallback_returns_empty_on_missing_data(
        self,
        oecd_service: OecdService,
    ) -> None:
        """Test raw fallback returns empty list on invalid structure."""
        result = oecd_service._transform_sdmx_data_raw({}, "test")
        assert result == []

        result = oecd_service._transform_sdmx_data_raw({"data": {}}, "test")
        assert result == []


class TestTransformEdgeCases:
    """Edge case tests for SDMX transformation."""

    def test_handles_malformed_series_key_gracefully(
        self,
        oecd_service: OecdService,
    ) -> None:
        """Test that malformed series keys don't crash transformation."""
        data = {
            "data": {
                "structures": [
                    {
                        "dimensions": {
                            "series": [{"id": "REF_AREA", "values": [{"id": "USA"}]}],
                            "observation": [{"id": "TIME_PERIOD", "values": [{"id": "2020"}]}],
                        },
                        "attributes": {"series": [], "observation": []},
                    }
                ],
                "dataSets": [
                    {
                        "series": {
                            "0": {"observations": {"0": [100.0]}},  # Valid
                            "invalid:key:format": {
                                "observations": {"0": [200.0]}
                            },  # May cause issues
                        }
                    }
                ],
            }
        }

        # Should not raise exception
        result = oecd_service._transform_sdmx_data(data, "test")
        # Should have at least the valid record
        assert len(result) >= 1

    def test_handles_missing_structure(
        self,
        oecd_service: OecdService,
    ) -> None:
        """Test handling when structure is missing."""
        data = {
            "data": {
                "structures": [],
                "dataSets": [{"series": {"0": {"observations": {"0": [100]}}}}],
            }
        }

        result = oecd_service._transform_sdmx_data(data, "test")
        assert result == []

    def test_handles_missing_dataset(
        self,
        oecd_service: OecdService,
    ) -> None:
        """Test handling when dataset is missing."""
        data = {
            "data": {
                "structures": [{"dimensions": {"series": [], "observation": []}}],
                "dataSets": [],
            }
        }

        result = oecd_service._transform_sdmx_data(data, "test")
        assert result == []
