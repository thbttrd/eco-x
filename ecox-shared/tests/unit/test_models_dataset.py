"""Tests for Dataset-related models."""

from datetime import datetime

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from ecox_shared.models import Dataset, DatasetMetadata, DataValue


class TestDataset:
    """Tests for Dataset model."""

    def test_dataset_creation(self) -> None:
        """Test creating a Dataset instance."""
        dataset = Dataset(
            code="nama_10_gdp",
            name="GDP and main components",
            source="eurostat",
            description="Gross domestic product data",
        )
        assert dataset.code == "nama_10_gdp"
        assert dataset.name == "GDP and main components"
        assert dataset.source == "eurostat"
        assert dataset.description == "Gross domestic product data"
        assert dataset.id is None
        assert dataset.last_fetched is None
        assert dataset.extra_metadata is None

    def test_dataset_with_all_fields(self) -> None:
        """Test creating a Dataset with all fields populated."""
        now = datetime.now()
        dataset = Dataset(
            id=1,
            code="nama_10_gdp",
            name="GDP",
            source="eurostat",
            description="GDP data",
            last_fetched=now,
            extra_metadata='{"dimensions": ["geo", "time"]}',
        )
        assert dataset.id == 1
        assert dataset.last_fetched == now
        assert dataset.extra_metadata == '{"dimensions": ["geo", "time"]}'

    def test_dataset_minimal(self) -> None:
        """Test creating a Dataset with only required fields."""
        # code, name, and source are the required fields
        dataset = Dataset(
            code="test",
            name="Test",
            source="eurostat",
        )
        assert dataset.code == "test"
        assert dataset.name == "Test"
        assert dataset.source == "eurostat"
        # Optional fields should have defaults
        assert dataset.description is None
        assert dataset.last_fetched is None
        assert dataset.extra_metadata is None

    @pytest.mark.asyncio
    async def test_dataset_persistence(self, test_db_session: AsyncSession) -> None:
        """Test persisting a Dataset to the database."""
        dataset = Dataset(
            code="test_dataset",
            name="Test Dataset",
            source="eurostat",
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)

        assert dataset.id is not None
        assert dataset.id > 0

    @pytest.mark.asyncio
    async def test_dataset_relationship_with_values(self, test_db_session: AsyncSession) -> None:
        """Test Dataset relationship with DataValue."""
        from sqlmodel import select

        dataset = Dataset(
            code="test_dataset",
            name="Test Dataset",
            source="eurostat",
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)

        # Add data values
        value1 = DataValue(
            dataset_id=dataset.id,  # type: ignore[arg-type]
            geo="EU27_2020",
            time_period="2022",
            indicator="B1GQ",
            value=15000000.0,
            unit="MIO_EUR",
        )
        value2 = DataValue(
            dataset_id=dataset.id,  # type: ignore[arg-type]
            geo="FR",
            time_period="2022",
            indicator="B1GQ",
            value=2500000.0,
            unit="MIO_EUR",
        )
        test_db_session.add_all([value1, value2])
        await test_db_session.commit()

        # Query values directly to verify relationship
        statement = select(DataValue).where(DataValue.dataset_id == dataset.id)
        result = await test_db_session.exec(statement)
        values = result.all()
        assert len(values) == 2


class TestDataValue:
    """Tests for DataValue model."""

    def test_datavalue_creation(self) -> None:
        """Test creating a DataValue instance."""
        value = DataValue(
            dataset_id=1,
            geo="EU27_2020",
            time_period="2022",
            indicator="B1GQ",
            value=15000000.5,
        )
        assert value.geo == "EU27_2020"
        assert value.time_period == "2022"
        assert value.indicator == "B1GQ"
        assert value.value == 15000000.5
        assert value.unit is None
        assert value.flags is None

    def test_datavalue_with_optional_fields(self) -> None:
        """Test DataValue with optional fields."""
        value = DataValue(
            dataset_id=1,
            geo="FR",
            time_period="2022-Q1",
            indicator="HICP",
            value=102.3,
            unit="PC",
            flags="e",
        )
        assert value.unit == "PC"
        assert value.flags == "e"

    @pytest.mark.asyncio
    async def test_datavalue_persistence(self, test_db_session: AsyncSession) -> None:
        """Test persisting a DataValue to the database."""
        # First create a dataset
        dataset = Dataset(
            code="test_dataset",
            name="Test Dataset",
            source="eurostat",
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)

        # Then create a data value
        value = DataValue(
            dataset_id=dataset.id,  # type: ignore[arg-type]
            geo="EU27_2020",
            time_period="2022",
            indicator="GDP",
            value=15000000.0,
        )
        test_db_session.add(value)
        await test_db_session.commit()
        await test_db_session.refresh(value)

        assert value.id is not None


class TestDatasetMetadata:
    """Tests for DatasetMetadata model."""

    def test_metadata_creation(self) -> None:
        """Test creating a DatasetMetadata instance."""
        metadata = DatasetMetadata(
            dataset_id=1,
            key="dimensions",
            value='["geo", "time", "indicator"]',
        )
        assert metadata.key == "dimensions"
        assert metadata.value == '["geo", "time", "indicator"]'
        assert metadata.created_at is not None

    def test_metadata_with_timestamp(self) -> None:
        """Test that created_at is automatically set."""
        before = datetime.now()
        metadata = DatasetMetadata(
            dataset_id=1,
            key="test",
            value="value",
        )
        after = datetime.now()

        assert before <= metadata.created_at <= after

    @pytest.mark.asyncio
    async def test_metadata_persistence(self, test_db_session: AsyncSession) -> None:
        """Test persisting DatasetMetadata to the database."""
        # First create a dataset
        dataset = Dataset(
            code="test_dataset",
            name="Test Dataset",
            source="eurostat",
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)

        # Then create metadata
        metadata = DatasetMetadata(
            dataset_id=dataset.id,  # type: ignore[arg-type]
            key="dimensions",
            value='{"geo": "Geographic area"}',
        )
        test_db_session.add(metadata)
        await test_db_session.commit()
        await test_db_session.refresh(metadata)

        assert metadata.id is not None
