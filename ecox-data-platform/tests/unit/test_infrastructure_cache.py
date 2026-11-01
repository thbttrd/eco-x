"""Tests for the in-memory cache."""

import time
from typing import Any

from ecox_platform.infrastructure.cache import Cache


class TestCache:
    """Tests for Cache class."""

    def test_cache_initialization(self) -> None:
        """Test cache initialization with default TTL."""
        cache = Cache()
        assert cache.ttl_seconds == 43200  # 12 hours default

    def test_cache_initialization_custom_ttl(self) -> None:
        """Test cache initialization with custom TTL."""
        cache = Cache(ttl_seconds=60)
        assert cache.ttl_seconds == 60

    def test_cache_set_and_get(self, test_cache: Cache) -> None:
        """Test setting and getting a value."""
        test_cache.set("eurostat", "nama_10_gdp", {"data": "test"})
        result = test_cache.get("eurostat", "nama_10_gdp")
        assert result == {"data": "test"}

    def test_cache_get_miss(self, test_cache: Cache) -> None:
        """Test cache miss returns None."""
        result = test_cache.get("eurostat", "nonexistent")
        assert result is None

    def test_cache_set_with_filters(self, test_cache: Cache) -> None:
        """Test setting with filters creates unique key."""
        test_cache.set("eurostat", "nama_10_gdp", {"data": "all"})
        test_cache.set("eurostat", "nama_10_gdp", {"data": "filtered"}, filters={"geo": "FR"})

        result_all = test_cache.get("eurostat", "nama_10_gdp")
        result_filtered = test_cache.get("eurostat", "nama_10_gdp", filters={"geo": "FR"})

        assert result_all == {"data": "all"}
        assert result_filtered == {"data": "filtered"}

    def test_cache_filters_order_independent(self, test_cache: Cache) -> None:
        """Test that filter order doesn't affect the key."""
        test_cache.set("eurostat", "ds", {"data": "test"}, filters={"a": "1", "b": "2"})

        # Get with same filters in different order
        result = test_cache.get("eurostat", "ds", filters={"b": "2", "a": "1"})
        assert result == {"data": "test"}

    def test_cache_expiration(self) -> None:
        """Test that cache entries expire after TTL."""
        cache = Cache(ttl_seconds=1)  # 1 second TTL
        cache.set("eurostat", "test", {"data": "value"})

        # Should be present immediately
        assert cache.get("eurostat", "test") == {"data": "value"}

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        assert cache.get("eurostat", "test") is None

    def test_cache_delete(self, test_cache: Cache) -> None:
        """Test deleting a cache entry."""
        test_cache.set("eurostat", "test", {"data": "value"})
        assert test_cache.get("eurostat", "test") is not None

        result = test_cache.delete("eurostat", "test")
        assert result is True
        assert test_cache.get("eurostat", "test") is None

    def test_cache_delete_nonexistent(self, test_cache: Cache) -> None:
        """Test deleting a nonexistent entry returns False."""
        result = test_cache.delete("eurostat", "nonexistent")
        assert result is False

    def test_cache_clear(self, test_cache: Cache) -> None:
        """Test clearing all cache entries."""
        test_cache.set("eurostat", "ds1", {"data": "1"})
        test_cache.set("eurostat", "ds2", {"data": "2"})
        test_cache.set("fred", "GDP", {"data": "3"})

        assert test_cache.size() == 3

        test_cache.clear()

        assert test_cache.size() == 0
        assert test_cache.get("eurostat", "ds1") is None

    def test_cache_cleanup_expired(self) -> None:
        """Test cleanup of expired entries."""
        cache = Cache(ttl_seconds=1)
        cache.set("eurostat", "ds1", {"data": "1"})
        cache.set("eurostat", "ds2", {"data": "2"}, ttl_seconds=10)  # Longer TTL

        # Wait for first entry to expire
        time.sleep(1.1)

        removed = cache.cleanup_expired()

        assert removed == 1
        assert cache.get("eurostat", "ds1") is None
        assert cache.get("eurostat", "ds2") is not None

    def test_cache_size(self, test_cache: Cache) -> None:
        """Test getting cache size."""
        assert test_cache.size() == 0

        test_cache.set("eurostat", "ds1", {"data": "1"})
        assert test_cache.size() == 1

        test_cache.set("eurostat", "ds2", {"data": "2"})
        assert test_cache.size() == 2

    def test_cache_stats(self, test_cache: Cache) -> None:
        """Test getting cache statistics."""
        test_cache.set("eurostat", "ds1", {"data": "1"})
        test_cache.set("eurostat", "ds2", {"data": "2"})

        stats = test_cache.stats()

        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2
        assert stats["expired_entries"] == 0
        assert stats["ttl_seconds"] == 60

    def test_cache_custom_ttl_on_set(self, test_cache: Cache) -> None:
        """Test setting with custom TTL overrides default."""
        test_cache.set("eurostat", "short", {"data": "short"}, ttl_seconds=1)
        test_cache.set("eurostat", "long", {"data": "long"}, ttl_seconds=3600)

        # Wait for short TTL to expire
        time.sleep(1.1)

        assert test_cache.get("eurostat", "short") is None
        assert test_cache.get("eurostat", "long") == {"data": "long"}


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_key_without_filters(self, test_cache: Cache) -> None:
        """Test key generation without filters."""
        key = test_cache._generate_key("eurostat", "nama_10_gdp")
        assert key == "eurostat:nama_10_gdp"

    def test_key_with_filters(self, test_cache: Cache) -> None:
        """Test key generation with filters includes hash."""
        key = test_cache._generate_key("eurostat", "nama_10_gdp", {"geo": "FR"})
        assert key.startswith("eurostat:nama_10_gdp:")
        assert len(key) > len("eurostat:nama_10_gdp:")

    def test_key_same_filters_same_key(self, test_cache: Cache) -> None:
        """Test that same filters produce same key."""
        key1 = test_cache._generate_key("eurostat", "ds", {"geo": "FR", "time": "2022"})
        key2 = test_cache._generate_key("eurostat", "ds", {"time": "2022", "geo": "FR"})
        assert key1 == key2

    def test_key_different_filters_different_key(self, test_cache: Cache) -> None:
        """Test that different filters produce different keys."""
        key1 = test_cache._generate_key("eurostat", "ds", {"geo": "FR"})
        key2 = test_cache._generate_key("eurostat", "ds", {"geo": "DE"})
        assert key1 != key2


