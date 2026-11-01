"""Continuous fetcher that orchestrates all source workers.

This module provides the main entry point for the continuous fetch scheduler.
It spawns and manages one worker per data source.
"""

import asyncio
from typing import Any

import structlog

from ecox_platform.config import settings
from ecox_platform.infrastructure.cache import Cache, get_cache
from ecox_platform.infrastructure.database import DatabaseManager, get_db_manager
from ecox_platform.scheduler.source_worker import SourceWorker
from ecox_platform.sources.eurostat.repository import EurostatRepository
from ecox_platform.sources.eurostat.service import EurostatService
from ecox_platform.sources.fred.repository import FredRepository
from ecox_platform.sources.fred.service import FredService
from ecox_platform.sources.nbs.repository import NbsRepository
from ecox_platform.sources.nbs.service import NbsService
from ecox_platform.sources.oecd.repository import OecdRepository
from ecox_platform.sources.oecd.service import OecdService
from ecox_platform.sources.ons.repository import OnsRepository
from ecox_platform.sources.ons.service import OnsService

logger = structlog.get_logger(__name__)

# List of all supported sources
ALL_SOURCES = ["eurostat", "fred", "oecd", "nbs", "ons"]


class ContinuousFetcher:
    """Orchestrates continuous dataset fetching across all sources.

    Features:
    - Spawns one worker per source
    - Monitors worker health
    - Provides aggregated status
    - Graceful shutdown
    """

    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        cache: Cache | None = None,
        sources: list[str] | None = None,
    ) -> None:
        """Initialize the continuous fetcher.

        Args:
            db_manager: Database manager (uses global if not provided)
            cache: Cache instance (uses global if not provided)
            sources: List of sources to enable (defaults to all)
        """
        self.db_manager = db_manager or get_db_manager()
        self.cache = cache or get_cache()
        self.enabled_sources = sources or ALL_SOURCES

        self.workers: dict[str, SourceWorker] = {}
        self.tasks: dict[str, asyncio.Task[None]] = {}
        self.is_running = False

        logger.info(
            "Continuous fetcher initialized",
            enabled_sources=self.enabled_sources,
        )

    def _create_service(self, source: str) -> Any:
        """Create a service instance for a source.

        Args:
            source: Source name

        Returns:
            Service instance

        Raises:
            ValueError: If source is not supported
        """
        if source == "eurostat":
            eurostat_config = settings.get_source_config("eurostat")
            eurostat_repository = EurostatRepository(rate_limit=eurostat_config.rate_limit)
            return EurostatService(repository=eurostat_repository, cache=self.cache)

        if source == "fred":
            fred_config = settings.get_source_config("fred")
            api_key = settings.fred_api_key
            if not api_key:
                raise ValueError("FRED API key not configured (set ECOX_FRED_API_KEY)")
            fred_repository = FredRepository(api_key=api_key, rate_limit=fred_config.rate_limit)
            return FredService(repository=fred_repository, cache=self.cache)

        if source == "ons":
            ons_config = settings.get_source_config("ons")
            ons_repository = OnsRepository(rate_limit=ons_config.rate_limit)
            return OnsService(repository=ons_repository, cache=self.cache)

        if source == "oecd":
            oecd_config = settings.get_source_config("oecd")
            oecd_repository = OecdRepository(rate_limit=oecd_config.rate_limit)
            return OecdService(repository=oecd_repository, cache=self.cache)

        if source == "nbs":
            nbs_config = settings.get_source_config("nbs")
            nbs_repository = NbsRepository(rate_limit=nbs_config.rate_limit)
            return NbsService(repository=nbs_repository, cache=self.cache)

        raise ValueError(f"Unsupported source: {source}")

    def _create_worker(self, source: str) -> SourceWorker | None:
        """Create a worker for a source.

        Args:
            source: Source name

        Returns:
            SourceWorker instance or None if source not implemented
        """
        try:
            service = self._create_service(source)
            config = settings.get_source_config(source)

            return SourceWorker(
                source_name=source,
                service=service,
                db_manager=self.db_manager,
                config=config,
            )
        except ValueError as e:
            logger.error(
                "Could not create worker - missing configuration",
                source=source,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to create worker",
                source=source,
                error=str(e),
            )
            return None

    async def start(self) -> None:
        """Start all source workers."""
        if self.is_running:
            logger.warning("Continuous fetcher already running")
            return

        self.is_running = True
        logger.info("Starting continuous fetcher")

        # Track skipped sources for startup summary
        disabled_sources: list[str] = []
        failed_sources: list[str] = []

        # Create and start workers for each source
        for source in self.enabled_sources:
            config = settings.get_source_config(source)
            if not config.enabled:
                logger.info("Source disabled, skipping", source=source)
                disabled_sources.append(source)
                continue

            worker = self._create_worker(source)
            if worker is None:
                failed_sources.append(source)
                continue

            self.workers[source] = worker
            task = asyncio.create_task(worker.run(), name=f"worker-{source}")
            self.tasks[source] = task

            logger.info("Worker started", source=source)

        logger.info(
            "Continuous fetcher started",
            active_workers=list(self.workers.keys()),
            disabled_sources=disabled_sources,
            failed_sources=failed_sources,
        )

    async def stop(self) -> None:
        """Stop all source workers gracefully."""
        if not self.is_running:
            return

        logger.info("Stopping continuous fetcher")
        self.is_running = False

        # Signal all workers to stop
        for worker in self.workers.values():
            worker.stop()

        # Cancel all tasks
        for task in self.tasks.values():
            task.cancel()

        # Wait for all tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)

        # Close service resources
        for source, worker in self.workers.items():
            try:
                if hasattr(worker.service, "repository") and hasattr(
                    worker.service.repository, "close"
                ):
                    await worker.service.repository.close()
            except Exception as e:
                logger.error(
                    "Error closing service",
                    source=source,
                    error=str(e),
                )

        self.workers.clear()
        self.tasks.clear()

        logger.info("Continuous fetcher stopped")

    def status(self) -> dict[str, Any]:
        """Get aggregated status from all workers.

        Returns:
            Dictionary with fetcher status
        """
        worker_statuses = {source: worker.status() for source, worker in self.workers.items()}

        total_fetched = sum(w.datasets_fetched for w in self.workers.values())
        total_failed = sum(w.datasets_failed for w in self.workers.values())

        return {
            "is_running": self.is_running,
            "enabled_sources": self.enabled_sources,
            "active_workers": list(self.workers.keys()),
            "total_datasets_fetched": total_fetched,
            "total_datasets_failed": total_failed,
            "workers": worker_statuses,
        }

    async def run_single_cycle(self, source: str) -> dict[str, Any]:
        """Run a single fetch cycle for a specific source.

        Useful for testing or manual triggering.

        Args:
            source: Source name to fetch

        Returns:
            Dictionary with cycle results
        """
        if source in self.workers:
            return await self.workers[source].run_cycle()

        # Create temporary worker
        worker = self._create_worker(source)
        if worker is None:
            return {"error": f"Could not create worker for {source}"}

        try:
            return await worker.run_cycle()
        finally:
            if hasattr(worker.service, "repository") and hasattr(
                worker.service.repository, "close"
            ):
                await worker.service.repository.close()


# Global fetcher instance
_fetcher: ContinuousFetcher | None = None


def get_fetcher() -> ContinuousFetcher:
    """Get the global continuous fetcher instance.

    Returns:
        ContinuousFetcher instance
    """
    global _fetcher
    if _fetcher is None:
        _fetcher = ContinuousFetcher()
    return _fetcher


async def start_fetcher() -> ContinuousFetcher:
    """Start the global continuous fetcher.

    Returns:
        ContinuousFetcher instance
    """
    fetcher = get_fetcher()
    await fetcher.start()
    return fetcher


async def stop_fetcher() -> None:
    """Stop the global continuous fetcher."""
    global _fetcher
    if _fetcher is not None:
        await _fetcher.stop()
        _fetcher = None
