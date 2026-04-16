"""Redis caching layer for performance optimization.

Provides caching for frequently accessed data with automatic invalidation.
"""

import json
import logging
import pickle
from functools import wraps
from typing import Any, Optional, Callable, Union
import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class Cache:
    """Redis-backed cache with TTL support and automatic serialization."""

    def __init__(self, redis_client: redis.Redis):
        """Initialize cache with Redis client.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self._prefix = "1ai_social:"

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key.

        Args:
            key: Cache key

        Returns:
            Prefixed key string
        """
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        try:
            prefixed_key = self._make_key(key)
            value = self.redis.get(prefixed_key)

            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None

            logger.debug(f"Cache hit: {key}")
            return pickle.loads(value)
        except RedisError as e:
            logger.error(f"Redis error on get({key}): {e}")
            return None
        except Exception as e:
            logger.error(f"Error deserializing cache value for {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (must be picklable)
            ttl: Time to live in seconds (default: 5 minutes)

        Returns:
            True if successful, False otherwise
        """
        try:
            prefixed_key = self._make_key(key)
            serialized = pickle.dumps(value)
            self.redis.setex(prefixed_key, ttl, serialized)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True
        except RedisError as e:
            logger.error(f"Redis error on set({key}): {e}")
            return False
        except Exception as e:
            logger.error(f"Error serializing value for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False otherwise
        """
        try:
            prefixed_key = self._make_key(key)
            result = self.redis.delete(prefixed_key)
            logger.debug(f"Cache delete: {key} (existed: {result > 0})")
            return result > 0
        except RedisError as e:
            logger.error(f"Redis error on delete({key}): {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            prefixed_pattern = self._make_key(pattern)
            keys = self.redis.keys(prefixed_pattern)

            if not keys:
                return 0

            count = self.redis.delete(*keys)
            logger.debug(f"Cache delete pattern: {pattern} ({count} keys)")
            return count
        except RedisError as e:
            logger.error(f"Redis error on delete_pattern({pattern}): {e}")
            return 0

    def flush(self) -> bool:
        """Flush all cache entries with prefix.

        Returns:
            True if successful, False otherwise
        """
        try:
            pattern = self._make_key("*")
            keys = self.redis.keys(pattern)

            if keys:
                self.redis.delete(*keys)
                logger.info(f"Cache flushed: {len(keys)} keys deleted")

            return True
        except RedisError as e:
            logger.error(f"Redis error on flush: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            prefixed_key = self._make_key(key)
            return self.redis.exists(prefixed_key) > 0
        except RedisError as e:
            logger.error(f"Redis error on exists({key}): {e}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiry, None if key doesn't exist
        """
        try:
            prefixed_key = self._make_key(key)
            ttl = self.redis.ttl(prefixed_key)

            if ttl == -2:  # Key doesn't exist
                return None

            return ttl
        except RedisError as e:
            logger.error(f"Redis error on get_ttl({key}): {e}")
            return None

    def increment(
        self, key: str, amount: int = 1, ttl: Optional[int] = None
    ) -> Optional[int]:
        """Increment counter in cache.

        Args:
            key: Cache key
            amount: Amount to increment by
            ttl: TTL for new keys (optional)

        Returns:
            New value after increment, or None on error
        """
        try:
            prefixed_key = self._make_key(key)
            new_value = self.redis.incrby(prefixed_key, amount)

            if ttl is not None and new_value == amount:
                # Key was just created, set TTL
                self.redis.expire(prefixed_key, ttl)

            return new_value
        except RedisError as e:
            logger.error(f"Redis error on increment({key}): {e}")
            return None


def cache_result(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
    key_func: Optional[Callable] = None,
):
    """Decorator to cache function results.

    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        key_prefix: Optional prefix for cache key
        key_func: Optional function to generate cache key from args/kwargs

    Example:
        @cache_result(ttl=3600, key_prefix="plan_limits")
        def get_plan_limits(plan_name: str):
            return fetch_from_db(plan_name)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache instance from first arg if it's a method
            cache_instance = None
            if args and hasattr(args[0], "__class__"):
                if hasattr(args[0], "cache"):
                    cache_instance = args[0].cache

            # If no cache available, execute function directly
            if cache_instance is None:
                logger.debug(
                    f"No cache instance available for {func.__name__}, executing directly"
                )
                return func(*args, **kwargs)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                prefix = key_prefix or func.__name__
                # Create key from function args (skip self/cls)
                func_args = args[1:] if args and hasattr(args[0], "__class__") else args
                args_str = "_".join(str(arg) for arg in func_args)
                kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                key_parts = [prefix, args_str, kwargs_str]
                cache_key = ":".join(filter(None, key_parts))

            # Try to get from cache
            cached_value = cache_instance.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


def invalidate_cache(pattern: str):
    """Decorator to invalidate cache after function execution.

    Args:
        pattern: Cache key pattern to invalidate

    Example:
        @invalidate_cache("plan_limits:*")
        def update_plan_limits(plan_name: str, limits: dict):
            save_to_db(plan_name, limits)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Get cache instance
            cache_instance = None
            if args and hasattr(args[0], "__class__"):
                if hasattr(args[0], "cache"):
                    cache_instance = args[0].cache

            if cache_instance:
                cache_instance.delete_pattern(pattern)
                logger.debug(f"Invalidated cache pattern: {pattern}")

            return result

        return wrapper

    return decorator
