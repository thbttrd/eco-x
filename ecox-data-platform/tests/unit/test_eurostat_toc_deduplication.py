"""Unit tests for Eurostat TOC deduplication logic.

Tests that duplicate dataset entries in the Eurostat TOC are properly
deduplicated, keeping the entry with the most recent last_update.
"""

from typing import Any


def deduplicate_toc(datasets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Helper function that mimics the deduplication logic from repository.py."""
    seen_codes: dict[str, dict[str, Any]] = {}
    for ds in datasets:
        ds_code = str(ds["code"])
        if ds_code not in seen_codes:
            seen_codes[ds_code] = ds
        else:
            existing_update = str(seen_codes[ds_code].get("last_update") or "")
            new_update = str(ds.get("last_update") or "")
            if new_update > existing_update:
                seen_codes[ds_code] = ds
    return list(seen_codes.values())


class TestTocDeduplication:
    """Tests for TOC deduplication logic."""

    def test_deduplicate_removes_duplicates(
        self, sample_eurostat_toc_with_duplicates: list[dict]
    ) -> None:
        """Deduplication should remove duplicate dataset codes."""
        result = deduplicate_toc(sample_eurostat_toc_with_duplicates)

        # Should have 3 unique datasets (from 6 entries)
        assert len(result) == 3
        assert {d["code"] for d in result} == {"nama_10_gdp", "prc_hicp_midx", "une_rt_m"}

    def test_deduplicate_preserves_unique(self, sample_eurostat_toc_unique: list[dict]) -> None:
        """Deduplication should preserve all unique codes."""
        result = deduplicate_toc(sample_eurostat_toc_unique)

        assert len(result) == 3
        assert {d["code"] for d in result} == {"nama_10_gdp", "prc_hicp_midx", "une_rt_m"}

    def test_deduplicate_keeps_most_recent_last_update(
        self, sample_toc_different_last_updates: list[dict]
    ) -> None:
        """Deduplication should keep entry with most recent last_update."""
        result = deduplicate_toc(sample_toc_different_last_updates)

        assert len(result) == 1
        assert result[0]["name"] == "New version"
        assert result[0]["last_update"] == "15.12.2024"

    def test_deduplicate_handles_none_last_update(
        self, sample_toc_with_none_dates: list[dict]
    ) -> None:
        """Deduplication should handle None last_update gracefully."""
        result = deduplicate_toc(sample_toc_with_none_dates)

        assert len(result) == 1
        # Entry with actual date should win over None
        assert result[0]["last_update"] == "01.12.2024"

    def test_deduplicate_handles_empty_list(self) -> None:
        """Deduplication should handle empty dataset list."""
        result = deduplicate_toc([])
        assert len(result) == 0

    def test_deduplicate_calculates_correct_counts(
        self, sample_eurostat_toc_with_duplicates: list[dict]
    ) -> None:
        """Test that duplicate removal math is correct."""
        original_count = len(sample_eurostat_toc_with_duplicates)
        result = deduplicate_toc(sample_eurostat_toc_with_duplicates)
        duplicates_removed = original_count - len(result)

        assert original_count == 6
        assert len(result) == 3
        assert duplicates_removed == 3
