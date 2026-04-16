from 1ai_social.rate_limiter import RateLimiter, RateLimitExceeded, RATE_LIMITS

print("✓ Rate limiter module imports successfully")
print(f"✓ Rate limit configs: {list(RATE_LIMITS.keys())}")
for name, config in RATE_LIMITS.items():
    print(f"  - {name}: {config['capacity']} req/{config['window']}s")
