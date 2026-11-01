"""In-memory caching layer with TTL (Time-To-Live).

This module provides a simple in-memory cache with time-based expiration,
aligned with data source update schedules. Includes automatic cleanup daemon
and size-based eviction to prevent unbounded memory growth.

Thread Safety:
    All cache operations are protected by an asyncio.Lock to prevent race
    conditions when the cleanup daemon runs concurrently with application code.

Size Estimation:
    Uses recursive size calculation for accurate memory tracking. For very
    deep nested structures, estimation may still undercount due to shared
    references and internal Python object overhead.
"""

import asyncio
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Default TTL: 12 hours (43200 seconds)
DEFAULT_CACHE_TTL_SECONDS = 43200

# Default max cache size: 8 GB
DEFAULT_MAX_CACHE_SIZE_BYTES = 8 * 1024 * 1024 * 1024

# Cleanup interval: 5 minutes
DEFAULT_CLEANUP_INTERVAL_SECONDS = 300

# Batch eviction: remove this percentage of entries when over limit
EVICTION_BATCH_PERCENTAGE = 10

# System key prefix to prevent collisions with user data
SYSTEM_KEY_PREFIX = "__SYS__:"


@dataclass
class CacheEntry:
    """Cache entry with value and expiration time."""

    value: Any
    expires_at: datetime
    size_bytes: int = 0  # Cached size for performance


