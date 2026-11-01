"""Tests for FetchLog API schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from ecox_shared.schemas import FetchLogListResponse, FetchLogResponse


class TestFetchLogResponse:
    """Tests for FetchLogResponse schema."""

    def test_fetchlog_response_creation(self) -> None:
        """Test creating a FetchLogResponse."""
        now = datetime.now()
        response = FetchLogResponse(
            id=1,
            dataset_code="nama_10_gdp",
            source="eurostat",
            status="success",
            started_at=now,
        )
        assert response.id == 1
        assert response.dataset_code == "nama_10_gdp"
        assert response.source == "eurostat"
        assert response.status == "success"
        assert response.started_at == now
        assert response.records_fetched is None
        assert response.error_message is None
        assert response.completed_at is None
        assert response.duration_seconds is None

    def test_fetchlog_response_success(self) -> None:
        """Test FetchLogResponse for a successful fetch."""
        started = datetime.now()
        completed = started
        response = FetchLogResponse(
            id=1,
            dataset_code="nama_10_gdp",
            source="eurostat",
            status="success",
            records_fetched=1500,
            started_at=started,
            completed_at=completed,
            duration_seconds=5.5,
        )
        assert response.records_fetched == 1500
        assert response.duration_seconds == 5.5
        assert response.error_message is None

    def test_fetchlog_response_error(self) -> None:
        """Test FetchLogResponse for a failed fetch."""
        response = FetchLogResponse(
            id=1,
            dataset_code="invalid_dataset",
            source="eurostat",
            status="error",
            records_fetched=0,
            error_message="Dataset not found: 404",
            started_at=datetime.now(),
        )
        assert response.status == "error"
        assert response.error_message == "Dataset not found: 404"

    def test_fetchlog_response_serialization(self) -> None:
        """Test serializing FetchLogResponse to dict."""
        now = datetime.now()
        response = FetchLogResponse(
            id=1,
            dataset_code="nama_10_gdp",
            source="eurostat",
            status="success",
            started_at=now,
        )
        data = response.model_dump()

        assert data["id"] == 1
        assert data["dataset_code"] == "nama_10_gdp"
        assert data["status"] == "success"
        assert "started_at" in data

    def test_fetchlog_response_required_fields(self) -> None:
        """Test that required fields raise validation errors."""
        with pytest.raises(ValidationError):
            FetchLogResponse()  # type: ignore[call-arg]


class TestFetchLogListResponse:
    """Tests for FetchLogListResponse schema."""

    def test_list_response_creation(self) -> None:
        """Test creating a FetchLogListResponse."""
        now = datetime.now()
        items = [
            FetchLogResponse(
                id=1,
                dataset_code="ds1",
                source="eurostat",
                status="success",
                started_at=now,
            ),
            FetchLogResponse(
                id=2,
                dataset_code="ds2",
                source="fred",
                status="error",
                started_at=now,
            ),
        ]
        response = FetchLogListResponse(
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
        """Test FetchLogListResponse with empty items."""
        response = FetchLogListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert response.items == []
        assert response.total == 0

    def test_list_response_serialization(self) -> None:
        """Test serializing FetchLogListResponse to dict."""
        now = datetime.now()
        items = [
            FetchLogResponse(
                id=1,
                dataset_code="ds1",
                source="eurostat",
                status="success",
                started_at=now,
            ),
        ]
        response = FetchLogListResponse(
            items=items,
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )
        data = response.model_dump()

        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["page"] == 1