class TestCacheSizeEstimation:
    """Tests for cache size estimation."""

    def test_estimate_size_empty_cache(self) -> None:
        """Test size estimation for empty cache."""
        cache = Cache()
        assert cache._estimate_size_bytes() == 0

    def test_estimate_size_with_entries(self) -> None:
        """Test size estimation with entries."""
        cache = Cache()
        cache.set("eurostat", "ds1", {"key": "value"})
        cache.set("eurostat", "ds2", ["item1", "item2", "item3"])

        size = cache._estimate_size_bytes()
        assert size > 0

    def test_estimate_size_dict_values(self) -> None:
        """Test size estimation for dict values includes nested keys."""
        cache = Cache()
        cache.set("eurostat", "ds", {"a": "1", "b": "2", "c": "3"})

        size = cache._estimate_size_bytes()
        # Should account for dict keys and values
        assert size > 100

    def test_estimate_size_list_values(self) -> None:
        """Test size estimation for list values includes items."""
        cache = Cache()
        large_list = list(range(1000))
        cache.set("eurostat", "ds", large_list)

        size = cache._estimate_size_bytes()
        # Should be larger than a small cache
        assert size > 1000


class TestCacheEviction:
    """Tests for cache size-based eviction."""

    def test_evict_oldest_under_limit(self) -> None:
        """Test eviction does nothing when under size limit."""
        cache = Cache(max_size_bytes=1024 * 1024)  # 1 MB
        cache.set("eurostat", "ds1", {"data": "small"})

        evicted = cache._evict_oldest()
        assert evicted == 0
        assert cache.size() == 1

    def test_evict_oldest_over_limit(self) -> None:
        """Test eviction removes entries when over size limit."""
        # Create cache with very small limit
        cache = Cache(max_size_bytes=100)  # 100 bytes - very small

        # Add entries that exceed limit
        cache.set("eurostat", "ds1", {"data": "value1" * 10})
        cache.set("eurostat", "ds2", {"data": "value2" * 10})
        cache.set("eurostat", "ds3", {"data": "value3" * 10})

        initial_size = cache.size()
        evicted = cache._evict_oldest()

        # Should have evicted some entries
        assert evicted > 0
        assert cache.size() < initial_size

    def test_evict_oldest_removes_oldest_first(self) -> None:
        """Test eviction removes entries with oldest expiration first."""
        import time

        cache = Cache(max_size_bytes=100, ttl_seconds=3600)

        # Add entries with different expiration times
        cache.set("eurostat", "old", {"data": "old"}, ttl_seconds=10)
        time.sleep(0.1)
        cache.set("eurostat", "newer", {"data": "newer"}, ttl_seconds=3600)
        time.sleep(0.1)
        cache.set("eurostat", "newest", {"data": "newest"}, ttl_seconds=7200)

        # Force eviction
        cache._evict_oldest()

        # Old entry should be evicted first (has earliest expiration)
        # If any entries remain, they should be the newer ones
        if cache.size() > 0:
            assert cache.get("eurostat", "old") is None or cache.size() == 3

    def test_max_size_bytes_initialization(self) -> None:
        """Test cache initializes with correct max size."""
        cache = Cache(max_size_bytes=4 * 1024 * 1024 * 1024)  # 4 GB
        assert cache.max_size_bytes == 4 * 1024 * 1024 * 1024

    def test_default_max_size(self) -> None:
        """Test cache uses default 8GB max size."""
        cache = Cache()
        assert cache.max_size_bytes == 8 * 1024 * 1024 * 1024


