"""Redis-backed rate limiting middleware using token bucket algorithm."""

import logging
import time
from functools import wraps
from typing import Any, Callable, Optional

import redis

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, limit: int, reset_time: int):
        self.limit = limit
        self.reset_time = reset_time
        super().__init__(f"Rate limit of {limit} requests exceeded")


class RateLimiter:
    """Redis-backed rate limiter using token bucket algorithm with Lua scripts."""

    # Lua script for token bucket rate limiting (atomic operation)
    TOKEN_BUCKET_SCRIPT = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local refill_rate = tonumber(ARGV[2])
    local now = tonumber(ARGV[3])
    local requested = tonumber(ARGV[4])
    
    local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
    local tokens = tonumber(bucket[1])
    local last_refill = tonumber(bucket[2])
    
    if tokens == nil then
        tokens = capacity
        last_refill = now
    end
    
    -- Calculate tokens to add based on time elapsed
    local elapsed = now - last_refill
    local tokens_to_add = elapsed * refill_rate
    tokens = math.min(capacity, tokens + tokens_to_add)
    last_refill = now
    
    -- Check if we have enough tokens
    if tokens >= requested then
        tokens = tokens - requested
        redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
        redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) + 60)
        return {1, tokens, last_refill}
    else
        redis.call('HMSET', key, 'tokens', tokens, 'last_refill', last_refill)
        redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) + 60)
        return {0, tokens, last_refill}
    end
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize rate limiter with Redis connection.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.script = self.redis_client.register_script(self.TOKEN_BUCKET_SCRIPT)
        logger.info(f"RateLimiter initialized with Redis at {redis_url}")

    def check_rate_limit(
        self,
        key: str,
        capacity: int,
        refill_rate: float,
        requested: int = 1,
    ) -> tuple[bool, int, int]:
        """Check if request is within rate limit using token bucket algorithm.

        Args:
            key: Unique identifier for the rate limit bucket (e.g., "user:123:api")
            capacity: Maximum number of tokens (requests) in the bucket
            refill_rate: Tokens added per second
            requested: Number of tokens to consume (default 1)

        Returns:
            Tuple of (allowed, remaining_tokens, reset_time)
        """
        now = time.time()

        try:
            result = self.script(
                keys=[f"ratelimit:{key}"],
                args=[capacity, refill_rate, now, requested],
            )

            allowed = bool(result[0])
            remaining = int(result[1])
            last_refill = float(result[2])

            # Calculate reset time (when bucket will be full again)
            tokens_needed = capacity - remaining
            reset_time = int(last_refill + (tokens_needed / refill_rate))

            return allowed, remaining, reset_time

        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiting: {e}")
            # Fail open - allow request if Redis is down
            return True, capacity, int(now)

    def get_rate_limit_headers(
        self, limit: int, remaining: int, reset_time: int
    ) -> dict[str, str]:
        """Generate rate limit headers for HTTP response.

        Args:
            limit: Maximum requests allowed
            remaining: Remaining requests in current window
            reset_time: Unix timestamp when limit resets

        Returns:
            Dictionary of rate limit headers
        """
        return {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(reset_time),
        }


# Rate limit configurations
RATE_LIMITS = {
    "global": {"capacity": 100, "window": 900},  # 100 requests per 15 minutes
    "auth": {"capacity": 10, "window": 600},  # 10 requests per 10 minutes
    "api": {"capacity": 1000, "window": 3600},  # 1000 requests per hour
}

# Endpoints that should not be rate limited
EXEMPT_ENDPOINTS = ["/health/live", "/health/ready", "/health_check"]


def rate_limit(
    limit_type: str = "api",
    get_user_id: Optional[Callable[[Any], str]] = None,
):
    """Decorator to apply rate limiting to MCP tools.

    Args:
        limit_type: Type of rate limit to apply ('global', 'auth', 'api')
        get_user_id: Optional function to extract user ID from request context
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get rate limit configuration
            config = RATE_LIMITS.get(limit_type, RATE_LIMITS["api"])
            capacity = config["capacity"]
            window = config["window"]
            refill_rate = capacity / window

            # Determine rate limit key
            user_id = "anonymous"
            if get_user_id:
                try:
                    user_id = get_user_id(kwargs)
                except Exception as e:
                    logger.warning(f"Failed to extract user_id: {e}")

            # Create rate limit key
            endpoint = func.__name__
            rate_limit_key = f"{limit_type}:{user_id}:{endpoint}"

            # Initialize rate limiter
            import os

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            limiter = RateLimiter(redis_url)

            # Check rate limit
            allowed, remaining, reset_time = limiter.check_rate_limit(
                rate_limit_key, capacity, refill_rate
            )

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for {rate_limit_key}: {capacity} requests per {window}s"
                )
                raise RateLimitExceeded(capacity, reset_time)

            # Execute the function
            result = func(*args, **kwargs)

            # Add rate limit info to response if it's a dict
            if isinstance(result, dict):
                result["rate_limit"] = limiter.get_rate_limit_headers(
                    capacity, remaining, reset_time
                )

            return result

        return wrapper

    return decorator


def get_user_id_from_kwargs(kwargs: dict) -> str:
    """Extract user_id from function kwargs or use IP-based identifier.

    Args:
        kwargs: Function keyword arguments

    Returns:
        User identifier string
    """
    # Try to get user_id from kwargs
    if "user_id" in kwargs:
        return str(kwargs["user_id"])

    # Try to get from context (if available)
    if "context" in kwargs and hasattr(kwargs["context"], "user_id"):
        return str(kwargs["context"].user_id)

    # Fallback to IP-based identifier (would need request context)
    return "anonymous"
