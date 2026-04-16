"""Tests for cache module."""

import pytest
import time
import importlib
from unittest.mock import Mock, patch
from redis.exceptions import RedisError

cache_module = importlib.import_module("1ai_social.cache")
Cache = cache_module.Cache
cache_result = cache_module.cache_result
invalidate_cache = cache_module.invalidate_cache


@pytest.fixture
def mock_redis():
    return Mock()


@pytest.fixture
def cache(mock_redis):
    return Cache(mock_redis)


class TestCache:
    def test_get_hit(self, cache, mock_redis):
        import pickle

        mock_redis.get.return_value = pickle.dumps({"data": "value"})

        result = cache.get("test_key")

        assert result == {"data": "value"}
        mock_redis.get.assert_called_once_with("1ai_social:test_key")

    def test_get_miss(self, cache, mock_redis):
        mock_redis.get.return_value = None

        result = cache.get("test_key")

        assert result is None
        mock_redis.get.assert_called_once_with("1ai_social:test_key")

    def test_get_redis_error(self, cache, mock_redis):
        mock_redis.get.side_effect = RedisError("Connection failed")

        result = cache.get("test_key")

        assert result is None

    def test_set_success(self, cache, mock_redis):
        result = cache.set("test_key", {"data": "value"}, ttl=300)

        assert result is True
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "1ai_social:test_key"
        assert call_args[0][1] == 300

    def test_set_redis_error(self, cache, mock_redis):
        mock_redis.setex.side_effect = RedisError("Connection failed")

        result = cache.set("test_key", {"data": "value"})

        assert result is False

    def test_delete_success(self, cache, mock_redis):
        mock_redis.delete.return_value = 1

        result = cache.delete("test_key")

        assert result is True
        mock_redis.delete.assert_called_once_with("1ai_social:test_key")

    def test_delete_not_found(self, cache, mock_redis):
        mock_redis.delete.return_value = 0

        result = cache.delete("test_key")

        assert result is False

    def test_delete_pattern(self, cache, mock_redis):
        mock_redis.keys.return_value = [b"1ai_social:user:1", b"1ai_social:user:2"]
        mock_redis.delete.return_value = 2

        result = cache.delete_pattern("user:*")

        assert result == 2
        mock_redis.keys.assert_called_once_with("1ai_social:user:*")

    def test_flush(self, cache, mock_redis):
        mock_redis.keys.return_value = [b"1ai_social:key1", b"1ai_social:key2"]

        result = cache.flush()

        assert result is True
        mock_redis.delete.assert_called_once()

    def test_exists_true(self, cache, mock_redis):
        mock_redis.exists.return_value = 1

        result = cache.exists("test_key")

        assert result is True
        mock_redis.exists.assert_called_once_with("1ai_social:test_key")

    def test_exists_false(self, cache, mock_redis):
        mock_redis.exists.return_value = 0

        result = cache.exists("test_key")

        assert result is False

    def test_get_ttl_exists(self, cache, mock_redis):
        mock_redis.ttl.return_value = 300

        result = cache.get_ttl("test_key")

        assert result == 300

    def test_get_ttl_not_exists(self, cache, mock_redis):
        mock_redis.ttl.return_value = -2

        result = cache.get_ttl("test_key")

        assert result is None

    def test_increment(self, cache, mock_redis):
        mock_redis.incrby.return_value = 5

        result = cache.increment("counter", amount=5)

        assert result == 5
        mock_redis.incrby.assert_called_once_with("1ai_social:counter", 5)

    def test_increment_with_ttl(self, cache, mock_redis):
        mock_redis.incrby.return_value = 1

        result = cache.increment("counter", amount=1, ttl=300)

        assert result == 1
        mock_redis.expire.assert_called_once_with("1ai_social:counter", 300)


class TestCacheDecorator:
    def test_cache_result_hit(self, mock_redis):
        import pickle

        cache_instance = Cache(mock_redis)
        mock_redis.get.return_value = pickle.dumps("cached_result")

        class Service:
            def __init__(self):
                self.cache = cache_instance

            @cache_result(ttl=300)
            def get_data(self, key):
                return f"fresh_{key}"

        service = Service()
        result = service.get_data("test")

        assert result == "cached_result"

    def test_cache_result_miss(self, mock_redis):
        cache_instance = Cache(mock_redis)
        mock_redis.get.return_value = None

        class Service:
            def __init__(self):
                self.cache = cache_instance

            @cache_result(ttl=300)
            def get_data(self, key):
                return f"fresh_{key}"

        service = Service()
        result = service.get_data("test")

        assert result == "fresh_test"
        assert mock_redis.setex.called

    def test_cache_result_no_cache_instance(self):
        class Service:
            @cache_result(ttl=300)
            def get_data(self, key):
                return f"fresh_{key}"

        service = Service()
        result = service.get_data("test")

        assert result == "fresh_test"

    def test_invalidate_cache_decorator(self, mock_redis):
        cache_instance = Cache(mock_redis)
        mock_redis.keys.return_value = [b"1ai_social:plan:*"]

        class Service:
            def __init__(self):
                self.cache = cache_instance

            @invalidate_cache("plan:*")
            def update_plan(self, plan_id):
                return f"updated_{plan_id}"

        service = Service()
        result = service.update_plan("premium")

        assert result == "updated_premium"
        mock_redis.keys.assert_called_once_with("1ai_social:plan:*")


class TestCacheIntegration:
    @pytest.mark.integration
    def test_real_redis_operations(self):
        import redis
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url, decode_responses=False)
        cache = Cache(redis_client)

        test_key = "integration_test_key"
        test_value = {"test": "data", "number": 42}

        cache.delete(test_key)

        result = cache.get(test_key)
        assert result is None

        cache.set(test_key, test_value, ttl=10)

        result = cache.get(test_key)
        assert result == test_value

        assert cache.exists(test_key) is True

        ttl = cache.get_ttl(test_key)
        assert ttl > 0 and ttl <= 10

        cache.delete(test_key)
        assert cache.exists(test_key) is False

    @pytest.mark.integration
    def test_cache_hit_rate(self):
        import redis
        import os

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url, decode_responses=False)
        cache = Cache(redis_client)

        cache.flush()

        test_data = {f"key_{i}": f"value_{i}" for i in range(10)}

        for key, value in test_data.items():
            cache.set(key, value, ttl=60)

        hits = 0
        total = 100

        for _ in range(total):
            import random

            key = f"key_{random.randint(0, 9)}"
            result = cache.get(key)
            if result is not None:
                hits += 1

        hit_rate = (hits / total) * 100

        assert hit_rate >= 80, f"Cache hit rate {hit_rate}% is below 80%"

        cache.flush()
