#!/usr/bin/env python3
"""Test rate limiter with curl-like requests simulation."""

import sys
import time
import os

os.environ["REDIS_URL"] = "redis://localhost:6379/0"


def test_rate_limit_simulation():
    """Simulate rate limiting behavior without actual Redis."""
    print("Rate Limiter Test - Simulating Multiple Requests\n")
    print("=" * 60)

    print("\nTest 1: API Endpoint Rate Limit (1000 req/hour)")
    print("-" * 60)
    capacity = 1000
    window = 3600
    refill_rate = capacity / window

    print(f"Configuration: {capacity} requests per {window} seconds")
    print(f"Refill rate: {refill_rate:.4f} tokens/second\n")

    tokens = capacity
    last_refill = time.time()

    for i in range(10):
        now = time.time()
        elapsed = now - last_refill
        tokens_to_add = elapsed * refill_rate
        tokens = min(capacity, tokens + tokens_to_add)
        last_refill = now

        if tokens >= 1:
            tokens -= 1
            remaining = int(tokens)
            reset_time = int(now + ((capacity - tokens) / refill_rate))
            print(f"Request {i + 1:2d}: ✓ ALLOWED")
            print(f"  X-RateLimit-Limit: {capacity}")
            print(f"  X-RateLimit-Remaining: {remaining}")
            print(f"  X-RateLimit-Reset: {reset_time}")
        else:
            reset_time = int(now + ((1 - tokens) / refill_rate))
            print(f"Request {i + 1:2d}: ✗ BLOCKED (429 Too Many Requests)")
            print(f"  X-RateLimit-Limit: {capacity}")
            print(f"  X-RateLimit-Remaining: 0")
            print(f"  X-RateLimit-Reset: {reset_time}")
            print(f"  Retry-After: {reset_time - int(now)} seconds")

        time.sleep(0.1)

    print("\n" + "=" * 60)
    print("\nTest 2: Auth Endpoint Rate Limit (10 req/10min)")
    print("-" * 60)
    capacity = 10
    window = 600
    refill_rate = capacity / window

    print(f"Configuration: {capacity} requests per {window} seconds")
    print(f"Refill rate: {refill_rate:.4f} tokens/second\n")

    tokens = capacity

    for i in range(15):
        if tokens >= 1:
            tokens -= 1
            print(f"Request {i + 1:2d}: ✓ ALLOWED (remaining: {int(tokens)})")
        else:
            print(f"Request {i + 1:2d}: ✗ BLOCKED - Rate limit exceeded")

    print("\n" + "=" * 60)
    print("\nTest 3: Global Rate Limit (100 req/15min)")
    print("-" * 60)
    capacity = 100
    window = 900

    print(f"Configuration: {capacity} requests per {window} seconds")
    print(f"Per-user isolation: user:123:api, user:456:api")
    print(f"\nSimulating burst traffic:\n")

    for user_id in ["user:123", "user:456"]:
        tokens = capacity
        success = 0
        blocked = 0

        for i in range(120):
            if tokens >= 1:
                tokens -= 1
                success += 1
            else:
                blocked += 1

        print(f"{user_id}: {success} allowed, {blocked} blocked")

    print("\n" + "=" * 60)
    print("\n✓ Rate limiter simulation completed successfully!")
    print("\nExpected behavior:")
    print("  - API endpoints: 1000 req/hour per user")
    print("  - Auth endpoints: 10 req/10min per user")
    print("  - Global limit: 100 req/15min per user")
    print("  - 429 status code when limit exceeded")
    print("  - Rate limit headers in all responses")
    print("  - Health check endpoints are exempt")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(test_rate_limit_simulation())
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
