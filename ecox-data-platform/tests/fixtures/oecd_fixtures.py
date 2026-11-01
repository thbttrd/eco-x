"""OECD API response fixtures for testing.

Provides sample responses matching the OECD SDMX 2.1 API format.
"""

import pytest


@pytest.fixture
def sample_oecd_dataflows_response() -> dict:
    """Sample response from /dataflow endpoint."""
    return {
        "meta": {"id": "IDREF1234", "prepared": "2025-01-01T00:00:00Z"},
        "data": {
            "dataflows": [
                {
                    "id": "DSD_KEI@DF_KEI",
                    "agencyID": "OECD.SDD.STES",
                    "version": "4.0",
                    "name": "Key Short-Term Economic Indicators",
                    "description": "Main economic indicators for OECD countries",
                },
                {
                    "id": "DSD_NAMAIN1@DF_QNA_EXPENDITURE",
                    "agencyID": "OECD.SDD.NAD",
                    "version": "1.0",
                    "name": "Quarterly National Accounts - Expenditure",
                    "description": "Quarterly GDP expenditure data",
                },
                {
                    "id": "DSD_REG_ECO@DF_GDP",
                    "agencyID": "OECD.CFE.EDS",
                    "version": "2.4",
                    "name": "Regional GDP",
                    "description": "GDP by region",
                },
            ]
        },
    }


@pytest.fixture
def sample_oecd_data_response() -> dict:
    """Sample response from /data endpoint with SDMX-JSON format."""
    return {
        "meta": {"id": "IDREF5678", "prepared": "2025-01-01T00:00:00Z"},
        "data": {
            "structures": [
                {
                    "name": "Key Short-Term Economic Indicators",
                    "dimensions": {
                        "series": [
                            {
                                "id": "REF_AREA",
                                "name": "Reference area",
                                "keyPosition": 0,
                                "values": [
                                    {"id": "USA", "name": "United States"},
                                    {"id": "FRA", "name": "France"},
                                    {"id": "DEU", "name": "Germany"},
                                ],
                            },
                            {
                                "id": "FREQ",
                                "name": "Frequency",
                                "keyPosition": 1,
                                "values": [{"id": "A", "name": "Annual"}],
                            },
                            {
                                "id": "MEASURE",
                                "name": "Measure",
                                "keyPosition": 2,
                                "values": [
                                    {"id": "GDP", "name": "Gross Domestic Product"},
                                    {"id": "CPI", "name": "Consumer Price Index"},
                                ],
                            },
                            {
                                "id": "UNIT_MEASURE",
                                "name": "Unit of measure",
                                "keyPosition": 3,
                                "values": [
                                    {"id": "GR", "name": "Growth rate"},
                                    {"id": "IX", "name": "Index"},
                                ],
                            },
                        ],
                        "observation": [
                            {
                                "id": "TIME_PERIOD",
                                "name": "Time",
                                "values": [
                                    {"id": "2020", "name": "2020"},
                                    {"id": "2021", "name": "2021"},
                                    {"id": "2022", "name": "2022"},
                                    {"id": "2023", "name": "2023"},
                                ],
                            }
                        ],
                    },
                    "attributes": {
                        "series": [],
                        "observation": [
                            {
                                "id": "OBS_STATUS",
                                "name": "Observation status",
                                "values": [
                                    {"id": "A", "name": "Normal"},
                                    {"id": "E", "name": "Estimated"},
                                    {"id": "P", "name": "Provisional"},
                                ],
                            }
                        ],
                    },
                }
            ],
            "dataSets": [
                {
                    "action": "Information",
                    "series": {
                        # USA, Annual, GDP, Growth rate
                        "0:0:0:0": {
                            "attributes": [],
                            "observations": {
                                "0": [-2.2, 0],  # 2020: -2.2% (normal)
                                "1": [5.9, 0],  # 2021: 5.9% (normal)
                                "2": [2.1, 0],  # 2022: 2.1% (normal)
                                "3": [2.5, 1],  # 2023: 2.5% (estimated)
                            },
                        },
                        # FRA, Annual, GDP, Growth rate
                        "1:0:0:0": {
                            "attributes": [],
                            "observations": {
                                "0": [-7.5, 0],  # 2020
                                "1": [6.4, 0],  # 2021
                                "2": [2.5, 0],  # 2022
                                "3": [0.9, 2],  # 2023 (provisional)
                            },
                        },
                        # DEU, Annual, GDP, Growth rate
                        "2:0:0:0": {
                            "attributes": [],
                            "observations": {
                                "0": [-3.8, 0],  # 2020
                                "1": [3.2, 0],  # 2021
                                "2": [1.9, 0],  # 2022
                                "3": [-0.1, 1],  # 2023 (estimated)
                            },
                        },
                    },
                }
            ],
        },
    }


