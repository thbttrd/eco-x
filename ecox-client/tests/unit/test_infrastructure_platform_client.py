"""Tests for the PlatformClient HTTP client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from ecox_client.infrastructure.platform_client import PlatformClient, PlatformClientError


class TestPlatformClientInit:
    """Tests for PlatformClient initialization."""

    def test_init_default_settings(self) -> None:
        """Test client uses default settings."""
        with patch("ecox_client.infrastructure.platform_client.settings") as mock_settings:
            mock_settings.platform_url = "http://localhost:8000"
            mock_settings.platform_timeout = 30.0

            client = PlatformClient()

            assert client.base_url == "http://localhost:8000"
            assert client.timeout == 30.0

    def test_init_custom_url(self) -> None:
        """Test client with custom URL."""
        with patch("ecox_client.infrastructure.platform_client.settings") as mock_settings:
            mock_settings.platform_url = "http://default:8000"
            mock_settings.platform_timeout = 30.0

            client = PlatformClient(base_url="http://custom:9000")

            assert client.base_url == "http://custom:9000"

    def test_init_strips_trailing_slash(self) -> None:
        """Test URL trailing slash is stripped."""
        with patch("ecox_client.infrastructure.platform_client.settings") as mock_settings:
            mock_settings.platform_url = "http://localhost:8000/"
            mock_settings.platform_timeout = 30.0

            client = PlatformClient()

            assert client.base_url == "http://localhost:8000"


class TestPlatformClientRequest:
    """Tests for PlatformClient request method."""

    @pytest.fixture
    def client(self) -> PlatformClient:
        """Create a test client."""
        with patch("ecox_client.infrastructure.platform_client.settings") as mock_settings:
            mock_settings.platform_url = "http://test:8000"
            mock_settings.platform_timeout = 10.0
            return PlatformClient()

    async def test_successful_request(self, client: PlatformClient) -> None:
        """Test successful API request."""
        mock_request = httpx.Request("GET", "http://test:8000/health")
        mock_response = httpx.Response(
            200,
            json={"status": "healthy"},
            request=mock_request,
        )
        client.client.request = AsyncMock(return_value=mock_response)

        result = await client._request("GET", "/health")

        assert result == {"status": "healthy"}
        client.client.request.assert_called_once_with("GET", "/health", params=None)

    async def test_request_with_params(self, client: PlatformClient) -> None:
        """Test request with query parameters."""
        mock_request = httpx.Request("GET", "http://test:8000/datasets")
        mock_response = httpx.Response(
            200,
            json={"items": []},
            request=mock_request,
        )
        client.client.request = AsyncMock(return_value=mock_response)

        await client._request("GET", "/datasets", params={"page": 1, "source": "eurostat"})

        client.client.request.assert_called_once_with(
            "GET", "/datasets", params={"page": 1, "source": "eurostat"}
        )

    async def test_http_error_raises_platform_error(self, client: PlatformClient) -> None:
        """Test HTTP error raises PlatformClientError."""
        mock_response = httpx.Response(
            404,
            json={"detail": "Not found"},
        )
        mock_response._request = httpx.Request("GET", "http://test:8000/invalid")

        async def mock_request(*args, **kwargs):
            response = mock_response
            response.raise_for_status()
            return response

        client.client.request = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Not found", request=mock_response.request, response=mock_response
            )
        )

        with pytest.raises(PlatformClientError) as exc_info:
            await client._request("GET", "/invalid")

        assert exc_info.value.status_code == 404

    async def test_connection_error_raises_platform_error(self, client: PlatformClient) -> None:
        """Test connection error raises PlatformClientError."""
        client.client.request = AsyncMock(side_effect=httpx.RequestError("Connection refused"))

        with pytest.raises(PlatformClientError) as exc_info:
            await client._request("GET", "/health")

        assert "Connection refused" in str(exc_info.value)
        assert exc_info.value.status_code is None


class TestPlatformClientEndpoints:
    """Tests for PlatformClient endpoint methods."""

    @pytest.fixture
    def client(self) -> PlatformClient:
        """Create a test client with mocked request."""
        with patch("ecox_client.infrastructure.platform_client.settings") as mock_settings:
            mock_settings.platform_url = "http://test:8000"
            mock_settings.platform_timeout = 10.0
            return PlatformClient()

    async def test_health(self, client: PlatformClient) -> None:
        """Test health endpoint."""
        client._request = AsyncMock(return_value={"status": "healthy"})

        result = await client.health()

        assert result == {"status": "healthy"}
        client._request.assert_called_once_with("GET", "/health")

    async def test_list_sources(self, client: PlatformClient) -> None:
        """Test list sources endpoint."""
        mock_response = [{"code": "eurostat", "name": "Eurostat"}]
        client._request = AsyncMock(return_value=mock_response)

        result = await client.list_sources()

        assert result == mock_response
        client._request.assert_called_once_with("GET", "/api/sources")

    async def test_get_source_status(self, client: PlatformClient) -> None:
        """Test get source status endpoint."""
        mock_response = {"code": "eurostat", "worker_status": "running"}
        client._request = AsyncMock(return_value=mock_response)

        result = await client.get_source_status("eurostat")

        assert result == mock_response
        client._request.assert_called_once_with("GET", "/api/sources/eurostat")

    async def test_list_datasets(self, client: PlatformClient) -> None:
        """Test list datasets endpoint."""
        mock_response = {"items": [], "total": 0}
        client._request = AsyncMock(return_value=mock_response)

        result = await client.list_datasets(source="eurostat", page=2, page_size=10)

        assert result == mock_response
        client._request.assert_called_once_with(
            "GET",
            "/api/datasets",
            params={"page": 2, "page_size": 10, "source": "eurostat"},
        )

    async def test_list_datasets_with_search(self, client: PlatformClient) -> None:
        """Test list datasets with search."""
        mock_response = {"items": [], "total": 0}
        client._request = AsyncMock(return_value=mock_response)

        await client.list_datasets(search="gdp")

        client._request.assert_called_once_with(
            "GET",
            "/api/datasets",
            params={"page": 1, "page_size": 20, "search": "gdp"},
        )

    async def test_get_dataset(self, client: PlatformClient) -> None:
        """Test get dataset details."""
        mock_response = {"code": "nama_10_gdp", "source": "eurostat"}
        client._request = AsyncMock(return_value=mock_response)

        result = await client.get_dataset("eurostat", "nama_10_gdp")

        assert result == mock_response
        client._request.assert_called_once_with("GET", "/api/datasets/eurostat/nama_10_gdp")

    async def test_get_dataset_values(self, client: PlatformClient) -> None:
        """Test get dataset values."""
        mock_response = {"items": [], "total": 0}
        client._request = AsyncMock(return_value=mock_response)

        result = await client.get_dataset_values(
            "eurostat", "nama_10_gdp", geo="FR", time_period="2023"
        )

        assert result == mock_response
        client._request.assert_called_once_with(
            "GET",
            "/api/datasets/eurostat/nama_10_gdp/values",
            params={"page": 1, "page_size": 100, "geo": "FR", "time_period": "2023"},
        )

    async def test_get_dimension_values(self, client: PlatformClient) -> None:
        """Test get dimension values."""
        mock_response = {"dimension": "geo", "values": ["FR", "DE"]}
        client._request = AsyncMock(return_value=mock_response)

        result = await client.get_dimension_values("eurostat", "nama_10_gdp", "geo")

        assert result == mock_response
        client._request.assert_called_once_with(
            "GET", "/api/datasets/eurostat/nama_10_gdp/dimensions/geo"
        )

    async def test_list_fetch_logs(self, client: PlatformClient) -> None:
        """Test list fetch logs."""
        mock_response = {"items": [], "total": 0}
        client._request = AsyncMock(return_value=mock_response)

        result = await client.list_fetch_logs(source="eurostat", status="success")

        assert result == mock_response
        client._request.assert_called_once_with(
            "GET",
            "/api/fetch-logs",
            params={"page": 1, "page_size": 50, "source": "eurostat", "status": "success"},
        )

    async def test_get_fetch_summary(self, client: PlatformClient) -> None:
        """Test get fetch summary."""
        mock_response = {"total_operations": 100}
        client._request = AsyncMock(return_value=mock_response)

        result = await client.get_fetch_summary(hours=48)

        assert result == mock_response
        client._request.assert_called_once_with(
            "GET", "/api/fetch-logs/summary", params={"hours": 48}
        )

    async def test_close(self, client: PlatformClient) -> None:
        """Test closing the client."""
        client.client.aclose = AsyncMock()

        await client.close()

        client.client.aclose.assert_called_once()


class TestGlobalClientFunctions:
    """Tests for global client functions."""

    def test_get_platform_client_creates_singleton(self) -> None:
        """Test get_platform_client creates a singleton."""
        from ecox_client.infrastructure import platform_client

        # Reset global
        platform_client._client = None

        with patch.object(platform_client, "PlatformClient") as mock_cls:
            client1 = platform_client.get_platform_client()
            client2 = platform_client.get_platform_client()

            assert client1 is client2
            mock_cls.assert_called_once()

        # Cleanup
        platform_client._client = None

    async def test_close_platform_client(self) -> None:
        """Test close_platform_client closes and clears singleton."""
        from ecox_client.infrastructure import platform_client

        mock_client = AsyncMock()
        platform_client._client = mock_client

        await platform_client.close_platform_client()

        mock_client.close.assert_called_once()
        assert platform_client._client is None
