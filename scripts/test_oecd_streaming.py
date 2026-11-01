#!/usr/bin/env python3
"""Test OECD large response handling with streaming."""

import asyncio
import sys

sys.path.insert(0, "ecox-shared/src")
sys.path.insert(0, "ecox-data-platform/src")

from ecox_shared.utils import ResilientHttpClient


async def main() -> bool:
    """Test streaming method exists and works."""
    # Test 1: Verify method exists on the client
    print("Test 1: Verify get_large() method exists...")
    client = ResilientHttpClient(
        base_url="https://httpbin.org",
        rate_limit=2.0,
        timeout=30,
    )

    try:
        # Verify method exists
        if not hasattr(client, "get_large"):
            print("FAIL: get_large() method does not exist on ResilientHttpClient")
            return False
        print("  - Method exists on client")

        # Test with httpbin (reliable test endpoint)
        print("\nTest 2: Verify streaming works with httpbin...")
        data = await client.get_large("json")

        if "slideshow" in data:
            print("PASS: Streaming method works correctly")
            print("  - Response has 'slideshow' key")
            return True

        print("FAIL: Unexpected response structure")
        return False

    except Exception as e:
        print(f"FAIL: Error: {e}")
        return False

    finally:
        await client.close()


if __name__ == "__main__":
    exit(0 if asyncio.run(main()) else 1)
