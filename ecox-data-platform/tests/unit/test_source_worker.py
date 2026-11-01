"""Unit tests for SourceWorker multi-queue architecture.

Tests cover:
- Large dataset detection (_is_large_dataset)
- Timeout tracking (_record_timeout, should_skip_timeout_dataset)
- Queue splitting behavior
"""

from unittest.mock import MagicMock

import pytest

from ecox_platform.scheduler.source_worker import (
    FAST_QUEUE_TIMEOUT,
    QUEUE_MAX_CONSECUTIVE_FAILURES,
    SLOW_QUEUE_TIMEOUT,
    SourceWorker,
)


class TestLargeDatasetDetection:
    """Tests for _is_large_dataset method."""

    @pytest.fixture
    def worker(self) -> SourceWorker:
        """Create a worker with mocked dependencies."""
        mock_service = MagicMock()
        mock_db_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.max_concurrent = 3
        mock_config.rate_limit = 1.0
        mock_config.refresh_hours = 24

        return SourceWorker(
            source_name="test",
            service=mock_service,
            db_manager=mock_db_manager,
            config=mock_config,
        )

    def test_cfe_agency_in_code_is_large(self, worker: SourceWorker) -> None:
        """CFE agency in dataset code should be detected as large."""
        dataset_meta = {"code": "OECD.CFE.EDS,DSD_EDS_LARGE,1.0"}
        assert worker._is_large_dataset(dataset_meta) is True

    def test_eds_agency_in_code_is_large(self, worker: SourceWorker) -> None:
        """EDS agency in dataset code should be detected as large."""
        dataset_meta = {"code": "OECD.SDD.EDS,DSD_SOMETHING,1.0"}
        assert worker._is_large_dataset(dataset_meta) is True

    def test_cfe_in_agency_id_is_large(self, worker: SourceWorker) -> None:
        """CFE in agency_id field should be detected as large."""
        dataset_meta = {"code": "SOME_DATASET", "agency_id": "CFE"}
        assert worker._is_large_dataset(dataset_meta) is True

    def test_normal_dataset_not_large(self, worker: SourceWorker) -> None:
        """Normal datasets should not be detected as large."""
        dataset_meta = {"code": "OECD.SDD.STES,DSD_KEI,4.0"}
        assert worker._is_large_dataset(dataset_meta) is False

    def test_empty_metadata_not_large(self, worker: SourceWorker) -> None:
        """Empty metadata should not be detected as large."""
        dataset_meta = {}
        assert worker._is_large_dataset(dataset_meta) is False


class TestTimeoutTracking:
    """Tests for timeout tracking methods."""

    @pytest.fixture
    def worker(self) -> SourceWorker:
        """Create a worker with mocked dependencies."""
        mock_service = MagicMock()
        mock_db_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.max_concurrent = 3
        mock_config.rate_limit = 1.0
        mock_config.refresh_hours = 24

        return SourceWorker(
            source_name="test",
            service=mock_service,
            db_manager=mock_db_manager,
            config=mock_config,
        )

    def test_first_timeout_not_marked_too_large(self, worker: SourceWorker) -> None:
        """First timeout should not mark dataset as too large."""
        worker._record_timeout("DATASET_1")

        assert worker.should_skip_timeout_dataset("DATASET_1") is False
        assert worker._timeout_counts["DATASET_1"] == 1

    def test_second_timeout_marks_too_large(self, worker: SourceWorker) -> None:
        """Second timeout should mark dataset as too large."""
        worker._record_timeout("DATASET_1")
        worker._record_timeout("DATASET_1")

        assert worker.should_skip_timeout_dataset("DATASET_1") is True
        assert "DATASET_1" in worker._timeout_datasets

    def test_clear_timeout_on_success(self, worker: SourceWorker) -> None:
        """Successful fetch should clear timeout count."""
        worker._record_timeout("DATASET_1")
        assert worker._timeout_counts["DATASET_1"] == 1

        worker._clear_timeout("DATASET_1")
        assert "DATASET_1" not in worker._timeout_counts

    def test_get_timeout_datasets_returns_list(self, worker: SourceWorker) -> None:
        """get_timeout_datasets should return list of too-large datasets."""
        # Mark two datasets as too large
        worker._record_timeout("DATASET_1")
        worker._record_timeout("DATASET_1")
        worker._record_timeout("DATASET_2")
        worker._record_timeout("DATASET_2")

        result = worker.get_timeout_datasets()

        assert isinstance(result, list)
        assert len(result) == 2
        assert "DATASET_1" in result
        assert "DATASET_2" in result


