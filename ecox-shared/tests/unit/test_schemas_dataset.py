"""Tests for Dataset-related API schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from ecox_shared.schemas import (
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetResponse,
    DataValueListResponse,
    DataValueResponse,
)


class TestDatasetResponse:
    """Tests for DatasetResponse schema."""

    def test_dataset_response_creation(self) -> None:
        """Test creating a DatasetResponse."""
        response = DatasetResponse(
            id=1,
            code="nama_10_gdp",
            name="GDP and main components",
            source="eurostat",
        )
        assert response.id == 1
        assert response.code == "nama_10_gdp"
        assert response.name == "GDP and main components"
        assert response.source == "eurostat"
        assert response.description is None
        assert response.last_fetched is None
        assert response.record_count is None

    def test_dataset_response_with_all_fields(self) -> None:
        """Test DatasetResponse with all optional fields."""
        now = datetime.now()
        response = DatasetResponse(
            id=1,
            code="nama_10_gdp",
            name="GDP",
            source="eurostat",
            description="Gross domestic product data",
            last_fetched=now,
            record_count=1500,
        )
        assert response.description == "Gross domestic product data"
        assert response.last_fetched == now
        assert response.record_count == 1500

    def test_dataset_response_serialization(self) -> None:
        """Test serializing DatasetResponse to dict."""
        response = DatasetResponse(
            id=1,
            code="nama_10_gdp",
            name="GDP",
            source="eurostat",
        )
        data = response.model_dump()

        assert data["id"] == 1
        assert data["code"] == "nama_10_gdp"
        assert "description" in data
        assert "last_fetched" in data

    def test_dataset_response_required_fields(self) -> None:
        """Test that required fields raise validation errors."""
        with pytest.raises(ValidationError):
            DatasetResponse()  # type: ignore[call-arg]


class TestDatasetDetailResponse:
    """Tests for DatasetDetailResponse schema."""

    def test_detail_response_creation(self) -> None:
        """Test creating a DatasetDetailResponse."""
        response = DatasetDetailResponse(
            id=1,
            code="nama_10_gdp",
            name="GDP",
            source="eurostat",
        )
        assert response.extra_metadata is None
        assert response.dimensions is None

    def test_detail_response_with_metadata(self) -> None:
        """Test DatasetDetailResponse with extra metadata."""
        response = DatasetDetailResponse(
            id=1,
            code="nama_10_gdp",
            name="GDP",
            source="eurostat",
            extra_metadata={"unit": "EUR", "freq": "A"},
            dimensions=["geo", "time", "indicator"],
        )
        assert response.extra_metadata == {"unit": "EUR", "freq": "A"}
        assert response.dimensions == ["geo", "time", "indicator"]


class TestDatasetListResponse:
    """Tests for DatasetListResponse schema."""

    def test_list_response_creation(self) -> None:
        """Test creating a DatasetListResponse."""
        items = [
            DatasetResponse(id=1, code="ds1", name="Dataset 1", source="eurostat"),
            DatasetResponse(id=2, code="ds2", name="Dataset 2", source="eurostat"),
        ]
        response = DatasetListResponse(
            items=items,
            total=10,
            page=1,
            page_size=2,
            total_pages=5,
        )
        assert len(response.items) == 2
        assert response.total == 10
        assert response.page == 1
        assert response.page_size == 2
        assert response.total_pages == 5

    def test_list_response_empty(self) -> None:
        """Test DatasetListResponse with empty items."""
        response = DatasetListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert response.items == []
        assert response.total == 0


class TestDataValueResponse:
    """Tests for DataValueResponse schema."""

    def test_datavalue_response_creation(self) -> None:
        """Test creating a DataValueResponse."""
        response = DataValueResponse(
            geo="EU27_2020",
            time_period="2022",
            indicator="B1GQ",
            value=15000000.5,
        )
        assert response.geo == "EU27_2020"
        assert response.time_period == "2022"
        assert response.indicator == "B1GQ"
        assert response.value == 15000000.5
        assert response.unit is None
        assert response.flags is None

    def test_datavalue_response_with_optional_fields(self) -> None:
        """Test DataValueResponse with optional fields."""
        response = DataValueResponse(
            geo="FR",
            time_period="2022-Q1",
            indicator="HICP",
            value=102.3,
            unit="PC",
            flags="e",
        )
        assert response.unit == "PC"
        assert response.flags == "e"

    def test_datavalue_response_serialization(self) -> None:
        """Test serializing DataValueResponse to dict."""
        response = DataValueResponse(
            geo="EU27_2020",
            time_period="2022",
            indicator="GDP",
            value=15000000.0,
            unit="MIO_EUR",
        )
        data = response.model_dump()

        assert data["geo"] == "EU27_2020"
        assert data["value"] == 15000000.0
        assert data["unit"] == "MIO_EUR"


class TestDataValueListResponse:
    """Tests for DataValueListResponse schema."""

    def test_list_response_creation(self) -> None:
        """Test creating a DataValueListResponse."""
        items = [
            DataValueResponse(
                geo="EU27_2020",
                time_period="2022",
                indicator="GDP",
                value=15000000.0,
            ),
            DataValueResponse(
                geo="FR",
                time_period="2022",
                indicator="GDP",
                value=2500000.0,
            ),
        ]
        response = DataValueListResponse(
            items=items,
            total=100,
            page=1,
            page_size=2,
            total_pages=50,
            dataset_code="nama_10_gdp",
            source="eurostat",
        )
        assert len(response.items) == 2
        assert response.dataset_code == "nama_10_gdp"
        assert response.source == "eurostat"

    def test_list_response_required_fields(self) -> None:
        """Test that dataset_code and source are required."""
        with pytest.raises(ValidationError):
            DataValueListResponse(
                items=[],
                total=0,
                page=1,
                page_size=20,
                total_pages=0,
                # Missing dataset_code and source
            )