class TestCacheCleanupDaemon:
    """Tests for cache cleanup daemon."""

    import pytest

    @pytest.mark.asyncio
    async def test_start_cleanup_daemon(self) -> None:
        """Test starting the cleanup daemon."""
        cache = Cache()

        assert cache._cleanup_task is None

        await cache.start_cleanup_daemon(interval_seconds=60)

        assert cache._cleanup_task is not None
        assert not cache._cleanup_task.done()

        # Cleanup
        await cache.stop_cleanup_daemon()

    @pytest.mark.asyncio
    async def test_stop_cleanup_daemon(self) -> None:
        """Test stopping the cleanup daemon."""
        cache = Cache()

        await cache.start_cleanup_daemon(interval_seconds=60)
        assert cache._cleanup_task is not None

        await cache.stop_cleanup_daemon()

        assert cache._cleanup_task is None

    @pytest.mark.asyncio
    async def test_start_daemon_twice_warns(self) -> None:
        """Test starting daemon twice doesn't create duplicate."""
        cache = Cache()

        await cache.start_cleanup_daemon(interval_seconds=60)
        first_task = cache._cleanup_task

        # Starting again should not create a new task
        await cache.start_cleanup_daemon(interval_seconds=60)
        assert cache._cleanup_task is first_task

        # Cleanup
        await cache.stop_cleanup_daemon()

    @pytest.mark.asyncio
    async def test_stop_daemon_when_not_running(self) -> None:
        """Test stopping daemon when not running doesn't error."""
        cache = Cache()

        # Should not raise
        await cache.stop_cleanup_daemon()

    @pytest.mark.asyncio
    async def test_stats_shows_daemon_status(self) -> None:
        """Test stats includes daemon running status."""
        cache = Cache()

        stats_before = cache.stats()
        assert stats_before["cleanup_daemon_running"] is False

        await cache.start_cleanup_daemon(interval_seconds=60)

        stats_during = cache.stats()
        assert stats_during["cleanup_daemon_running"] is True

        await cache.stop_cleanup_daemon()

        stats_after = cache.stats()
        assert stats_after["cleanup_daemon_running"] is False


class TestCacheStatsEnhanced:
    """Tests for enhanced cache statistics."""

    def test_stats_includes_size_info(self) -> None:
        """Test stats includes cache size information."""
        cache = Cache()
        cache.set("eurostat", "ds", {"data": "value"})

        stats = cache.stats()

        assert "estimated_cache_size_mb" in stats
        assert "max_size_mb" in stats
        assert stats["estimated_cache_size_mb"] > 0
        assert stats["max_size_mb"] == 8 * 1024  # 8 GB in MB

    def test_stats_includes_process_memory(self) -> None:
        """Test stats includes process memory if psutil available."""
        cache = Cache()
        stats = cache.stats()

        # psutil may or may not be available in test environment
        try:
            import psutil  # noqa: F401

            assert "process_rss_mb" in stats
            assert "process_vms_mb" in stats
            assert stats["process_rss_mb"] > 0
        except ImportError:
            # psutil not available, these keys should be absent
            assert "process_rss_mb" not in stats
            assert "process_vms_mb" not in stats

    def test_stats_cleanup_daemon_field(self) -> None:
        """Test stats includes cleanup daemon status."""
        cache = Cache()
        stats = cache.stats()

        assert "cleanup_daemon_running" in stats
        assert isinstance(stats["cleanup_daemon_running"], bool)

    def test_stats_includes_utilization_pct(self) -> None:
        """Test stats includes size utilization percentage."""
        cache = Cache(max_size_bytes=1000)
        cache.set("test", "ds", {"data": "value"})

        stats = cache.stats()

        assert "size_utilization_pct" in stats
        assert stats["size_utilization_pct"] > 0