@pytest.fixture
def sample_oecd_structure_response() -> dict:
    """Sample response from /dataflow/{id}?references=all endpoint."""
    return {
        "meta": {"id": "IDREF9012"},
        "data": {
            "dataflows": [
                {
                    "id": "DSD_KEI@DF_KEI",
                    "agencyID": "OECD.SDD.STES",
                    "version": "4.0",
                    "name": "Key Short-Term Economic Indicators",
                    "description": "Main economic indicators for OECD countries",
                }
            ],
            "dataStructures": [
                {
                    "id": "DSD_KEI",
                    "agencyID": "OECD.SDD.STES",
                    "version": "4.0",
                    "name": "Key Short-Term Economic Indicators",
                    "dataStructureComponents": {
                        "dimensionList": {
                            "dimensions": [
                                {"id": "REF_AREA", "name": "Reference area", "position": 1},
                                {"id": "FREQ", "name": "Frequency", "position": 2},
                                {"id": "MEASURE", "name": "Measure", "position": 3},
                                {"id": "UNIT_MEASURE", "name": "Unit of measure", "position": 4},
                                {"id": "ACTIVITY", "name": "Economic activity", "position": 5},
                                {"id": "ADJUSTMENT", "name": "Adjustment", "position": 6},
                                {"id": "TRANSFORMATION", "name": "Transformation", "position": 7},
                            ]
                        },
                        "attributeList": {
                            "attributes": [
                                {"id": "UNIT_MULT", "name": "Unit multiplier"},
                                {"id": "DECIMALS", "name": "Decimals"},
                                {"id": "OBS_STATUS", "name": "Observation status"},
                            ]
                        },
                    },
                }
            ],
        },
    }


@pytest.fixture
def sample_oecd_empty_data_response() -> dict:
    """Sample response with no data (empty dataset)."""
    return {
        "meta": {"id": "IDREF0000"},
        "data": {
            "structures": [
                {
                    "name": "Empty Dataset",
                    "dimensions": {"series": [], "observation": []},
                    "attributes": {"series": [], "observation": []},
                }
            ],
            "dataSets": [{"action": "Information", "series": {}}],
        },
    }


@pytest.fixture
def sample_oecd_quarterly_data_response() -> dict:
    """Sample response with quarterly data."""
    return {
        "meta": {"id": "IDREF_Q"},
        "data": {
            "structures": [
                {
                    "dimensions": {
                        "series": [
                            {
                                "id": "REF_AREA",
                                "values": [{"id": "USA", "name": "United States"}],
                            },
                            {
                                "id": "FREQ",
                                "values": [{"id": "Q", "name": "Quarterly"}],
                            },
                            {
                                "id": "MEASURE",
                                "values": [{"id": "GDP", "name": "GDP"}],
                            },
                            {
                                "id": "UNIT_MEASURE",
                                "values": [{"id": "GR", "name": "Growth rate"}],
                            },
                        ],
                        "observation": [
                            {
                                "id": "TIME_PERIOD",
                                "values": [
                                    {"id": "2023-Q1"},
                                    {"id": "2023-Q2"},
                                    {"id": "2023-Q3"},
                                    {"id": "2023-Q4"},
                                ],
                            }
                        ],
                    },
                    "attributes": {"series": [], "observation": []},
                }
            ],
            "dataSets": [
                {
                    "series": {
                        "0:0:0:0": {
                            "observations": {
                                "0": [2.2],
                                "1": [2.1],
                                "2": [2.9],
                                "3": [2.5],
                            }
                        }
                    }
                }
            ],
        },
    }