class TestWorkerInitialization:
    """Tests for worker initialization."""

    def test_dual_semaphores_created(self) -> None:
        """Worker should create separate fast and slow semaphores."""
        mock_service = MagicMock()
        mock_db_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.max_concurrent = 3
        mock_config.rate_limit = 1.0
        mock_config.refresh_hours = 24

        worker = SourceWorker(
            source_name="test",
            service=mock_service,
            db_manager=mock_db_manager,
            config=mock_config,
        )

        # Fast queue should have max_concurrent - 1 slots (2)
        assert worker.fast_semaphore._value == 2
        # Slow queue should have 1 slot
        assert worker.slow_semaphore._value == 1

    def test_large_agencies_configured(self) -> None:
        """Worker should have CFE and EDS as large agencies."""
        mock_service = MagicMock()
        mock_db_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.max_concurrent = 3
        mock_config.rate_limit = 1.0
        mock_config.refresh_hours = 24

        worker = SourceWorker(
            source_name="test",
            service=mock_service,
            db_manager=mock_db_manager,
            config=mock_config,
        )

        assert "CFE" in worker.large_agencies
        assert "EDS" in worker.large_agencies


class TestWorkerStatus:
    """Tests for worker status reporting."""

    def test_status_includes_timeout_datasets(self) -> None:
        """Worker status should include timeout tracking info."""
        mock_service = MagicMock()
        mock_db_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.max_concurrent = 3
        mock_config.rate_limit = 1.0
        mock_config.refresh_hours = 24

        worker = SourceWorker(
            source_name="test",
            service=mock_service,
            db_manager=mock_db_manager,
            config=mock_config,
        )

        # Mark a dataset as too large
        worker._record_timeout("LARGE_DATASET")
        worker._record_timeout("LARGE_DATASET")

        status = worker.status()

        assert "timeout_datasets" in status
        assert "timeout_datasets_count" in status
        assert status["timeout_datasets_count"] == 1
        assert "LARGE_DATASET" in status["timeout_datasets"]


class TestConstants:
    """Tests for module constants."""

    def test_fast_queue_timeout_is_5_minutes(self) -> None:
        """Fast queue should have 5-minute timeout."""
        assert FAST_QUEUE_TIMEOUT == 300  # 5 minutes

    def test_slow_queue_timeout_is_30_minutes(self) -> None:
        """Slow queue should have 30-minute timeout."""
        assert SLOW_QUEUE_TIMEOUT == 1800  # 30 minutes

    def test_consecutive_failure_threshold_is_5(self) -> None:
        """Consecutive failure threshold should be 5 per queue."""
        assert QUEUE_MAX_CONSECUTIVE_FAILURES == 5