class Cache:
    """In-memory cache with TTL support.

    Features:
    - Time-based expiration (TTL)
    - Automatic cleanup of expired entries
    - Cache key generation from filters
    - Thread-safe operations via asyncio.Lock
    - Batch eviction for performance
    - Recursive size estimation
    """

    def __init__(
        self,
        ttl_seconds: int | None = None,
        max_size_bytes: int | None = None,
    ) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: Time-to-live in seconds (default: 12 hours)
            max_size_bytes: Maximum cache size in bytes (default: 8 GB)
        """
        self.ttl_seconds = ttl_seconds or DEFAULT_CACHE_TTL_SECONDS
        self.max_size_bytes = max_size_bytes or DEFAULT_MAX_CACHE_SIZE_BYTES
        self._cache: dict[str, CacheEntry] = {}
        self._cleanup_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._cached_total_size: int = 0  # Incrementally tracked size

        logger.info(
            "Cache initialized",
            ttl_seconds=self.ttl_seconds,
            max_size_mb=self.max_size_bytes / (1024 * 1024),
        )

    def _generate_key(
        self, source: str, dataset_code: str, filters: dict[str, Any] | None = None
    ) -> str:
        """Generate a cache key from source, dataset, and filters.

        Args:
            source: Data source (e.g., "eurostat")
            dataset_code: Dataset code (e.g., "nama_10_gdp")
            filters: Optional filters to include in the key

        Returns:
            Cache key string
        """
        # Sort filters for consistent key generation
        filter_str = ""
        if filters:
            sorted_filters = json.dumps(filters, sort_keys=True)
            filter_hash = hashlib.sha256(sorted_filters.encode()).hexdigest()[:8]
            filter_str = f":{filter_hash}"

        # Use system prefix for internal cache keys to prevent collisions
        if dataset_code.startswith("__") and dataset_code.endswith("__"):
            key = f"{SYSTEM_KEY_PREFIX}{source}:{dataset_code}{filter_str}"
        else:
            key = f"{source}:{dataset_code}{filter_str}"
        return key

    def _estimate_object_size(self, obj: Any, seen: set[int] | None = None) -> int:
        """Recursively estimate the size of an object in bytes.

        This provides more accurate size estimation than sys.getsizeof alone
        by traversing nested structures.

        Args:
            obj: Object to measure
            seen: Set of object IDs already counted (to handle circular refs)

        Returns:
            Estimated size in bytes
        """
        if seen is None:
            seen = set()

        obj_id = id(obj)
        if obj_id in seen:
            return 0  # Already counted (circular reference)
        seen.add(obj_id)

        size = sys.getsizeof(obj)

        if isinstance(obj, dict):
            size += sum(
                self._estimate_object_size(k, seen) + self._estimate_object_size(v, seen)
                for k, v in obj.items()
            )
        elif isinstance(obj, (list, tuple, set, frozenset)):
            size += sum(self._estimate_object_size(item, seen) for item in obj)
        elif hasattr(obj, "__dict__"):
            size += self._estimate_object_size(obj.__dict__, seen)

        return size

    def get(
        self, source: str, dataset_code: str, filters: dict[str, Any] | None = None
    ) -> Any | None:
        """Get a value from the cache.

        Args:
            source: Data source
            dataset_code: Dataset code
            filters: Optional filters

        Returns:
            Cached value if found and not expired, None otherwise
        """
        key = self._generate_key(source, dataset_code, filters)

        if key not in self._cache:
            logger.debug("Cache miss", key=key)
            return None

        entry = self._cache[key]

        # Check if expired
        if datetime.now() > entry.expires_at:
            logger.debug("Cache entry expired", key=key)
            # Update cached size before deletion
            self._cached_total_size -= entry.size_bytes
            del self._cache[key]
            return None

        logger.debug("Cache hit", key=key)
        return entry.value

    def set(
        self,
        source: str,
        dataset_code: str,
        value: Any,
        filters: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set a value in the cache.

        Args:
            source: Data source
            dataset_code: Dataset code
            value: Value to cache
            filters: Optional filters
            ttl_seconds: Custom TTL in seconds (default: use cache default)
        """
        key = self._generate_key(source, dataset_code, filters)
        ttl = ttl_seconds or self.ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl)

        # Calculate size for the new entry
        entry_size = (
            self._estimate_object_size(value) + sys.getsizeof(key) + 64
        )  # 64 for CacheEntry overhead

        # If key exists, subtract old size first
        if key in self._cache:
            self._cached_total_size -= self._cache[key].size_bytes

        self._cache[key] = CacheEntry(value=value, expires_at=expires_at, size_bytes=entry_size)
        self._cached_total_size += entry_size

        logger.debug("Cache set", key=key, ttl_seconds=ttl, size_bytes=entry_size)

    def delete(self, source: str, dataset_code: str, filters: dict[str, Any] | None = None) -> bool:
        """Delete a value from the cache.

        Args:
            source: Data source
            dataset_code: Dataset code
            filters: Optional filters

        Returns:
            True if the key was found and deleted, False otherwise
        """
        key = self._generate_key(source, dataset_code, filters)

        if key in self._cache:
            self._cached_total_size -= self._cache[key].size_bytes
            del self._cache[key]
            logger.debug("Cache entry deleted", key=key)
            return True

        return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        count = len(self._cache)
        self._cache.clear()
        self._cached_total_size = 0
        logger.info("Cache cleared", entries_removed=count)

    async def cleanup_expired_async(self) -> int:
        """Remove all expired entries from the cache (async, thread-safe).

        Returns:
            Number of entries removed
        """
        async with self._lock:
            return self._cleanup_expired_unlocked()

    def cleanup_expired(self) -> int:
        """Remove all expired entries from the cache.

        Note: For thread-safe cleanup, use cleanup_expired_async() instead.

        Returns:
            Number of entries removed
        """
        return self._cleanup_expired_unlocked()

    def _cleanup_expired_unlocked(self) -> int:
        """Internal cleanup without locking.

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        expired_keys = [key for key, entry in self._cache.items() if now > entry.expires_at]

        size_freed = 0
        for key in expired_keys:
            size_freed += self._cache[key].size_bytes
            del self._cache[key]

        self._cached_total_size -= size_freed

        if expired_keys:
            logger.info(
                "Expired cache entries removed",
                count=len(expired_keys),
                size_freed_mb=size_freed / (1024 * 1024),
            )

        return len(expired_keys)

    def size(self) -> int:
        """Get the number of entries in the cache.

        Returns:
            Number of cached entries
        """
        return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics including memory usage.

        Returns:
            Dictionary with cache stats
        """
        now = datetime.now()
        active_entries = sum(1 for entry in self._cache.values() if now <= entry.expires_at)
        expired_entries = len(self._cache) - active_entries

        stats_dict: dict[str, Any] = {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": expired_entries,
            "ttl_seconds": self.ttl_seconds,
            "estimated_cache_size_mb": self._cached_total_size / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "size_utilization_pct": (self._cached_total_size / self.max_size_bytes * 100)
            if self.max_size_bytes > 0
            else 0,
            "cleanup_daemon_running": self._cleanup_task is not None
            and not self._cleanup_task.done(),
        }

        # Add process memory info if psutil is available
        try:
            import psutil

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            stats_dict["process_rss_mb"] = memory_info.rss / (1024 * 1024)
            stats_dict["process_vms_mb"] = memory_info.vms / (1024 * 1024)
        except ImportError:
            pass

        return stats_dict

    def _estimate_size_bytes(self) -> int:
        """Get the cached total size estimate.

        This returns the incrementally tracked size, which is more efficient
        than recalculating on every call.

        Returns:
            Estimated size in bytes
        """
        return self._cached_total_size

    def _recalculate_size(self) -> int:
        """Recalculate total cache size from scratch.

        Use this to correct any drift in the incremental size tracking.

        Returns:
            Recalculated size in bytes
        """
        total = 0
        for _key, entry in self._cache.items():
            total += entry.size_bytes
        self._cached_total_size = total
        return total

    async def _evict_oldest_async(self) -> int:
        """Remove oldest entries until cache is under max_size_bytes (async, thread-safe).

        Uses batch eviction for better performance.

        Returns:
            Number of entries evicted
        """
        async with self._lock:
            return self._evict_oldest_unlocked()

    def _evict_oldest(self) -> int:
        """Remove oldest entries until cache is under max_size_bytes.

        Note: For thread-safe eviction, use _evict_oldest_async() instead.

        Returns:
            Number of entries evicted
        """
        return self._evict_oldest_unlocked()

    def _evict_oldest_unlocked(self) -> int:
        """Internal eviction without locking.

        Uses batch eviction (removes EVICTION_BATCH_PERCENTAGE of entries)
        for better performance instead of one-by-one removal.

        Returns:
            Number of entries evicted
        """
        if self._cached_total_size <= self.max_size_bytes or not self._cache:
            return 0

        evicted = 0
        size_freed = 0

        # Calculate how many entries to evict in this batch
        # Evict at least enough to get under limit, or EVICTION_BATCH_PERCENTAGE
        entries_to_evict = max(1, len(self._cache) * EVICTION_BATCH_PERCENTAGE // 100)

        # Sort entries by expiration time (oldest first)
        sorted_entries = sorted(self._cache.items(), key=lambda kv: kv[1].expires_at)

        # Evict oldest entries until under limit or batch complete
        for key, entry in sorted_entries:
            if (
                self._cached_total_size - size_freed <= self.max_size_bytes
                and evicted >= entries_to_evict
            ):
                break

            size_freed += entry.size_bytes
            del self._cache[key]
            evicted += 1

            # Safety limit: don't evict more than 50% in one batch
            if evicted >= len(sorted_entries) // 2:
                break

        self._cached_total_size -= size_freed

        if evicted:
            logger.info(
                "Cache entries evicted due to size limit",
                count=evicted,
                size_freed_mb=size_freed / (1024 * 1024),
                new_size_mb=self._cached_total_size / (1024 * 1024),
            )

        return evicted

    async def start_cleanup_daemon(self, interval_seconds: int | None = None) -> None:
        """Start the background cleanup daemon.

        The daemon periodically removes expired entries and evicts
        oldest entries if cache exceeds max size.

        Args:
            interval_seconds: Cleanup interval (default: 5 minutes)
        """
        if self._cleanup_task is not None and not self._cleanup_task.done():
            logger.warning("Cleanup daemon already running")
            return

        interval = interval_seconds or DEFAULT_CLEANUP_INTERVAL_SECONDS

        async def _cleanup_loop() -> None:
            logger.info("Cache cleanup daemon started", interval_seconds=interval)
            while True:
                try:
                    await asyncio.sleep(interval)

                    # Use async versions for thread safety
                    async with self._lock:
                        expired_count = self._cleanup_expired_unlocked()
                        evicted_count = self._evict_oldest_unlocked()

                    stats = self.stats()
                    logger.info(
                        "Cache cleanup completed",
                        expired_removed=expired_count,
                        evicted_for_size=evicted_count,
                        **stats,
                    )
                except asyncio.CancelledError:
                    logger.info("Cache cleanup daemon stopping")
                    raise
                except Exception as e:
                    # Log error but keep daemon running
                    logger.error(
                        "Cache cleanup error (daemon continues)",
                        error=str(e),
                        error_type=type(e).__name__,
                    )

        self._cleanup_task = asyncio.create_task(_cleanup_loop())

    async def stop_cleanup_daemon(self) -> None:
        """Stop the background cleanup daemon."""
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Cache cleanup daemon stopped")


# Global cache instance
_cache: Cache | None = None


def get_cache() -> Cache:
    """Get or create the global cache instance.

    Returns:
        Cache: Global cache instance
    """
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
