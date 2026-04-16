#!/usr/bin/env python3
"""Test script for health check endpoints."""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "1ai_social"))

from health import HealthChecker


async def test_health_live():
    """Test liveness probe."""
    checker = HealthChecker("postgresql://localhost/test", None, None)
    result = checker.check_live()
    assert result["status"] == "healthy", f"Expected healthy, got {result}"
    print("✓ Liveness probe test passed")
    return result


async def test_health_ready_healthy():
    """Test readiness probe with all dependencies healthy."""
    checker = HealthChecker("postgresql://localhost/test", None, None)

    with patch.object(checker, "check_database", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = {"status": "healthy", "latency_ms": 10}

        result = await checker.check_ready()
        assert result["status"] == "healthy", (
            f"Expected healthy, got {result['status']}"
        )
        assert "checks" in result
        assert "database" in result["checks"]
        print("✓ Readiness probe (healthy) test passed")
        return result


async def test_health_ready_db_down():
    """Test readiness probe with database down."""
    checker = HealthChecker("postgresql://localhost/test", None, None)

    with patch.object(checker, "check_database", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = {
            "status": "unhealthy",
            "latency_ms": 5000,
            "error": "Connection refused",
        }

        result = await checker.check_ready()
        assert result["status"] == "unhealthy", (
            f"Expected unhealthy, got {result['status']}"
        )
        assert result["checks"]["database"]["status"] == "unhealthy"
        print("✓ Readiness probe (database down) test passed")
        return result


async def test_health_ready_redis_down():
    """Test readiness probe with Redis down (should still be healthy if DB is up)."""
    checker = HealthChecker("postgresql://localhost/test", "redis://localhost", None)

    with (
        patch.object(checker, "check_database", new_callable=AsyncMock) as mock_db,
        patch.object(checker, "check_redis", new_callable=AsyncMock) as mock_redis,
    ):
        mock_db.return_value = {"status": "healthy", "latency_ms": 10}
        mock_redis.return_value = {
            "status": "unhealthy",
            "latency_ms": 5000,
            "error": "Connection refused",
        }

        result = await checker.check_ready()
        # Should still be healthy because Redis is optional
        assert result["status"] == "healthy", (
            f"Expected healthy (Redis optional), got {result['status']}"
        )
        assert result["checks"]["redis"]["status"] == "unhealthy"
        print("✓ Readiness probe (Redis down, DB up) test passed")
        return result


async def main():
    """Run all tests."""
    print("Testing health check endpoints...\n")

    results = {
        "liveness": await test_health_live(),
        "readiness_healthy": await test_health_ready_healthy(),
        "readiness_db_down": await test_health_ready_db_down(),
        "readiness_redis_down": await test_health_ready_redis_down(),
    }

    # Save healthy scenario
    with open(
        "/home/openclaw/projects/1ai-social/.sisyphus/evidence/task-8-health-pass.json",
        "w",
    ) as f:
        json.dump(results["readiness_healthy"], f, indent=2)

    # Save failure scenario
    with open(
        "/home/openclaw/projects/1ai-social/.sisyphus/evidence/task-8-health-fail.json",
        "w",
    ) as f:
        json.dump(results["readiness_db_down"], f, indent=2)

    print("\n✓ All tests passed!")
    print(f"✓ Evidence saved to .sisyphus/evidence/")


if __name__ == "__main__":
    asyncio.run(main())