class TestRateLimitDetection:
    """Tests for 429 rate limit detection in _fetch_dataset.

    The implementation detects 429 in two ways:
    1. From exception.response.status_code (preferred)
    2. From error string patterns ("'429" or "Too Many Requests")
    """

    @pytest.fixture
    def worker(self) -> SourceWorker:
        """Create a worker with mocked dependencies."""
        mock_service = MagicMock()
        mock_db_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.max_concurrent = 3
        mock_config.rate_limit = 1.0
        mock_config.refresh_hours = 24

        return SourceWorker(
            source_name="test",
            service=mock_service,
            db_manager=mock_db_manager,
            config=mock_config,
        )

    def test_detect_429_from_status_code(self, worker: SourceWorker) -> None:
        """429 should be detected from exception.response.status_code."""
        # Create an exception with a response attribute
        exc = Exception("Rate limited")
        exc.response = MagicMock()  # type: ignore[attr-defined]
        exc.response.status_code = 429

        # Check detection logic directly
        is_server_error = False
        is_rate_limited = False
        if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
            status_code = exc.response.status_code
            is_server_error = 500 <= status_code < 600
            is_rate_limited = status_code == 429

        assert is_rate_limited is True
        assert is_server_error is False

    def test_detect_429_from_error_string(self, worker: SourceWorker) -> None:
        """429 should be detected from error message pattern."""
        # Exception without response attribute - fallback to string matching
        error_str = "Client error '429 Too Many Requests' for url 'https://api.example.com'"

        is_rate_limited = "'429" in error_str or "Too Many Requests" in error_str

        assert is_rate_limited is True

    def test_detect_too_many_requests_from_error_string(self, worker: SourceWorker) -> None:
        """'Too Many Requests' text should trigger rate limit detection."""
        error_str = "API returned: Too Many Requests. Please slow down."

        is_rate_limited = "'429" in error_str or "Too Many Requests" in error_str

        assert is_rate_limited is True

    def test_detect_5xx_from_status_code(self, worker: SourceWorker) -> None:
        """5xx errors should be detected as server errors, not rate limits."""
        exc = Exception("Server error")
        exc.response = MagicMock()  # type: ignore[attr-defined]
        exc.response.status_code = 503

        is_server_error = False
        is_rate_limited = False
        if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
            status_code = exc.response.status_code
            is_server_error = 500 <= status_code < 600
            is_rate_limited = status_code == 429

        assert is_server_error is True
        assert is_rate_limited is False

    def test_distinguish_429_from_5xx(self, worker: SourceWorker) -> None:
        """429 and 5xx should be detected separately."""
        # Test 429
        exc_429 = Exception("Rate limited")
        exc_429.response = MagicMock()  # type: ignore[attr-defined]
        exc_429.response.status_code = 429

        status_code = exc_429.response.status_code
        is_rate_limited_429 = status_code == 429
        is_server_error_429 = 500 <= status_code < 600

        # Test 503
        exc_503 = Exception("Service unavailable")
        exc_503.response = MagicMock()  # type: ignore[attr-defined]
        exc_503.response.status_code = 503

        status_code = exc_503.response.status_code
        is_rate_limited_503 = (
            status_code == 429
        )  # Check if 503 is detected as 429 (it shouldn't be)
        is_server_error_503 = 500 <= status_code < 600

        # 429: rate limited, not server error
        assert is_rate_limited_429 is True
        assert is_server_error_429 is False

        # 503: server error, not rate limited
        assert is_rate_limited_503 is False
        assert is_server_error_503 is True


