"""Tests for BaseService content hash and change detection functionality."""

import pytest

from ecox_platform.sources.base.service import BaseService


class TestComputeContentHash:
    """Tests for compute_content_hash static method."""

    def test_empty_values_returns_hash(self) -> None:
        """Test that empty values list returns a valid hash."""
        result = BaseService.compute_content_hash([])
        assert len(result) == 64  # SHA256 hex digest
        assert result.isalnum()

    def test_single_value_returns_hash(self) -> None:
        """Test hash computation for a single value."""
        values = [
            {
                "geo": "FR",
                "time_period": "2022",
                "indicator": "GDP",
                "value": 1000.0,
                "unit": "EUR",
                "flags": None,
            }
        ]
        result = BaseService.compute_content_hash(values)
        assert len(result) == 64

    def test_same_values_same_hash(self) -> None:
        """Test that identical values produce identical hash."""
        values1 = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
            {"geo": "DE", "time_period": "2022", "indicator": "GDP", "value": 2000.0},
        ]
        values2 = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
            {"geo": "DE", "time_period": "2022", "indicator": "GDP", "value": 2000.0},
        ]
        assert BaseService.compute_content_hash(values1) == BaseService.compute_content_hash(
            values2
        )

    def test_different_values_different_hash(self) -> None:
        """Test that different values produce different hash."""
        values1 = [{"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0}]
        values2 = [{"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1001.0}]
        assert BaseService.compute_content_hash(values1) != BaseService.compute_content_hash(
            values2
        )

    def test_order_independent_hash(self) -> None:
        """Test that value order doesn't affect hash (sorted by key)."""
        values1 = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
            {"geo": "DE", "time_period": "2022", "indicator": "GDP", "value": 2000.0},
        ]
        values2 = [
            {"geo": "DE", "time_period": "2022", "indicator": "GDP", "value": 2000.0},
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
        ]
        assert BaseService.compute_content_hash(values1) == BaseService.compute_content_hash(
            values2
        )

    def test_deterministic_hash(self) -> None:
        """Test that hash is deterministic across multiple calls."""
        values = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.0},
            {"geo": "DE", "time_period": "2021", "indicator": "CPI", "value": 105.5},
            {"geo": "EU", "time_period": "2023", "indicator": "POP", "value": 450000000},
        ]
        # Call multiple times
        hashes = [BaseService.compute_content_hash(values) for _ in range(10)]
        # All should be identical
        assert len(set(hashes)) == 1

    def test_handles_none_values(self) -> None:
        """Test that None values in fields are handled correctly."""
        values = [
            {
                "geo": "FR",
                "time_period": "2022",
                "indicator": "GDP",
                "value": 1000.0,
                "unit": None,
                "flags": None,
            }
        ]
        result = BaseService.compute_content_hash(values)
        assert len(result) == 64

    def test_handles_float_precision(self) -> None:
        """Test that float values are handled consistently."""
        values1 = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.123456789}
        ]
        values2 = [
            {"geo": "FR", "time_period": "2022", "indicator": "GDP", "value": 1000.123456789}
        ]
        assert BaseService.compute_content_hash(values1) == BaseService.compute_content_hash(
            values2
        )

    def test_large_dataset_hash(self) -> None:
        """Test hash computation for large datasets."""
        values = [
            {
                "geo": f"GEO_{i}",
                "time_period": f"{2000 + i % 25}",
                "indicator": "GDP",
                "value": float(i * 1000),
            }
            for i in range(10000)
        ]
        result = BaseService.compute_content_hash(values)
        assert len(result) == 64


class TestNeedsUpdate:
    """Tests for needs_update async method.

    Note: These tests require a database session and are integration tests.
    They are placed here for organization but marked appropriately.
    """

    @pytest.mark.asyncio
    async def test_needs_update_no_existing_hash(self, test_db_session) -> None:
        """Test that update is needed when no existing hash."""
        from ecox_shared.models import Dataset

        # Create a dataset without content_hash
        dataset = Dataset(
            code="TEST_DATASET",
            name="Test Dataset",
            source="test",
            content_hash=None,
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)

        # Create a minimal service for testing
        from unittest.mock import MagicMock

        from ecox_platform.infrastructure.cache import Cache

        service = BaseService(
            repository=MagicMock(),
            cache=Cache(),
            source_name="test",
        )

        result = await service.needs_update(test_db_session, dataset.id, "newhash123")
        assert result is True

    @pytest.mark.asyncio
    async def test_needs_update_hash_changed(self, test_db_session) -> None:
        """Test that update is needed when hash has changed."""
        from ecox_shared.models import Dataset

        # Create dataset with existing hash
        dataset = Dataset(
            code="TEST_DATASET",
            name="Test Dataset",
            source="test",
            content_hash="oldhash123",
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)

        from unittest.mock import MagicMock

        from ecox_platform.infrastructure.cache import Cache

        service = BaseService(
            repository=MagicMock(),
            cache=Cache(),
            source_name="test",
        )

        result = await service.needs_update(test_db_session, dataset.id, "newhash456")
        assert result is True

    @pytest.mark.asyncio
    async def test_needs_update_hash_unchanged(self, test_db_session) -> None:
        """Test that update is NOT needed when hash is unchanged."""
        from ecox_shared.models import Dataset

        same_hash = "samehash789"
        dataset = Dataset(
            code="TEST_DATASET",
            name="Test Dataset",
            source="test",
            content_hash=same_hash,
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)

        from unittest.mock import MagicMock

        from ecox_platform.infrastructure.cache import Cache

        service = BaseService(
            repository=MagicMock(),
            cache=Cache(),
            source_name="test",
        )

        result = await service.needs_update(test_db_session, dataset.id, same_hash)
        assert result is False


class TestUpdateContentHash:
    """Tests for update_content_hash async method."""

    @pytest.mark.asyncio
    async def test_update_content_hash_success(self, test_db_session) -> None:
        """Test updating content hash on a dataset."""
        from ecox_shared.models import Dataset

        dataset = Dataset(
            code="TEST_DATASET",
            name="Test Dataset",
            source="test",
            content_hash=None,
        )
        test_db_session.add(dataset)
        await test_db_session.commit()
        await test_db_session.refresh(dataset)

        from unittest.mock import MagicMock

        from ecox_platform.infrastructure.cache import Cache

        service = BaseService(
            repository=MagicMock(),
            cache=Cache(),
            source_name="test",
        )

        new_hash = "updatedhash123"
        await service.update_content_hash(test_db_session, dataset.id, new_hash)

        # Refresh and verify
        await test_db_session.refresh(dataset)
        assert dataset.content_hash == new_hash
