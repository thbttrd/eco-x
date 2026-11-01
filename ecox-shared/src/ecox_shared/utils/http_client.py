"""Resilient HTTP client with retry logic and rate limiting.

This module provides an HTTP client with:
- Automatic retry with exponential backoff (using tenacity)
- Rate limiting (using aiolimiter)
- Timeout handling
- Error classification (retryable vs non-retryable)
"""

from typing import Any

import httpx
import structlog
from aiolimiter import AsyncLimiter
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

# Default configuration values
DEFAULT_RATE_LIMIT = 2.0  # requests per second
DEFAULT_TIMEOUT = 30  # seconds


def _is_retryable_exception(exc: BaseException) -> bool:
    """Check if an exception should trigger a retry.

    Used by tenacity's retry decorator to determine if request should be retried.

    Args:
        exc: The exception to check

    Returns:
        True if the request should be retried, False otherwise
    """
    # Retry on network errors and timeouts
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True

    # Retry on HTTP errors with specific status codes (5xx server errors and 429 rate limits)
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500 or exc.response.status_code == 429

    # Retry on connection drops during streaming (common with large OECD responses)
    error_msg = str(exc).lower()
    if "peer closed connection" in error_msg or "incomplete chunked read" in error_msg:
        return True

    return False


class ResilientHttpClient:
    """HTTP client with retry logic and rate limiting.

    Features:
    - Automatic retry on network errors, timeouts, and 5xx responses (3 attempts)
    - Exponential backoff: 1s → 2s → 4s → 8s
    - Rate limiting to prevent API overload
    - Structured logging for all requests

    Note:
        Retries are hardcoded to 3 attempts in the @retry decorator. Python decorators
        are evaluated at class definition time and cannot access instance variables.
    """

    def __init__(
        self,
        base_url: str,
        rate_limit: float = DEFAULT_RATE_LIMIT,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the HTTP client.

        Args:
            base_url: Base URL for all requests
            rate_limit: Maximum requests per second (default: 2.0)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip("/")
        self.rate_limit = rate_limit
        self.timeout = timeout

        # Rate limiter: limit requests per second
        # aiolimiter requires max_rate >= 1, so for rates < 1 we invert the math
        # e.g., 0.33 req/sec = 1 req per 3 seconds
        if rate_limit >= 1.0:
            self.rate_limiter = AsyncLimiter(max_rate=rate_limit, time_period=1.0)
        else:
            # For sub-1 rates, use max_rate=1 with longer time_period
            self.rate_limiter = AsyncLimiter(max_rate=1.0, time_period=1.0 / rate_limit)

        # HTTP client with timeout and redirect following
        self.client = httpx.AsyncClient(timeout=float(self.timeout), follow_redirects=True)

        # Dedicated client for large downloads (lazy initialized)
        self._large_download_client: httpx.AsyncClient | None = None

        logger.info(
            "HTTP client initialized",
            base_url=self.base_url,
            rate_limit=self.rate_limit,
            timeout=self.timeout,
        )

    async def __aenter__(self) -> "ResilientHttpClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close all HTTP clients."""
        await self.client.aclose()
        if self._large_download_client is not None:
            await self._large_download_client.aclose()
            self._large_download_client = None
        logger.info("HTTP client closed")

    def _get_large_download_client(self) -> httpx.AsyncClient:
        """Get or create a dedicated client for large downloads.

        Uses separate connection pool with extended timeouts:
        - 30s connect timeout (same as main)
        - 30 minute read timeout (for streaming large files)
        - Separate connection pool to not block normal requests
        """
        if self._large_download_client is None:
            timeout = httpx.Timeout(
                connect=30.0,  # 30s to establish connection
                read=1800.0,  # 30 minutes for streaming large responses
                write=30.0,
                pool=30.0,
            )
            # Separate limits = separate connection pool
            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=300.0,  # 5 minutes
            )
            self._large_download_client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
            )
            logger.info(
                "Large download client initialized",
                read_timeout=1800.0,
                max_connections=10,
            )
        return self._large_download_client

    def _should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry.

        Args:
            exception: The exception to check

        Returns:
            True if the request should be retried, False otherwise
        """
        # Retry on network errors and timeouts
        if isinstance(exception, (httpx.TimeoutException, httpx.NetworkError)):
            return True

        # Retry on HTTP errors with specific status codes
        if isinstance(exception, httpx.HTTPStatusError):
            # Retry on 5xx server errors and 429 rate limits
            return exception.response.status_code >= 500 or exception.response.status_code == 429

        # Retry on connection drops during streaming
        error_msg = str(exception).lower()
        if "peer closed connection" in error_msg or "incomplete chunked read" in error_msg:
            return True

        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(_is_retryable_exception),
        reraise=True,
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses (after retries)
            httpx.TimeoutException: On timeout (after retries)
            httpx.NetworkError: On network errors (after retries)
        """
        # Handle empty endpoint - don't add trailing slash
        if endpoint:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
        else:
            url = self.base_url

        async with self.rate_limiter:
            logger.debug("Making HTTP request", method=method, url=url, params=params)

            response = await self.client.request(method=method, url=url, params=params, **kwargs)

            # Log response
            logger.debug(
                "HTTP response received",
                method=method,
                url=url,
                status_code=response.status_code,
                response_time=response.elapsed.total_seconds(),
            )

            # Raise on 4xx/5xx errors
            response.raise_for_status()

            return response

    async def get_json(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | list[Any]:
        """Make a GET request and return raw JSON response (dict or list).

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response (can be dict or list)

        Raises:
            httpx.HTTPStatusError: On HTTP errors
            ValueError: If response is not valid JSON
        """
        try:
            response = await self._make_request("GET", endpoint, params=params)
            if not response.content:
                raise ValueError(f"Empty response from {endpoint or self.base_url}")

            # Detect HTML response (WAF/bot protection blocking JSON API)
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type or response.text.strip().startswith("<!DOCTYPE"):
                logger.warning(
                    "Received HTML instead of JSON - possible WAF/bot protection",
                    endpoint=endpoint,
                    content_type=content_type,
                )
                raise ValueError(
                    "API returned HTML instead of JSON (possible rate limit or bot protection). "
                    "Try again later or reduce request frequency."
                )

            result: dict[str, Any] | list[Any] = response.json()
            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP request failed",
                endpoint=endpoint,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise
        except httpx.TimeoutException as e:
            logger.error("HTTP request timed out", endpoint=endpoint, error=str(e))
            raise
        except httpx.NetworkError as e:
            logger.error("Network error during HTTP request", endpoint=endpoint, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during HTTP request", endpoint=endpoint, error=str(e))
            raise

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request and return JSON response as dict.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPStatusError: On HTTP errors
            ValueError: If response is not valid JSON or not a dict
        """
        try:
            response = await self._make_request("GET", endpoint, params=params)
            if not response.content:
                raise ValueError(f"Empty response from {endpoint or self.base_url}")

            # Detect HTML response (WAF/bot protection blocking JSON API)
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type or response.text.strip().startswith("<!DOCTYPE"):
                logger.warning(
                    "Received HTML instead of JSON - possible WAF/bot protection",
                    endpoint=endpoint,
                    content_type=content_type,
                )
                raise ValueError(
                    "API returned HTML instead of JSON (possible rate limit or bot protection). "
                    "Try again later or reduce request frequency."
                )

            json_data = response.json()
            if isinstance(json_data, dict):
                return json_data
            raise ValueError(f"Expected dict response, got {type(json_data).__name__}")
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP request failed",
                endpoint=endpoint,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise
        except httpx.TimeoutException as e:
            logger.error("HTTP request timed out", endpoint=endpoint, error=str(e))
            raise
        except httpx.NetworkError as e:
            logger.error("Network error during HTTP request", endpoint=endpoint, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during HTTP request", endpoint=endpoint, error=str(e))
            raise

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a POST request and return JSON response.

        Args:
            endpoint: API endpoint
            data: Form data
            json: JSON data

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPStatusError: On HTTP errors
        """
        response = await self._make_request("POST", endpoint, data=data, json=json)
        return dict(response.json())

    async def get_large(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        max_size_mb: int = 500,
    ) -> dict[str, Any]:
        """Make a GET request for potentially large responses using streaming.

        Uses streaming to properly handle large responses that might otherwise
        be truncated due to buffer limits. This is especially important for
        OECD datasets which can be 100MB+.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Optional HTTP headers
            max_size_mb: Maximum allowed response size in MB (default 500MB)

        Returns:
            JSON response as dictionary

        Raises:
            httpx.HTTPStatusError: On HTTP errors
            ValueError: If response exceeds size limit or is truncated
        """
        # Build URL
        if endpoint:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
        else:
            url = self.base_url

        try:
            # Get dedicated client with extended timeouts for large downloads
            client = self._get_large_download_client()

            async with self.rate_limiter:
                logger.debug(
                    "Making streaming HTTP request",
                    method="GET",
                    url=url,
                    params=params,
                )

                # Use streaming with dedicated client to handle large responses
                async with client.stream("GET", url, params=params, headers=headers) as response:
                    response.raise_for_status()

                    # Check content length if available
                    content_length = response.headers.get("content-length")
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > max_size_mb:
                            raise ValueError(
                                f"Response too large: {size_mb:.1f}MB exceeds limit of {max_size_mb}MB"
                            )
                        logger.debug("Large response size", size_mb=f"{size_mb:.1f}")

                    # Read entire response with streaming
                    content = await response.aread()

                    logger.debug(
                        "Streaming response received",
                        url=url,
                        status_code=response.status_code,
                        content_length=len(content),
                    )

                    # Parse JSON
                    json_data = response.json()
                    if isinstance(json_data, dict):
                        return json_data
                    raise ValueError(f"Expected dict response, got {type(json_data).__name__}")

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP request failed",
                endpoint=endpoint,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise
        except httpx.TimeoutException as e:
            logger.error("HTTP request timed out", endpoint=endpoint, error=str(e))
            raise
        except httpx.NetworkError as e:
            logger.error("Network error during HTTP request", endpoint=endpoint, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during HTTP request", endpoint=endpoint, error=str(e))
            raise