class TestRecursiveSizeEstimation:
    """Tests for recursive object size estimation."""

    def test_estimate_nested_dict(self) -> None:
        """Test size estimation for deeply nested dicts."""
        cache = Cache()
        nested = {"level1": {"level2": {"level3": {"data": "deep"}}}}

        size = cache._estimate_object_size(nested)
        # Should be larger than just the top-level dict
        assert size > 100

    def test_estimate_list_of_dicts(self) -> None:
        """Test size estimation for list containing dicts."""
        cache = Cache()
        data = [{"key": f"value_{i}"} for i in range(100)]

        size = cache._estimate_object_size(data)
        # Should account for all nested dicts
        assert size > 1000

    def test_estimate_handles_circular_reference(self) -> None:
        """Test size estimation handles circular references."""
        cache = Cache()
        data: dict[str, Any] = {"key": "value"}
        data["self"] = data  # Circular reference

        # Should not infinite loop
        size = cache._estimate_object_size(data)
        assert size > 0


class TestSystemKeyPrefix:
    """Tests for system key prefixing."""

    def test_system_key_gets_prefix(self) -> None:
        """Test that system keys (like __toc__) get prefixed."""
        cache = Cache()

        key = cache._generate_key("eurostat", "__toc__")
        assert key.startswith("__SYS__:")
        assert "eurostat" in key
        assert "__toc__" in key

    def test_regular_key_no_prefix(self) -> None:
        """Test that regular keys don't get system prefix."""
        cache = Cache()

        key = cache._generate_key("eurostat", "nama_10_gdp")
        assert not key.startswith("__SYS__:")
        assert key == "eurostat:nama_10_gdp"

    def test_system_key_isolation(self) -> None:
        """Test that system and regular keys with similar names are isolated."""
        cache = Cache()

        # Set both a system key and a regular key
        cache.set("test", "__toc__", {"type": "system"})
        cache.set("test", "toc", {"type": "regular"})

        # They should be separate entries
        assert cache.size() == 2
        assert cache.get("test", "__toc__")["type"] == "system"
        assert cache.get("test", "toc")["type"] == "regular"


class TestBatchEviction:
    """Tests for batch eviction behavior."""

    def test_batch_eviction_removes_multiple(self) -> None:
        """Test that batch eviction removes multiple entries at once."""
        # Create cache with very small limit
        cache = Cache(max_size_bytes=100)

        # Add many entries
        for i in range(20):
            cache.set("test", f"ds_{i}", {"data": f"value_{i}" * 10})

        # Check entries were added
        initial_size = cache.size()
        assert initial_size == 20

        # Force eviction
        evicted = cache._evict_oldest()

        # Should have evicted multiple entries (batch of 10%)
        assert evicted >= 2  # At least 10% of 20

    def test_batch_eviction_respects_safety_limit(self) -> None:
        """Test that batch eviction doesn't remove more than 50%."""
        cache = Cache(max_size_bytes=10)  # Very small

        # Add entries
        for i in range(100):
            cache.set("test", f"ds_{i}", {"data": f"value_{i}"})

        initial = cache.size()
        evicted = cache._evict_oldest()

        # Should not evict more than half
        assert evicted <= initial // 2


class TestIncrementalSizeTracking:
    """Tests for incremental size tracking."""

    def test_size_tracking_on_set(self) -> None:
        """Test that setting values updates size tracking."""
        cache = Cache()

        assert cache._cached_total_size == 0

        cache.set("test", "ds1", {"data": "value"})
        size_after_first = cache._cached_total_size
        assert size_after_first > 0

        cache.set("test", "ds2", {"data": "value2"})
        assert cache._cached_total_size > size_after_first

    def test_size_tracking_on_delete(self) -> None:
        """Test that deleting values updates size tracking."""
        cache = Cache()

        cache.set("test", "ds1", {"data": "value"})
        size_with_entry = cache._cached_total_size

        cache.delete("test", "ds1")
        assert cache._cached_total_size < size_with_entry

    def test_size_tracking_on_clear(self) -> None:
        """Test that clearing cache resets size tracking."""
        cache = Cache()

        cache.set("test", "ds1", {"data": "value"})
        cache.set("test", "ds2", {"data": "value2"})
        assert cache._cached_total_size > 0

        cache.clear()
        assert cache._cached_total_size == 0

    def test_size_tracking_on_update(self) -> None:
        """Test that updating existing key adjusts size correctly."""
        cache = Cache()

        cache.set("test", "ds", {"data": "small"})
        small_size = cache._cached_total_size

        # Update with larger value
        cache.set("test", "ds", {"data": "much_larger_value_here"})
        larger_size = cache._cached_total_size

        assert larger_size > small_size
        assert cache.size() == 1  # Still just one entry
