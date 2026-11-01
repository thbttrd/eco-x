#!/usr/bin/env python3
"""Test ONS problematic dataset tracking."""

import sys

sys.path.insert(0, "ecox-data-platform/src")

from ecox_platform.sources.ons.repository import OnsRepository


def main() -> bool:
    """Test OnsRepository failure tracking logic."""
    # Create repository without starting HTTP client
    repo = OnsRepository.__new__(OnsRepository)
    repo._failure_counts = {}
    repo._problematic_datasets = set()
    repo._failure_threshold = 3

    print("Test 1: Dataset marked problematic after 3 failures...")
    for _ in range(3):
        repo.record_dataset_failure("problem-dataset")

    if repo.should_skip_dataset("problem-dataset"):
        print("  PASS: Dataset marked problematic after 3 failures")
    else:
        print("  FAIL: Dataset not marked problematic")
        return False

    print("\nTest 2: Normal datasets not skipped...")
    if not repo.should_skip_dataset("normal-dataset"):
        print("  PASS: Normal datasets not skipped")
    else:
        print("  FAIL: Normal datasets incorrectly skipped")
        return False

    print("\nTest 3: Success resets failure count...")
    repo._failure_counts["test-dataset"] = 2
    repo.record_dataset_success("test-dataset")
    if repo._failure_counts.get("test-dataset") is None:
        print("  PASS: Success resets failure count")
    else:
        print("  FAIL: Success didn't reset count")
        return False

    print("\nTest 4: Failure count increments correctly...")
    repo.record_dataset_failure("counting-test")
    repo.record_dataset_failure("counting-test")
    if repo._failure_counts.get("counting-test") == 2:
        print("  PASS: Failure count increments correctly")
    else:
        print(f"  FAIL: Expected 2, got {repo._failure_counts.get('counting-test')}")
        return False

    print("\nAll tests passed!")
    return True


if __name__ == "__main__":
    exit(0 if main() else 1)
