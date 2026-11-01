"""Tests for Source API schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from ecox_shared.schemas import SourceResponse, SourceStatusResponse


class TestSourceResponse:
    """Tests for SourceResponse schema."""

    def test_source_response_creation(self) -> None:
        """Test creating a SourceResponse."""
        response = SourceResponse(
            code="eurostat",
            name="Eurostat",
            dataset_count=50,
        )
        assert response.code == "eurostat"
        assert response.name == "Eurostat"
        assert response.dataset_count == 50
        assert response.description is None
        assert response.total_available is None
        assert response.last_activity is None

    def test_source_response_with_all_fields(self) -> None:
        """Test SourceResponse with all optional fields."""
        now = datetime.now()
        response = SourceResponse(
            code="eurostat",
            name="Eurostat",
            description="Statistical office of the European Union",
            dataset_count=50,
            total_available=5000,
            last_activity=now,
        )
        assert response.description == "Statistical office of the European Union"
        assert response.total_available == 5000
        assert response.last_activity == now

    def test_source_response_serialization(self) -> None:
        """Test serializing SourceResponse to dict."""
        response = SourceResponse(
            code="eurostat",
            name="Eurostat",
            dataset_count=50,
        )
        data = response.model_dump()

        assert data["code"] == "eurostat"
        assert data["name"] == "Eurostat"
        assert data["dataset_count"] == 50
        assert "description" in data
        assert "total_available" in data

    def test_source_response_required_fields(self) -> None:
        """Test that required fields raise validation errors."""
        with pytest.raises(ValidationError):
            SourceResponse()  # type: ignore[call-arg]


class TestSourceStatusResponse:
    """Tests for SourceStatusResponse schema."""

    def test_status_response_creation(self) -> None:
        """Test creating a SourceStatusResponse."""
        response = SourceStatusResponse(
            code="eurostat",
            name="Eurostat",
            dataset_count=50,
            worker_status="running",
            rate_limit=2.0,
        )
        assert response.code == "eurostat"
        assert response.name == "Eurostat"
        assert response.dataset_count == 50
        assert response.worker_status == "running"
        assert response.rate_limit == 2.0
        assert response.fetch_queue_size == 0
        assert response.recent_errors == 0

    def test_status_response_with_all_fields(self) -> None:
        """Test SourceStatusResponse with all fields."""
        now = datetime.now()
        response = SourceStatusResponse(
            code="eurostat",
            name="Eurostat",
            description="EU statistics",
            dataset_count=50,
            total_available=5000,
            last_activity=now,
            worker_status="idle",
            fetch_queue_size=10,
            rate_limit=2.0,
            recent_errors=3,
        )
        assert response.worker_status == "idle"
        assert response.fetch_queue_size == 10
        assert response.recent_errors == 3

    def test_status_response_worker_statuses(self) -> None:
        """Test different worker status values."""
        for status in ["running", "idle", "stopped", "error"]:
            response = SourceStatusResponse(
                code="eurostat",
                name="Eurostat",
                dataset_count=0,
                worker_status=status,
                rate_limit=2.0,
            )
            assert response.worker_status == status

    def test_status_response_serialization(self) -> None:
        """Test serializing SourceStatusResponse to dict."""
        response = SourceStatusResponse(
            code="eurostat",
            name="Eurostat",
            dataset_count=50,
            worker_status="running",
            rate_limit=2.0,
        )
        data = response.model_dump()

        assert data["code"] == "eurostat"
        assert data["worker_status"] == "running"
        assert data["rate_limit"] == 2.0
        assert data["fetch_queue_size"] == 0
        assert data["recent_errors"] == 0

    def test_status_response_required_fields(self) -> None:
        """Test that required fields raise validation errors."""
        with pytest.raises(ValidationError):
            SourceStatusResponse(
                code="eurostat",
                name="Eurostat",
                dataset_count=50,
                # Missing worker_status and rate_limit
            )