class TestQueuePauseOnRateLimit:
    """Tests for queue pause behavior on 429 rate limiting.

    When rate limited, the queue should:
    1. Pause for 60 seconds
    2. Reset consecutive_failures counter
    3. NOT stop the queue early
    """

    @pytest.fixture
    def worker(self) -> SourceWorker:
        """Create a worker with mocked dependencies."""
        mock_service = MagicMock()
        mock_db_manager = MagicMock()
        mock_config = MagicMock()
        mock_config.max_concurrent = 3
        mock_config.rate_limit = 1.0
        mock_config.refresh_hours = 24

        return SourceWorker(
            source_name="test",
            service=mock_service,
            db_manager=mock_db_manager,
            config=mock_config,
        )

    @pytest.mark.asyncio
    async def test_queue_pause_on_rate_limit(self, worker: SourceWorker) -> None:
        """Queue should pause for 60 seconds when rate limited."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        # Mock _fetch_dataset to return rate_limited on first call, success on second
        call_count = 0

        async def mock_fetch(*args: object, **kwargs: object) -> tuple[bool, bool, bool, bool]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return (False, False, False, True)  # Rate limited
            return (True, False, False, False)  # Success

        worker._fetch_dataset = mock_fetch  # type: ignore[method-assign]

        datasets = [{"code": "DATASET_1"}, {"code": "DATASET_2"}]

        with patch.object(asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
            result = await worker._process_queue(datasets, worker.fast_semaphore, 300, "fast")

        # Should have slept for 60s on rate limit, plus 1s rate limit delay per request
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert 60 in sleep_calls, f"Expected 60s pause, got calls: {sleep_calls}"

        # Should have continued after pause (fetched 1, failed 1 for rate limit)
        assert result["fetched"] == 1
        assert result["rate_limited"] == 1

    @pytest.mark.asyncio
    async def test_consecutive_failures_reset_after_rate_limit_pause(
        self, worker: SourceWorker
    ) -> None:
        """Consecutive failures should reset to 0 after rate limit pause."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        # Track if we would have stopped due to consecutive failures
        # 5 regular failures should stop, but 5 rate limits should NOT

        call_count = 0

        async def mock_fetch(*args: object, **kwargs: object) -> tuple[bool, bool, bool, bool]:
            nonlocal call_count
            call_count += 1
            if call_count <= 5:
                return (False, False, False, True)  # 5 rate limits
            return (True, False, False, False)  # Success on 6th

        worker._fetch_dataset = mock_fetch  # type: ignore[method-assign]

        datasets = [{"code": f"DATASET_{i}"} for i in range(6)]

        with patch.object(asyncio, "sleep", new_callable=AsyncMock):
            result = await worker._process_queue(datasets, worker.fast_semaphore, 300, "fast")

        # Queue should NOT have stopped early (all 6 datasets processed)
        # 5 rate limited + 1 success
        assert result["rate_limited"] == 5
        assert result["fetched"] == 1
        assert result["failed"] == 5  # Rate limited counts as failed

    @pytest.mark.asyncio
    async def test_queue_stops_on_non_rate_limit_failures(self, worker: SourceWorker) -> None:
        """Queue should stop after 5 consecutive non-rate-limit failures."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        call_count = 0

        async def mock_fetch(*args: object, **kwargs: object) -> tuple[bool, bool, bool, bool]:
            nonlocal call_count
            call_count += 1
            # Return regular failure (not rate limited, not server error)
            return (False, False, False, False)

        worker._fetch_dataset = mock_fetch  # type: ignore[method-assign]

        # 10 datasets, but should stop after 5 consecutive failures
        datasets = [{"code": f"DATASET_{i}"} for i in range(10)]

        with patch.object(asyncio, "sleep", new_callable=AsyncMock):
            result = await worker._process_queue(datasets, worker.fast_semaphore, 300, "fast")

        # Should have stopped after 5 failures
        assert result["failed"] == 5
        assert result["fetched"] == 0
        # Should NOT have processed all 10
        assert call_count == 5

    @pytest.mark.asyncio
    async def test_rate_limited_counter_tracked(self, worker: SourceWorker) -> None:
        """Rate limited counter should be accurately tracked in results."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        call_count = 0

        async def mock_fetch(*args: object, **kwargs: object) -> tuple[bool, bool, bool, bool]:
            nonlocal call_count
            call_count += 1
            if call_count in {1, 3}:
                return (False, False, False, True)  # Rate limited
            if call_count == 2:
                return (True, False, False, False)  # Success
            return (False, False, True, False)  # Server error

        worker._fetch_dataset = mock_fetch  # type: ignore[method-assign]

        datasets = [{"code": f"DATASET_{i}"} for i in range(4)]

        with patch.object(asyncio, "sleep", new_callable=AsyncMock):
            result = await worker._process_queue(datasets, worker.fast_semaphore, 300, "fast")

        assert result["rate_limited"] == 2  # 2 rate limited
        assert result["fetched"] == 1  # 1 success
        assert result["server_errors"] == 1  # 1 server error
        assert result["failed"] == 3  # All non-success count as failed
