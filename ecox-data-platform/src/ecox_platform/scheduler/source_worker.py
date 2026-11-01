"""Source worker for continuous dataset fetching.

Each source has its own worker that continuously discovers and fetches datasets,
respecting rate limits and concurrency constraints.

Multi-Queue Architecture:
- Fast queue (2-3 concurrent): Small/medium datasets with 5-min timeout
- Slow queue (1 concurrent): Large datasets with 30-min timeout
- Both queues run in parallel with asyncio.gather()
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog
from ecox_shared.models import Dataset, SkippedDataset
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select

from ecox_platform.config import SourceConfig
from ecox_platform.infrastructure.database import DatabaseManager
from ecox_platform.logging_config import truncate_error
from ecox_platform.sources.base.service import BaseService

logger = structlog.get_logger(__name__)

# Backoff intervals for failed datasets (in hours)
BACKOFF_HOURS = [1, 4, 12, 24, 48]  # Exponential-ish backoff

# Timeout settings (in seconds)
FAST_QUEUE_TIMEOUT = 300  # 5 minutes for small/medium datasets
SLOW_QUEUE_TIMEOUT = 1800  # 30 minutes for large datasets

# Consecutive failure threshold per queue (stop early if rate limited)
QUEUE_MAX_CONSECUTIVE_FAILURES = 5


@dataclass
class FailureRecord:
    """Tracks failure state for a dataset."""

    failed_at: datetime
    failure_count: int
    error_message: str


class SourceWorker:
    """Worker that continuously fetches datasets from a single source.

    Features:
    - Discovers all available datasets from the source
    - Identifies stale datasets (older than refresh_hours)
    - Fetches with rate limiting and concurrency control
    - Reports status and statistics
    """

    def __init__(
        self,
        source_name: str,
        service: BaseService,
        db_manager: DatabaseManager,
        config: SourceConfig,
    ) -> None:
        """Initialize the source worker.

        Args:
            source_name: Name of the data source (e.g., "eurostat")
            service: Service instance for fetching data
            db_manager: Database manager for storing data
            config: Source-specific configuration
        """
        self.source_name = source_name
        self.service = service
        self.db_manager = db_manager
        self.config = config

        # Multi-queue concurrency control
        # Fast queue: gets most concurrent slots for small/medium datasets
        fast_slots = max(2, config.max_concurrent - 1)
        # Slow queue: 1 concurrent slot for large datasets (don't hog bandwidth)
        slow_slots = 1
        self.fast_semaphore = asyncio.Semaphore(fast_slots)
        self.slow_semaphore = asyncio.Semaphore(slow_slots)

        # Known large dataset agencies (OECD-specific: CFE = regional, EDS = education drilldowns)
        # These datasets are 100-300MB and take 30+ minutes to download
        self.large_agencies: set[str] = {"CFE", "EDS"}

        # Status tracking
        self.is_running = False
        self.last_activity: datetime | None = None
        self.datasets_fetched = 0
        self.datasets_failed = 0
        self.current_task: str | None = None

        # Failure tracking for backoff
        self._failed_datasets: dict[str, FailureRecord] = {}

        # Timeout tracking: datasets that consistently timeout are marked "too large"
        # These are skipped until restart to avoid wasting time retrying
        self._timeout_datasets: set[str] = set()
        self._timeout_counts: dict[str, int] = {}
        self._timeout_threshold = 2  # Mark as "too large" after 2 timeouts

        # Server error tracking: datasets that return 5xx errors consistently
        # These are API bugs (not our fault) - skip them to make progress
        self._server_error_datasets: set[str] = set()
        self._server_error_counts: dict[str, int] = {}
        self._server_error_threshold = 1  # Mark as broken after 1 failure (server bugs persist)

        logger.info(
            "Source worker initialized",
            source=source_name,
            rate_limit=config.rate_limit,
            max_concurrent=config.max_concurrent,
            fast_slots=fast_slots,
            slow_slots=slow_slots,
            refresh_hours=config.refresh_hours,
        )

    def _is_in_backoff(self, dataset_code: str) -> bool:
        """Check if a dataset is in backoff period after a failure.

        Args:
            dataset_code: The dataset code to check

        Returns:
            True if the dataset should be skipped due to recent failure
        """
        record = self._failed_datasets.get(dataset_code)
        if not record:
            return False

        # Calculate backoff duration based on failure count
        backoff_index = min(record.failure_count - 1, len(BACKOFF_HOURS) - 1)
        backoff_hours = BACKOFF_HOURS[backoff_index]
        backoff_until = record.failed_at + timedelta(hours=backoff_hours)

        return datetime.now() < backoff_until

    def _record_failure(self, dataset_code: str, error_message: str) -> None:
        """Record a dataset failure for backoff tracking.

        Args:
            dataset_code: The dataset that failed
            error_message: Error message from the failure
        """
        existing = self._failed_datasets.get(dataset_code)
        if existing:
            # Increment failure count
            self._failed_datasets[dataset_code] = FailureRecord(
                failed_at=datetime.now(),
                failure_count=existing.failure_count + 1,
                error_message=error_message,
            )
        else:
            # First failure
            self._failed_datasets[dataset_code] = FailureRecord(
                failed_at=datetime.now(),
                failure_count=1,
                error_message=error_message,
            )

        record = self._failed_datasets[dataset_code]
        backoff_index = min(record.failure_count - 1, len(BACKOFF_HOURS) - 1)
        backoff_hours = BACKOFF_HOURS[backoff_index]

        logger.info(
            "Dataset failure recorded",
            source=self.source_name,
            dataset_code=dataset_code,
            failure_count=record.failure_count,
            backoff_hours=backoff_hours,
        )

    def _clear_failure(self, dataset_code: str) -> None:
        """Clear failure record after successful fetch.

        Args:
            dataset_code: The dataset that succeeded
        """
        if dataset_code in self._failed_datasets:
            del self._failed_datasets[dataset_code]
            logger.info(
                "Dataset failure cleared",
                source=self.source_name,
                dataset_code=dataset_code,
            )

    def _is_large_dataset(self, dataset_meta: dict[str, Any]) -> bool:
        """Check if a dataset is from a known large agency.

        Large agencies (CFE, EDS) produce datasets that are 100-300MB and
        take 30+ minutes to download. These go to the slow queue.

        Args:
            dataset_meta: Dataset metadata dictionary

        Returns:
            True if dataset is from a large agency
        """
        # Check agency_id field (used by OECD)
        agency_id = dataset_meta.get("agency_id", "")
        for large_agency in self.large_agencies:
            if large_agency in agency_id:
                return True

        # Check dataset code for agency prefix (e.g., "OECD.CFE.EDS,DSD_...")
        code = dataset_meta.get("code", "")
        for large_agency in self.large_agencies:
            if f".{large_agency}." in code or f".{large_agency}," in code:
                return True

        return False

    def _record_timeout(self, dataset_code: str) -> None:
        """Record a timeout and mark as 'too large' after threshold.

        After 2 timeouts, the dataset is marked as "too large for timeout"
        and will be skipped in future cycles until restart.

        Args:
            dataset_code: The dataset that timed out
        """
        self._timeout_counts[dataset_code] = self._timeout_counts.get(dataset_code, 0) + 1
        count = self._timeout_counts[dataset_code]

        if count >= self._timeout_threshold:
            self._timeout_datasets.add(dataset_code)
            logger.warning(
                "Dataset marked as too large for timeout",
                source=self.source_name,
                dataset_code=dataset_code,
                timeout_count=count,
                action="skipping_until_restart",
            )
        else:
            logger.info(
                "Dataset timeout recorded",
                source=self.source_name,
                dataset_code=dataset_code,
                timeout_count=count,
                threshold=self._timeout_threshold,
            )

    def _clear_timeout(self, dataset_code: str) -> None:
        """Clear timeout count after successful fetch.

        If a dataset succeeds, its timeout count is reset
        (maybe it got smaller or network improved).

        Args:
            dataset_code: The dataset that succeeded
        """
        if dataset_code in self._timeout_counts:
            del self._timeout_counts[dataset_code]

    def should_skip_timeout_dataset(self, dataset_code: str) -> bool:
        """Check if dataset is marked as too large.

        Args:
            dataset_code: The dataset code to check

        Returns:
            True if the dataset should be skipped due to repeated timeouts
        """
        return dataset_code in self._timeout_datasets

    def get_timeout_datasets(self) -> list[str]:
        """Return list of datasets marked as too large.

        These datasets have timed out twice and are skipped until restart.
        Exposed via /health API for manual intervention.

        Returns:
            List of dataset codes that are too large
        """
        return list(self._timeout_datasets)

    def _record_server_error(self, dataset_code: str) -> None:
        """Record a 5xx server error and mark as broken after threshold.

        Server errors (500, 502, 503, 504) are typically API bugs,
        not transient issues. Mark datasets as broken after 1 failure
        to avoid wasting time retrying known-broken endpoints.

        Args:
            dataset_code: The dataset that returned a 5xx error
        """
        self._server_error_counts[dataset_code] = self._server_error_counts.get(dataset_code, 0) + 1
        count = self._server_error_counts[dataset_code]

        if count >= self._server_error_threshold:
            self._server_error_datasets.add(dataset_code)
            logger.warning(
                "Dataset marked as server-broken (5xx error)",
                source=self.source_name,
                dataset_code=dataset_code,
                error_count=count,
                action="skipping_until_restart",
            )
        else:
            logger.info(
                "Dataset server error recorded",
                source=self.source_name,
                dataset_code=dataset_code,
                error_count=count,
                threshold=self._server_error_threshold,
            )

    def _clear_server_error(self, dataset_code: str) -> None:
        """Clear server error count after successful fetch.

        If a dataset succeeds, its error count is reset
        (maybe the API bug was fixed).

        Args:
            dataset_code: The dataset that succeeded
        """
        if dataset_code in self._server_error_counts:
            del self._server_error_counts[dataset_code]

    def should_skip_server_error_dataset(self, dataset_code: str) -> bool:
        """Check if dataset is marked as having persistent server errors.

        Args:
            dataset_code: The dataset code to check

        Returns:
            True if the dataset should be skipped due to 5xx errors
        """
        return dataset_code in self._server_error_datasets

    def get_server_error_datasets(self) -> list[str]:
        """Return list of datasets marked as server-broken.

        These datasets return 5xx errors and are skipped until restart.
        Exposed via /health API for monitoring.

        Returns:
            List of dataset codes with server errors
        """
        return list(self._server_error_datasets)

    async def _discover_datasets(self) -> list[dict[str, Any]]:
        """Discover all available datasets from the source.

        Uses a database session to enable TOC caching.

        Returns:
            List of dataset metadata dictionaries
        """
        try:
            async with self.db_manager.get_session() as session:
                datasets = await self.service.repository.list_discoverable_datasets(session=session)
            logger.info(
                "Discovered datasets",
                source=self.source_name,
                count=len(datasets),
            )
            return datasets
        except Exception as e:
            logger.error(
                "Failed to discover datasets",
                source=self.source_name,
                error=truncate_error(e),
            )
            return []

    async def _get_stale_datasets(self, discovered: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Find datasets that need to be refreshed using smart refresh.

        Smart refresh logic:
        - New datasets (never fetched): Always fetch - high priority
        - Existing datasets: Only refresh if source's last_update changed

        This avoids re-checking datasets whose source data hasn't changed,
        dramatically reducing API calls when Eurostat hasn't published updates.

        Args:
            discovered: List of discovered dataset metadata (from TOC)

        Returns:
            List of dataset metadata needing refresh, with new datasets first
        """
        new_datasets = []  # Never fetched - high priority
        stale_datasets = []  # Source has updated - needs refresh
        unchanged = 0  # Source unchanged - skip
        skipped_large = 0  # Count of skipped large datasets
        skipped_backoff = 0  # Count of datasets in backoff period

        async with self.db_manager.get_session() as session:
            for dataset_meta in discovered:
                dataset_code = dataset_meta.get("code")
                if not dataset_code:
                    continue

                # Skip datasets in backoff period after recent failure
                if self._is_in_backoff(dataset_code):
                    skipped_backoff += 1
                    continue

                # Skip datasets exceeding max_values threshold
                values_count = dataset_meta.get("values_count", 0)
                if self.config.max_values > 0 and values_count > self.config.max_values:
                    skipped_large += 1
                    # Record skipped dataset using UPSERT (atomic, ignores duplicates)
                    stmt = (
                        insert(SkippedDataset)
                        .values(
                            source=self.source_name,
                            dataset_code=dataset_code,
                            reason="too_large",
                            values_count=values_count,
                            threshold=self.config.max_values,
                        )
                        .on_conflict_do_nothing(index_elements=["source", "dataset_code"])
                    )
                    await session.execute(stmt)
                    continue

                # Get source's last_update from TOC metadata
                source_last_update = dataset_meta.get("last_update")

                # Check if dataset exists in our database
                statement = select(Dataset).where(
                    Dataset.code == dataset_code,
                    Dataset.source == self.source_name,
                )
                result = await session.execute(statement)
                existing = result.scalar_one_or_none()

                if existing is None:
                    # Never fetched - prioritize these
                    new_datasets.append(dataset_meta)
                elif existing.source_last_update != source_last_update:
                    # Source has been updated since we last fetched - needs refresh
                    stale_datasets.append(dataset_meta)
                else:
                    # Source unchanged - skip (smart refresh optimization)
                    unchanged += 1

            # Commit skipped records after loop
            await session.commit()

        # Return new datasets first, then stale updates
        combined = new_datasets + stale_datasets

        logger.info(
            "Smart refresh: found datasets needing update",
            source=self.source_name,
            new_count=len(new_datasets),
            stale_count=len(stale_datasets),
            unchanged=unchanged,
            skipped_large=skipped_large,
            skipped_backoff=skipped_backoff,
            total_discovered=len(discovered),
        )
        return combined

    async def _fetch_dataset(
        self,
        dataset_meta: dict[str, Any],
        semaphore: asyncio.Semaphore,
        timeout_seconds: float,
    ) -> tuple[bool, bool, bool, bool]:
        """Fetch a single dataset with concurrency control and timeout.

        Args:
            dataset_meta: Dataset metadata dictionary
            semaphore: Semaphore to use for concurrency control
            timeout_seconds: Maximum time allowed for fetch

        Returns:
            Tuple of (success, is_skipped, is_server_error, is_rate_limited):
            - success: True if fetch succeeded
            - is_skipped: True if dataset was skipped (not counted as failure)
            - is_server_error: True if failed due to 5xx server error (API bug)
            - is_rate_limited: True if failed due to 429 rate limit
        """
        dataset_code = dataset_meta.get("code", "unknown")

        # Skip datasets marked as "too large for timeout"
        if self.should_skip_timeout_dataset(dataset_code):
            logger.debug(
                "Skipping too-large dataset",
                source=self.source_name,
                dataset_code=dataset_code,
                reason="exceeded_timeout_threshold",
            )
            return (
                False,
                True,
                False,
                False,
            )  # Not success, IS skipped, not server error, not rate limited

        # Skip datasets marked as having persistent server errors
        if self.should_skip_server_error_dataset(dataset_code):
            logger.debug(
                "Skipping server-broken dataset",
                source=self.source_name,
                dataset_code=dataset_code,
                reason="persistent_5xx_error",
            )
            return (
                False,
                True,
                False,
                False,
            )  # Not success, IS skipped, not server error, not rate limited

        async with semaphore:
            self.current_task = dataset_code
            self.last_activity = datetime.now()

            try:
                logger.info(
                    "Fetching dataset",
                    source=self.source_name,
                    dataset_code=dataset_code,
                    timeout_seconds=timeout_seconds,
                )

                async with self.db_manager.get_session() as session:
                    # Wrap fetch in timeout
                    await asyncio.wait_for(
                        self.service.fetch_and_store(
                            dataset_code=dataset_code,
                            session=session,  # type: ignore[arg-type]
                        ),
                        timeout=timeout_seconds,
                    )

                self.datasets_fetched += 1
                self._clear_failure(dataset_code)
                self._clear_timeout(dataset_code)  # Reset timeout count on success
                self._clear_server_error(dataset_code)  # Reset server error count on success
                logger.info(
                    "Dataset fetched successfully",
                    source=self.source_name,
                    dataset_code=dataset_code,
                )
                return (
                    True,
                    False,
                    False,
                    False,
                )  # Success, not skipped, not server error, not rate limited

            except TimeoutError:
                self.datasets_failed += 1
                self._record_timeout(dataset_code)
                logger.warning(
                    "Dataset fetch timed out",
                    source=self.source_name,
                    dataset_code=dataset_code,
                    timeout_seconds=timeout_seconds,
                )
                return (
                    False,
                    False,
                    False,
                    False,
                )  # Failed, not skipped, not server error, not rate limited

            except NotImplementedError:
                # Service not yet implemented (stub)
                logger.warning(
                    "Service not implemented",
                    source=self.source_name,
                    dataset_code=dataset_code,
                )
                return (
                    False,
                    True,
                    False,
                    False,
                )  # Treat as skip (not our fault), not server error, not rate limited

            except Exception as e:
                self.datasets_failed += 1
                self._record_failure(dataset_code, str(e))

                # Check for 5xx server errors and 429 rate limiting
                # First try to get status code from exception response attribute
                is_server_error = False
                is_rate_limited = False
                response = getattr(e, "response", None)
                if response is not None and hasattr(response, "status_code"):
                    status_code = response.status_code
                    is_server_error = 500 <= status_code < 600
                    is_rate_limited = status_code == 429
                else:
                    # Fallback: check for status code patterns in error message
                    # Use more specific patterns to avoid false positives (e.g., dataset names, port numbers)
                    error_str = str(e)
                    is_server_error = any(
                        f"'{code}" in error_str or f" {code} " in error_str
                        for code in ["500", "502", "503", "504"]
                    )
                    is_rate_limited = "'429" in error_str or "Too Many Requests" in error_str

                if is_server_error:
                    self._record_server_error(dataset_code)

                if is_rate_limited:
                    logger.warning(
                        "Rate limited by API",
                        source=self.source_name,
                        dataset_code=dataset_code,
                    )
                else:
                    logger.error(
                        "Failed to fetch dataset",
                        source=self.source_name,
                        dataset_code=dataset_code,
                        error=truncate_error(e),
                    )
                return (
                    False,
                    False,
                    is_server_error,
                    is_rate_limited,
                )  # Failed, not skipped, maybe server error, maybe rate limited

            finally:
                self.current_task = None

    async def _process_queue(
        self,
        datasets: list[dict[str, Any]],
        semaphore: asyncio.Semaphore,
        timeout_seconds: float,
        queue_name: str,
    ) -> dict[str, int]:
        """Process a queue of datasets with given semaphore and timeout.

        Each queue runs independently with its own consecutive failure counter.
        If 5 consecutive failures occur, the queue stops early (likely broken).

        Skipped datasets (timeout/server-error marked) DON'T count toward
        consecutive failures, allowing the queue to find working datasets.

        5xx server errors also DON'T count toward consecutive failures because
        they are API bugs, not rate limiting. The queue should keep running to
        mark all broken datasets and eventually find working ones.

        429 rate limit errors trigger a 60-second pause instead of stopping,
        allowing the rate limit window to reset before continuing.

        Args:
            datasets: List of dataset metadata to process
            semaphore: Semaphore for concurrency control
            timeout_seconds: Timeout for each dataset fetch
            queue_name: Name of the queue for logging ("fast" or "slow")

        Returns:
            Dictionary with fetched, failed, and skipped counts
        """
        fetched = 0
        failed = 0
        skipped = 0
        server_errors = 0
        rate_limited = 0
        consecutive_failures = 0

        for dataset_meta in datasets:
            success, is_skipped, is_server_error, is_rate_limited = await self._fetch_dataset(
                dataset_meta, semaphore, timeout_seconds
            )

            if success:
                fetched += 1
                consecutive_failures = 0  # Reset on success
            elif is_skipped:
                skipped += 1
                # DON'T increment consecutive_failures for skipped datasets
                # This allows the queue to skip broken datasets and find working ones
            elif is_server_error:
                failed += 1
                server_errors += 1
                # DON'T increment consecutive_failures for 5xx server errors
                # These are API bugs, not rate limiting - queue should keep running
                # to mark all broken datasets and find working ones
            elif is_rate_limited:
                failed += 1
                rate_limited += 1
                # Rate limited - pause and let rate limit window reset
                # DON'T count toward consecutive failures (server is working, just busy)
                logger.warning(
                    f"Pausing {queue_name} queue for 60s due to rate limiting",
                    source=self.source_name,
                    queue=queue_name,
                    rate_limited_count=rate_limited,
                    fetched=fetched,
                )
                await asyncio.sleep(60)  # Wait for rate limit window to reset
                consecutive_failures = 0  # Reset counter after pause
            else:
                failed += 1
                consecutive_failures += 1

                # Stop early if we're hitting persistent errors (non-5xx, non-rate-limit)
                if consecutive_failures >= QUEUE_MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        f"Stopping {queue_name} queue early due to consecutive failures",
                        source=self.source_name,
                        queue=queue_name,
                        consecutive_failures=consecutive_failures,
                        fetched=fetched,
                        failed=failed,
                        skipped=skipped,
                        server_errors=server_errors,
                        rate_limited=rate_limited,
                        remaining=len(datasets) - fetched - failed - skipped,
                    )
                    break

            # Rate limiting: wait between requests (shared across all queues)
            # Skip rate limit delay for skipped datasets (no API call made)
            if not is_skipped:
                await asyncio.sleep(1.0 / self.config.rate_limit)

        logger.info(
            f"{queue_name.capitalize()} queue completed",
            source=self.source_name,
            queue=queue_name,
            fetched=fetched,
            failed=failed,
            skipped=skipped,
            server_errors=server_errors,
            rate_limited=rate_limited,
            total=len(datasets),
        )

        return {
            "fetched": fetched,
            "failed": failed,
            "skipped": skipped,
            "server_errors": server_errors,
            "rate_limited": rate_limited,
        }

    async def run_cycle(self) -> dict[str, Any]:
        """Run one fetch cycle: discover, find stale, split into queues, fetch.

        Multi-Queue Architecture:
        - Fast queue (2-3 concurrent, 5-min timeout): Small/medium datasets
        - Slow queue (1 concurrent, 30-min timeout): Large datasets (CFE, EDS)
        - Both queues run in parallel with asyncio.gather()

        Returns:
            Dictionary with cycle results
        """
        cycle_start = datetime.now()

        # Discover available datasets
        discovered = await self._discover_datasets()
        if not discovered:
            return {
                "source": self.source_name,
                "discovered": 0,
                "stale": 0,
                "fetched": 0,
                "failed": 0,
                "skipped": 0,
                "fast_queue": {"fetched": 0, "failed": 0, "skipped": 0, "total": 0},
                "slow_queue": {"fetched": 0, "failed": 0, "skipped": 0, "total": 0},
                "duration_seconds": 0,
            }

        # Find stale datasets
        stale = await self._get_stale_datasets(discovered)
        if not stale:
            logger.info(
                "No stale datasets",
                source=self.source_name,
                total_datasets=len(discovered),
            )
            return {
                "source": self.source_name,
                "discovered": len(discovered),
                "stale": 0,
                "fetched": 0,
                "failed": 0,
                "skipped": 0,
                "fast_queue": {"fetched": 0, "failed": 0, "skipped": 0, "total": 0},
                "slow_queue": {"fetched": 0, "failed": 0, "skipped": 0, "total": 0},
                "duration_seconds": 0,
            }

        # Split datasets into fast and slow queues
        fast_datasets = [d for d in stale if not self._is_large_dataset(d)]
        slow_datasets = [d for d in stale if self._is_large_dataset(d)]

        # Randomize order to avoid clustering of broken datasets at the start
        # This prevents consecutive failures from stopping the queue early
        # when broken datasets happen to be alphabetically first (e.g., "ashe-*")
        random.shuffle(fast_datasets)
        random.shuffle(slow_datasets)

        logger.info(
            "Splitting datasets into queues",
            source=self.source_name,
            fast_count=len(fast_datasets),
            slow_count=len(slow_datasets),
        )

        # Process both queues in parallel with asyncio.gather()
        fast_task = self._process_queue(
            fast_datasets, self.fast_semaphore, FAST_QUEUE_TIMEOUT, "fast"
        )
        slow_task = self._process_queue(
            slow_datasets, self.slow_semaphore, SLOW_QUEUE_TIMEOUT, "slow"
        )

        fast_results, slow_results = await asyncio.gather(fast_task, slow_task)

        # Combine results
        total_fetched = fast_results["fetched"] + slow_results["fetched"]
        total_failed = fast_results["failed"] + slow_results["failed"]
        total_skipped = fast_results["skipped"] + slow_results["skipped"]

        duration = (datetime.now() - cycle_start).total_seconds()

        logger.info(
            "Fetch cycle completed",
            source=self.source_name,
            discovered=len(discovered),
            stale=len(stale),
            fetched=total_fetched,
            failed=total_failed,
            skipped=total_skipped,
            fast_queue=fast_results,
            slow_queue=slow_results,
            duration_seconds=duration,
        )

        return {
            "source": self.source_name,
            "discovered": len(discovered),
            "stale": len(stale),
            "fetched": total_fetched,
            "failed": total_failed,
            "skipped": total_skipped,
            "fast_queue": {**fast_results, "total": len(fast_datasets)},
            "slow_queue": {**slow_results, "total": len(slow_datasets)},
            "duration_seconds": duration,
        }

    async def run(self) -> None:
        """Run the worker continuously.

        This method runs forever, fetching stale datasets in cycles.
        Between cycles, it sleeps for a period based on refresh_hours.
        """
        self.is_running = True
        logger.info("Source worker started", source=self.source_name)

        while self.is_running:
            try:
                await self.run_cycle()

                # Sleep between cycles (check every 10% of refresh period)
                sleep_seconds = (self.config.refresh_hours * 3600) / 10
                sleep_seconds = min(sleep_seconds, 3600)  # Cap at 1 hour
                sleep_seconds = max(sleep_seconds, 60)  # At least 1 minute

                logger.debug(
                    "Worker sleeping",
                    source=self.source_name,
                    sleep_seconds=sleep_seconds,
                )
                await asyncio.sleep(sleep_seconds)

            except asyncio.CancelledError:
                logger.info("Source worker cancelled", source=self.source_name)
                break

            except Exception as e:
                logger.error(
                    "Worker cycle failed",
                    source=self.source_name,
                    error=truncate_error(e),
                )
                # Wait before retrying after error
                await asyncio.sleep(60)

        self.is_running = False
        logger.info("Source worker stopped", source=self.source_name)

    def stop(self) -> None:
        """Signal the worker to stop."""
        self.is_running = False

    def status(self) -> dict[str, Any]:
        """Get worker status.

        Returns:
            Dictionary with worker status including timeout and server error tracking
        """
        return {
            "source": self.source_name,
            "is_running": self.is_running,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "datasets_fetched": self.datasets_fetched,
            "datasets_failed": self.datasets_failed,
            "datasets_in_backoff": len(self._failed_datasets),
            "timeout_datasets": self.get_timeout_datasets(),
            "timeout_datasets_count": len(self._timeout_datasets),
            "server_error_datasets": self.get_server_error_datasets(),
            "server_error_datasets_count": len(self._server_error_datasets),
            "current_task": self.current_task,
            "config": {
                "rate_limit": self.config.rate_limit,
                "max_concurrent": self.config.max_concurrent,
                "refresh_hours": self.config.refresh_hours,
            },
        }
