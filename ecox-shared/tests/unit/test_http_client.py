"""Unit tests for the resilient HTTP client."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from ecox_shared.utils import ResilientHttpClient


@pytest.fixture
def http_client() -> ResilientHttpClient:
    """Create a test HTTP client."""
    return ResilientHttpClient(base_url="https://api.example.com")


class TestResilientHttpClientInit:
    """Tests for ResilientHttpClient initialization."""

    def test_init_with_defaults(self) -> None:
        """Test client initialization with default settings."""
        client = ResilientHttpClient(base_url="https://api.example.com/")

        assert client.base_url == "https://api.example.com"  # Trailing slash stripped
        assert client.rate_limit == 2.0  # Default rate limit
        assert client.timeout == 30  # Default timeout

    def test_init_with_custom_values(self) -> None:
        """Test client initialization with custom values."""
        client = ResilientHttpClient(
            base_url="https://api.example.com",
            rate_limit=5.0,
            timeout=60,
        )

        assert client.rate_limit == 5.0
        assert client.timeout == 60

    def test_init_strips_trailing_slash(self) -> None:
        """Test that trailing slashes are stripped from base_url."""
        client = ResilientHttpClient(base_url="https://api.example.com///")
        assert client.base_url == "https://api.example.com"

    def test_init_with_sub_one_rate_limit(self) -> None:
        """Test that sub-1 rate limits are handled correctly.

        aiolimiter requires max_rate >= 1, so for rates < 1 we invert the math:
        0.33 req/sec becomes max_rate=1.0, time_period=3.03s
        """
        client = ResilientHttpClient(
            base_url="https://api.example.com",
            rate_limit=0.33,
        )

        assert client.rate_limit == 0.33
        # Rate limiter should be configured with max_rate=1.0 and time_period≈3.03
        assert client.rate_limiter.max_rate == 1.0
        assert abs(client.rate_limiter.time_period - (1.0 / 0.33)) < 0.01

    def test_init_with_exactly_one_rate_limit(self) -> None:
        """Test that rate_limit=1.0 uses standard configuration."""
        client = ResilientHttpClient(
            base_url="https://api.example.com",
            rate_limit=1.0,
        )

        assert client.rate_limiter.max_rate == 1.0
        assert client.rate_limiter.time_period == 1.0

    def test_init_with_high_rate_limit(self) -> None:
        """Test that rate_limit > 1 uses standard configuration."""
        client = ResilientHttpClient(
            base_url="https://api.example.com",
            rate_limit=5.0,
        )

        assert client.rate_limiter.max_rate == 5.0
        assert client.rate_limiter.time_period == 1.0


class TestContextManager:
    """Tests for async context manager."""

    @pytest.mark.asyncio
    async def test_aenter(self, http_client: ResilientHttpClient) -> None:
        """Test async context manager entry."""
        result = await http_client.__aenter__()
        assert result is http_client

    @pytest.mark.asyncio
    async def test_aexit(self, http_client: ResilientHttpClient) -> None:
        """Test async context manager exit calls close."""
        http_client.client = AsyncMock()  # type: ignore[assignment]
        await http_client.__aexit__(None, None, None)
        http_client.client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_usage(self) -> None:
        """Test using client as context manager."""
        async with ResilientHttpClient(base_url="https://api.example.com") as client:
            assert isinstance(client, ResilientHttpClient)


class TestClose:
    """Tests for close method."""

    @pytest.mark.asyncio
    async def test_close(self, http_client: ResilientHttpClient) -> None:
        """Test close method closes the underlying client."""
        http_client.client = AsyncMock()  # type: ignore[assignment]
        await http_client.close()
        http_client.client.aclose.assert_called_once()


class TestShouldRetry:
    """Tests for _should_retry method."""

    def test_should_retry_on_timeout(self, http_client: ResilientHttpClient) -> None:
        """Test that timeouts are retryable."""
        exc = httpx.TimeoutException("Timeout")
        assert http_client._should_retry(exc) is True

    def test_should_retry_on_network_error(self, http_client: ResilientHttpClient) -> None:
        """Test that network errors are retryable."""
        exc = httpx.NetworkError("Connection failed")
        assert http_client._should_retry(exc) is True

    def test_should_retry_on_5xx(self, http_client: ResilientHttpClient) -> None:
        """Test that 5xx errors are retryable."""
        response = MagicMock()
        response.status_code = 500
        exc = httpx.HTTPStatusError("Server error", request=MagicMock(), response=response)
        assert http_client._should_retry(exc) is True

    def test_should_retry_on_502(self, http_client: ResilientHttpClient) -> None:
        """Test that 502 Bad Gateway is retryable."""
        response = MagicMock()
        response.status_code = 502
        exc = httpx.HTTPStatusError("Bad Gateway", request=MagicMock(), response=response)
        assert http_client._should_retry(exc) is True

    def test_should_retry_on_503(self, http_client: ResilientHttpClient) -> None:
        """Test that 503 Service Unavailable is retryable."""
        response = MagicMock()
        response.status_code = 503
        exc = httpx.HTTPStatusError("Service Unavailable", request=MagicMock(), response=response)
        assert http_client._should_retry(exc) is True

    def test_should_retry_on_429(self, http_client: ResilientHttpClient) -> None:
        """Test that 429 rate limit errors are retryable."""
        response = MagicMock()
        response.status_code = 429
        exc = httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=response)
        assert http_client._should_retry(exc) is True

    def test_should_not_retry_on_400(self, http_client: ResilientHttpClient) -> None:
        """Test that 400 Bad Request is not retryable."""
        response = MagicMock()
        response.status_code = 400
        exc = httpx.HTTPStatusError("Bad Request", request=MagicMock(), response=response)
        assert http_client._should_retry(exc) is False

    def test_should_not_retry_on_401(self, http_client: ResilientHttpClient) -> None:
        """Test that 401 Unauthorized is not retryable."""
        response = MagicMock()
        response.status_code = 401
        exc = httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=response)
        assert http_client._should_retry(exc) is False

    def test_should_not_retry_on_403(self, http_client: ResilientHttpClient) -> None:
        """Test that 403 Forbidden is not retryable."""
        response = MagicMock()
        response.status_code = 403
        exc = httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=response)
        assert http_client._should_retry(exc) is False

    def test_should_not_retry_on_404(self, http_client: ResilientHttpClient) -> None:
        """Test that 404 errors are not retryable."""
        response = MagicMock()
        response.status_code = 404
        exc = httpx.HTTPStatusError("Not found", request=MagicMock(), response=response)
        assert http_client._should_retry(exc) is False

    def test_should_not_retry_on_other_exceptions(self, http_client: ResilientHttpClient) -> None:
        """Test that other exceptions are not retryable."""
        exc = ValueError("Some error")
        assert http_client._should_retry(exc) is False


class TestMakeRequest:
    """Tests for _make_request method."""

    @pytest.mark.asyncio
    async def test_make_request_success(self, http_client: ResilientHttpClient) -> None:
        """Test successful request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        result = await http_client._make_request("GET", "/test", params={"key": "value"})

        assert result is mock_response
        http_client.client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_empty_endpoint(self, http_client: ResilientHttpClient) -> None:
        """Test request with empty endpoint uses base_url only."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        await http_client._make_request("GET", "")

        call_args = http_client.client.request.call_args
        assert call_args.kwargs["url"] == "https://api.example.com"


class TestGetJson:
    """Tests for get_json method."""

    @pytest.mark.asyncio
    async def test_get_json_returns_dict(self, http_client: ResilientHttpClient) -> None:
        """Test get_json returns dict response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"key": "value"}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        result = await http_client.get_json("/test")

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_json_returns_list(self, http_client: ResilientHttpClient) -> None:
        """Test get_json returns list response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"[1, 2, 3]"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = "[1, 2, 3]"
        mock_response.json.return_value = [1, 2, 3]
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        result = await http_client.get_json("/test")

        assert result == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_get_json_empty_response_raises(self, http_client: ResilientHttpClient) -> None:
        """Test get_json raises on empty response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        with pytest.raises(ValueError, match="Empty response"):
            await http_client.get_json("/test")

    @pytest.mark.asyncio
    async def test_get_json_html_response_raises(self, http_client: ResilientHttpClient) -> None:
        """Test get_json raises on HTML response (WAF protection)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<!DOCTYPE html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<!DOCTYPE html><html>...</html>"
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        with pytest.raises(ValueError, match="HTML instead of JSON"):
            await http_client.get_json("/test")

    @pytest.mark.asyncio
    async def test_get_json_http_error(self, http_client: ResilientHttpClient) -> None:
        """Test get_json propagates HTTP errors."""
        response = MagicMock()
        response.status_code = 500

        http_client.client.request = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=response
            )
        )

        with pytest.raises(httpx.HTTPStatusError):
            await http_client.get_json("/test")

    @pytest.mark.asyncio
    async def test_get_json_timeout_error(self, http_client: ResilientHttpClient) -> None:
        """Test get_json propagates timeout errors."""
        http_client.client.request = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.TimeoutException("Timeout")
        )

        with pytest.raises(httpx.TimeoutException):
            await http_client.get_json("/test")

    @pytest.mark.asyncio
    async def test_get_json_network_error(self, http_client: ResilientHttpClient) -> None:
        """Test get_json propagates network errors."""
        http_client.client.request = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.NetworkError("Network failed")
        )

        with pytest.raises(httpx.NetworkError):
            await http_client.get_json("/test")


class TestGet:
    """Tests for get method."""

    @pytest.mark.asyncio
    async def test_get_returns_dict(self, http_client: ResilientHttpClient) -> None:
        """Test get returns dict response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"key": "value"}'
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        result = await http_client.get("/test")

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_raises_on_list_response(self, http_client: ResilientHttpClient) -> None:
        """Test get raises ValueError on list response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"[1, 2, 3]"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = "[1, 2, 3]"
        mock_response.json.return_value = [1, 2, 3]
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        with pytest.raises(ValueError, match="Expected dict response"):
            await http_client.get("/test")

    @pytest.mark.asyncio
    async def test_get_empty_response_raises(self, http_client: ResilientHttpClient) -> None:
        """Test get raises on empty response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        with pytest.raises(ValueError, match="Empty response"):
            await http_client.get("/test")

    @pytest.mark.asyncio
    async def test_get_html_response_raises(self, http_client: ResilientHttpClient) -> None:
        """Test get raises on HTML response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<!DOCTYPE html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = "<!DOCTYPE html><html>...</html>"
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        with pytest.raises(ValueError, match="HTML instead of JSON"):
            await http_client.get("/test")

    @pytest.mark.asyncio
    async def test_get_http_error(self, http_client: ResilientHttpClient) -> None:
        """Test get propagates HTTP errors."""
        response = MagicMock()
        response.status_code = 404

        http_client.client.request = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.HTTPStatusError("Not found", request=MagicMock(), response=response)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await http_client.get("/test")

    @pytest.mark.asyncio
    async def test_get_timeout_error(self, http_client: ResilientHttpClient) -> None:
        """Test get propagates timeout errors."""
        http_client.client.request = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.TimeoutException("Timeout")
        )

        with pytest.raises(httpx.TimeoutException):
            await http_client.get("/test")

    @pytest.mark.asyncio
    async def test_get_network_error(self, http_client: ResilientHttpClient) -> None:
        """Test get propagates network errors."""
        http_client.client.request = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.NetworkError("Network failed")
        )

        with pytest.raises(httpx.NetworkError):
            await http_client.get("/test")


class TestPost:
    """Tests for post method."""

    @pytest.mark.asyncio
    async def test_post_with_json_data(self, http_client: ResilientHttpClient) -> None:
        """Test post with JSON data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "created"}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        result = await http_client.post("/test", json={"name": "test"})

        assert result == {"status": "created"}

    @pytest.mark.asyncio
    async def test_post_with_form_data(self, http_client: ResilientHttpClient) -> None:
        """Test post with form data."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status = MagicMock()

        http_client.client.request = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]

        result = await http_client.post("/test", data={"field": "value"})

        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_post_http_error(self, http_client: ResilientHttpClient) -> None:
        """Test post propagates HTTP errors."""
        response = MagicMock()
        response.status_code = 500

        http_client.client.request = AsyncMock(  # type: ignore[method-assign]
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=response
            )
        )

        with pytest.raises(httpx.HTTPStatusError):
            await http_client.post("/test", json={"data": "test"})


class TestGetLarge:
    """Tests for get_large method (streaming for large responses)."""

    @pytest.mark.asyncio
    async def test_get_large_returns_json(self, http_client: ResilientHttpClient) -> None:
        """Test get_large returns parsed JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.json.return_value = {"data": "test_data"}
        mock_response.raise_for_status = MagicMock()
        mock_response.aread = AsyncMock(return_value=b'{"data": "test_data"}')

        # Create async context manager mock for stream()
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response
        mock_stream_cm.__aexit__.return_value = None
        http_client.client.stream = MagicMock(return_value=mock_stream_cm)

        result = await http_client.get_large("/test")

        assert result == {"data": "test_data"}

    @pytest.mark.asyncio
    async def test_get_large_with_params(self, http_client: ResilientHttpClient) -> None:
        """Test get_large passes query parameters correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status = MagicMock()
        mock_response.aread = AsyncMock(return_value=b'{"result": "success"}')

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response
        mock_stream_cm.__aexit__.return_value = None
        http_client.client.stream = MagicMock(return_value=mock_stream_cm)

        result = await http_client.get_large("/test", params={"format": "json"})

        assert result == {"result": "success"}
        http_client.client.stream.assert_called_once()
        call_kwargs = http_client.client.stream.call_args
        assert call_kwargs[1]["params"] == {"format": "json"}

    @pytest.mark.asyncio
    async def test_get_large_with_headers(self, http_client: ResilientHttpClient) -> None:
        """Test get_large passes custom headers correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"data": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_response.aread = AsyncMock(return_value=b'{"data": "ok"}')

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response
        mock_stream_cm.__aexit__.return_value = None
        http_client.client.stream = MagicMock(return_value=mock_stream_cm)

        result = await http_client.get_large("/test", headers={"Accept": "application/json"})

        assert result == {"data": "ok"}
        call_kwargs = http_client.client.stream.call_args
        assert call_kwargs[1]["headers"] == {"Accept": "application/json"}

    @pytest.mark.asyncio
    async def test_get_large_rejects_oversized_response(
        self, http_client: ResilientHttpClient
    ) -> None:
        """Test get_large rejects responses exceeding size limit."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # 600MB response (exceeds default 500MB limit)
        mock_response.headers = {"content-length": str(600 * 1024 * 1024)}
        mock_response.raise_for_status = MagicMock()

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response
        mock_stream_cm.__aexit__.return_value = None
        http_client.client.stream = MagicMock(return_value=mock_stream_cm)

        with pytest.raises(ValueError, match="Response too large"):
            await http_client.get_large("/large-data")

    @pytest.mark.asyncio
    async def test_get_large_custom_size_limit(self, http_client: ResilientHttpClient) -> None:
        """Test get_large accepts custom size limit."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # 50MB response
        mock_response.headers = {"content-length": str(50 * 1024 * 1024)}
        mock_response.json.return_value = {"large": "data"}
        mock_response.raise_for_status = MagicMock()
        mock_response.aread = AsyncMock(return_value=b'{"large": "data"}')

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response
        mock_stream_cm.__aexit__.return_value = None
        http_client.client.stream = MagicMock(return_value=mock_stream_cm)

        # Should succeed with 100MB limit
        result = await http_client.get_large("/large-data", max_size_mb=100)
        assert result == {"large": "data"}

    @pytest.mark.asyncio
    async def test_get_large_http_error(self, http_client: ResilientHttpClient) -> None:
        """Test get_large propagates HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response
        mock_stream_cm.__aexit__.return_value = None
        http_client.client.stream = MagicMock(return_value=mock_stream_cm)

        with pytest.raises(httpx.HTTPStatusError):
            await http_client.get_large("/test")

    @pytest.mark.asyncio
    async def test_get_large_timeout_error(self, http_client: ResilientHttpClient) -> None:
        """Test get_large propagates timeout errors."""
        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.side_effect = httpx.TimeoutException("Timeout")
        http_client.client.stream = MagicMock(return_value=mock_stream_cm)

        with pytest.raises(httpx.TimeoutException):
            await http_client.get_large("/test")

    @pytest.mark.asyncio
    async def test_get_large_non_dict_response(self, http_client: ResilientHttpClient) -> None:
        """Test get_large raises error for non-dict JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = ["array", "data"]  # Not a dict
        mock_response.raise_for_status = MagicMock()
        mock_response.aread = AsyncMock(return_value=b'["array", "data"]')

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response
        mock_stream_cm.__aexit__.return_value = None
        http_client.client.stream = MagicMock(return_value=mock_stream_cm)

        with pytest.raises(ValueError, match="Expected dict response"):
            await http_client.get_large("/test")

    @pytest.mark.asyncio
    async def test_get_large_empty_endpoint(self, http_client: ResilientHttpClient) -> None:
        """Test get_large handles empty endpoint (uses base_url directly)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"root": "data"}
        mock_response.raise_for_status = MagicMock()
        mock_response.aread = AsyncMock(return_value=b'{"root": "data"}')

        mock_stream_cm = AsyncMock()
        mock_stream_cm.__aenter__.return_value = mock_response
        mock_stream_cm.__aexit__.return_value = None
        http_client.client.stream = MagicMock(return_value=mock_stream_cm)

        result = await http_client.get_large("")

        assert result == {"root": "data"}
        # Check URL used is just the base URL
        call_args = http_client.client.stream.call_args
        assert call_args[0][1] == "https://api.example.com"
