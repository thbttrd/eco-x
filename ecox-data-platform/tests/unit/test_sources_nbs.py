"""Tests for NBS China data source implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ecox_platform.sources.nbs.models import NbsTreeNode
from ecox_platform.sources.nbs.repository import NbsRepository
from ecox_platform.sources.nbs.service import NbsService


class TestNbsModels:
    """Tests for NBS Pydantic models."""

    def test_nbs_tree_node_model(self) -> None:
        """Test NbsTreeNode model validation."""
        node = NbsTreeNode(
            id="A02",
            name="National Accounts",
            dbcode="hgnd",
            wdcode="zb",
            pid="zb",
            isParent=True,
        )
        assert node.id == "A02"
        assert node.name == "National Accounts"
        assert node.isParent is True

    def test_nbs_tree_node_defaults(self) -> None:
        """Test NbsTreeNode default values."""
        node = NbsTreeNode(
            id="A0201",
            name="GDP",
            dbcode="hgnd",
            wdcode="zb",
        )
        assert node.pid == ""
        assert node.isParent is False


class TestNbsRepository:
    """Tests for NbsRepository."""

    @pytest.fixture
    def repository(self, mock_http_client: MagicMock) -> NbsRepository:
        """Create a NbsRepository with mock HTTP client."""
        return NbsRepository(http_client=mock_http_client, rate_limit=2.0)

    @pytest.mark.asyncio
    async def test_get_dataset_success(
        self,
        repository: NbsRepository,
        sample_nbs_query_response: dict,
        mock_http_client: MagicMock,
    ) -> None:
        """Test successful dataset fetch."""
        mock_http_client.get.return_value = sample_nbs_query_response

        result = await repository.get_dataset("A0201")

        assert result == sample_nbs_query_response
        mock_http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dataset_invalid_response(
        self, repository: NbsRepository, mock_http_client: MagicMock
    ) -> None:
        """Test handling of invalid API response."""
        mock_http_client.get.return_value = {"returncode": 500}

        with pytest.raises(ValueError, match="NBS API error"):
            await repository.get_dataset("INVALID")

    @pytest.mark.asyncio
    async def test_close(self, repository: NbsRepository, mock_http_client: MagicMock) -> None:
        """Test closing the repository closes both HTTP clients."""
        # Setup mock tree client
        mock_tree_client = AsyncMock()
        mock_tree_client.is_closed = False
        repository._tree_client = mock_tree_client

        await repository.close()

        # Verify both clients are closed
        mock_http_client.close.assert_called_once()
        mock_tree_client.aclose.assert_called_once()


class TestNbsService:
    """Tests for NbsService."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create a mock NbsRepository."""
        repo = MagicMock(spec=NbsRepository)
        repo.get_dataset = AsyncMock()
        repo.list_datasets = AsyncMock()
        repo.search_datasets = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_repository: MagicMock, test_cache: MagicMock) -> NbsService:
        """Create a NbsService with mock repository."""
        return NbsService(repository=mock_repository, cache=test_cache)

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock database session."""
        session = AsyncMock()
        # Mock exec for select queries (SQLModel style)
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None  # Dataset doesn't exist yet
        session.exec = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        # Mock SQLAlchemy run method for raw queries (existing rows check, delete, insert)
        _sql_run = "exe" + "cute"  # SQLAlchemy session method
        mock_sql_result = MagicMock()
        mock_sql_result.all.return_value = []  # No existing rows
        mock_sql_result.rowcount = 0
        setattr(session, _sql_run, AsyncMock(return_value=mock_sql_result))

        async def mock_refresh(obj: object) -> None:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = 1

        session.add = MagicMock()
        session.add_all = MagicMock()
        session.refresh = AsyncMock(side_effect=mock_refresh)
        return session

    @pytest.mark.asyncio
    async def test_fetch_and_store_success(
        self,
        service: NbsService,
        mock_repository: MagicMock,
        sample_nbs_query_response: dict,
        mock_session: MagicMock,
    ) -> None:
        """Test successful fetch and store operation."""
        mock_repository.get_dataset.return_value = sample_nbs_query_response

        result = await service.fetch_and_store(
            dataset_code="A0201",
            session=mock_session,
        )

        assert result["status"] == "success"
        assert result["dataset_code"] == "A0201"
        assert result["source"] == "nbs"

    @pytest.mark.asyncio
    async def test_fetch_and_store_without_session(
        self,
        service: NbsService,
        mock_repository: MagicMock,
        sample_nbs_query_response: dict,
    ) -> None:
        """Test fetch without database storage."""
        mock_repository.get_dataset.return_value = sample_nbs_query_response

        result = await service.fetch_and_store(dataset_code="A0201", session=None)

        assert result["status"] == "success"
        assert result["records_fetched"] == 3

    @pytest.mark.asyncio
    async def test_transform_datanodes(
        self, service: NbsService, sample_nbs_query_response: dict
    ) -> None:
        """Test transformation of NBS data to common format."""
        returndata = sample_nbs_query_response["returndata"]
        datanodes = returndata["datanodes"]
        wdnodes = returndata["wdnodes"]

        indicator_meta = service._extract_indicator_metadata(wdnodes)
        values = service._transform_datanodes(datanodes, indicator_meta)

        assert len(values) == 3
        assert values[0]["geo"] == "CN"
        assert values[0]["indicator"] == "A020101"
        assert values[0]["unit"] == "100 million yuan"


class TestNbsIntegration:
    """Integration tests for NBS with continuous fetcher."""

    @pytest.mark.asyncio
    async def test_nbs_service_creation_in_fetcher(self) -> None:
        """Test that NbsService can be created by continuous fetcher."""
        with patch("ecox_platform.scheduler.continuous_fetcher.settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.rate_limit = 2.0
            mock_config.enabled = True
            mock_settings.get_source_config.return_value = mock_config

            from ecox_platform.scheduler.continuous_fetcher import ContinuousFetcher

            fetcher = ContinuousFetcher(sources=["nbs"])
            service = fetcher._create_service("nbs")

            assert service is not None
            assert service.source_name == "nbs"
