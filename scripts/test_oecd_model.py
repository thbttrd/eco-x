#!/usr/bin/env python3
"""Test OECD model handles both 'id' and 'value' fields."""

import sys

sys.path.insert(0, "ecox-data-platform/src")

from ecox_platform.sources.oecd.models import OecdDimensionValue


def main() -> bool:
    """Test OecdDimensionValue handles both formats."""
    test_cases = [
        # (input_dict, expected_id)
        ({"id": "FRA", "name": "France"}, "FRA"),
        ({"value": "FRA08001"}, "FRA08001"),  # Alternative format
        ({"id": "DEU", "value": "DEU00001", "name": "Germany"}, "DEU"),  # id takes precedence
        ({"value": "USA", "name": "United States"}, "USA"),
        ({"id": "GBR"}, "GBR"),  # Minimal valid input
    ]

    passed = 0
    for case, expected_id in test_cases:
        try:
            result = OecdDimensionValue(**case)
            if result.id == expected_id:
                print(f"PASS: {case} -> id={result.id}")
                passed += 1
            else:
                print(f"FAIL: {case} -> got id={result.id}, expected {expected_id}")
        except Exception as e:
            print(f"FAIL: {case} -> {e}")

    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


if __name__ == "__main__":
    exit(0 if main() else 1)
