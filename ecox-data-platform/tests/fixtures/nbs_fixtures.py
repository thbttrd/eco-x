"""Test fixtures for NBS China data source tests."""

import pytest


@pytest.fixture
def sample_nbs_tree_response() -> list[dict]:
    """Sample NBS tree response (list of nodes)."""
    return [
        {
            "id": "A02",
            "name": "National Accounts",
            "dbcode": "hgnd",
            "wdcode": "zb",
            "pid": "zb",
            "isParent": True,
        },
        {
            "id": "A03",
            "name": "Population",
            "dbcode": "hgnd",
            "wdcode": "zb",
            "pid": "zb",
            "isParent": True,
        },
        {
            "id": "A0201",
            "name": "Gross Domestic Product",
            "dbcode": "hgnd",
            "wdcode": "zb",
            "pid": "A02",
            "isParent": False,
        },
    ]


@pytest.fixture
def sample_nbs_query_response() -> dict:
    """Sample NBS QueryData response."""
    return {
        "returncode": 200,
        "returndata": {
            "datanodes": [
                {
                    "code": "zb.A020101_sj.2023",
                    "data": {"data": 126058.2, "hasdata": True, "strdata": "126058.2"},
                    "wds": [
                        {"wdcode": "zb", "valuecode": "A020101"},
                        {"wdcode": "sj", "valuecode": "2023"},
                    ],
                },
                {
                    "code": "zb.A020101_sj.2022",
                    "data": {"data": 120472.0, "hasdata": True, "strdata": "120472.0"},
                    "wds": [
                        {"wdcode": "zb", "valuecode": "A020101"},
                        {"wdcode": "sj", "valuecode": "2022"},
                    ],
                },
                {
                    "code": "zb.A020102_sj.2023",
                    "data": {"data": 12.5, "hasdata": True, "strdata": "12.5"},
                    "wds": [
                        {"wdcode": "zb", "valuecode": "A020102"},
                        {"wdcode": "sj", "valuecode": "2023"},
                    ],
                },
            ],
            "wdnodes": [
                {
                    "wdcode": "zb",
                    "wdname": "Indicators",
                    "nodes": [
                        {
                            "code": "A020101",
                            "name": "Gross Domestic Product",
                            "cname": "国内生产总值",
                            "unit": "100 million yuan",
                            "exp": "Total GDP at current prices",
                        },
                        {
                            "code": "A020102",
                            "name": "GDP Growth Rate",
                            "cname": "国内生产总值增长率",
                            "unit": "%",
                            "exp": "Year-over-year growth rate",
                        },
                    ],
                },
                {
                    "wdcode": "sj",
                    "wdname": "Year",
                    "nodes": [
                        {"code": "2023", "name": "2023"},
                        {"code": "2022", "name": "2022"},
                    ],
                },
            ],
            "hasdatacount": 3,
        },
    }


@pytest.fixture
def sample_nbs_response_with_missing_data() -> dict:
    """Sample NBS response with missing data points."""
    return {
        "returncode": 200,
        "returndata": {
            "datanodes": [
                {
                    "code": "zb.A020101_sj.2023",
                    "data": {"data": 126058.2, "hasdata": True},
                    "wds": [
                        {"wdcode": "zb", "valuecode": "A020101"},
                        {"wdcode": "sj", "valuecode": "2023"},
                    ],
                },
                {
                    "code": "zb.A020101_sj.2022",
                    "data": {"hasdata": False},  # Missing data
                    "wds": [
                        {"wdcode": "zb", "valuecode": "A020101"},
                        {"wdcode": "sj", "valuecode": "2022"},
                    ],
                },
            ],
            "wdnodes": [
                {
                    "wdcode": "zb",
                    "wdname": "Indicators",
                    "nodes": [
                        {"code": "A020101", "name": "GDP", "unit": "100 million yuan"},
                    ],
                },
            ],
            "hasdatacount": 1,
        },
    }
