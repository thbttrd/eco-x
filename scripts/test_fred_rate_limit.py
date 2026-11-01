#!/usr/bin/env python3
"""Test FRED rate limit is correctly configured."""

import sys

sys.path.insert(0, "ecox-data-platform/src")

from ecox_platform.config import settings


def main() -> bool:
    print(f"FRED rate limit: {settings.fred_rate_limit} req/sec")
    if settings.fred_rate_limit <= 2.0:
        print("PASS: Rate limit correctly set to <= 2.0 (FRED API allows ~120/min)")
        return True
    print("FAIL: Rate limit too high (FRED API allows ~2 req/sec)")
    return False


if __name__ == "__main__":
    exit(0 if main() else 1)
