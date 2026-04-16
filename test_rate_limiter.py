#!/usr/bin/env python3
"""Test script for rate limiter functionality."""

import time
import sys
from 1ai_social.rate_limiter import RateLimiter, RateLimitExceeded

def test_rate_limiter():
    """Test basic rate limiting functionality."""
    print("Testing Redis-backed rate limiter...")
    
    limiter = RateLimiter("redis://localhost:6379/0")
    
    print("\n1. Testing token bucket algorithm (10 requests, 1 per second)...")
    capacity = 10
    refill_rate = 1.0
    
    success_count = 0
    for i in range(15):
        allowed, remaining, reset_time = limiter.check_rate_limit(
            f"test:user1:endpoint",
            capacity,
            refill_rate,
            requested=1
        )
        
        if allowed:
            success_count += 1
            print(f"  Request {i+1}: ALLOWED (remaining: {remaining})")
        else:
            print(f"  Request {i+1}: BLOCKED (remaining: {remaining}, reset: {reset_time})")
        
        time.sleep(0.1)
    
    print(f"\n  Result: {success_count}/15 requests allowed")
    
    print("\n2. Testing rate limit headers...")
    headers = limiter.get_rate_limit_headers(100, 95, int(time.time()) + 900)
    print(f"  X-RateLimit-Limit: {headers['X-RateLimit-Limit']}")
    print(f"  X-RateLimit-Remaining: {headers['X-RateLimit-Remaining']}")
    print(f"  X-RateLimit-Reset: {headers['X-RateLimit-Reset']}")
    
    print("\n3. Testing different rate limit configurations...")
    configs = [
        ("global", 100, 900),
        ("auth", 10, 600),
        ("api", 1000, 3600),
    ]
    
    for name, capacity, window in configs:
        refill_rate = capacity / window
        allowed, remaining, reset_time = limiter.check_rate_limit(
            f"test:user2:{name}",
            capacity,
            refill_rate,
            requested=1
        )
        print(f"  {name}: {capacity} req/{window}s - allowed={allowed}, remaining={remaining}")
    
    print("\n✓ Rate limiter tests completed successfully!")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(test_rate_limiter())
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
