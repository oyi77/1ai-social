"""
Health check module for 1ai-social.

Provides liveness and readiness probes for Kubernetes and load balancers.
- /health/live: Liveness probe (always 200 unless app crashed)
- /health/ready: Readiness probe (checks all dependencies)
"""

import asyncio
import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class HealthChecker:
    """Manages health checks for application dependencies."""

    def __init__(
        self, db_url: str, redis_url: str = None, external_api_url: str = None
    ):
        """Initialize health checker with dependency URLs.

        Args:
            db_url: PostgreSQL database URL
            redis_url: Redis connection URL (optional)
            external_api_url: External API endpoint to check (optional)
        """
        self.db_url = db_url
        self.redis_url = redis_url
        self.external_api_url = external_api_url
        self.check_timeout = 5  # 5 second timeout per check

    async def check_database(self) -> Dict[str, Any]:
        """Check PostgreSQL database connectivity."""
        start = time.time()
        try:
            import psycopg2
            from psycopg2 import OperationalError

            # Parse connection string
            conn = psycopg2.connect(self.db_url, connect_timeout=self.check_timeout)
            conn.close()
            latency_ms = int((time.time() - start) * 1000)
            return {"status": "healthy", "latency_ms": latency_ms}
        except (OperationalError, Exception) as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.warning(f"Database check failed: {str(e)}")
            return {"status": "unhealthy", "latency_ms": latency_ms, "error": str(e)}

    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis cache connectivity."""
        if not self.redis_url:
            return {"status": "skipped", "reason": "Redis URL not configured"}

        start = time.time()
        try:
            import redis

            r = redis.from_url(
                self.redis_url, socket_connect_timeout=self.check_timeout
            )
            r.ping()
            r.close()
            latency_ms = int((time.time() - start) * 1000)
            return {"status": "healthy", "latency_ms": latency_ms}
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.warning(f"Redis check failed: {str(e)}")
            return {"status": "unhealthy", "latency_ms": latency_ms, "error": str(e)}

    async def check_external_api(self) -> Dict[str, Any]:
        """Check external API reachability."""
        if not self.external_api_url:
            return {"status": "skipped", "reason": "External API URL not configured"}

        start = time.time()
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.external_api_url,
                    timeout=aiohttp.ClientTimeout(total=self.check_timeout),
                ) as resp:
                    latency_ms = int((time.time() - start) * 1000)
                    if resp.status < 500:
                        return {
                            "status": "healthy",
                            "latency_ms": latency_ms,
                            "http_status": resp.status,
                        }
                    else:
                        return {
                            "status": "unhealthy",
                            "latency_ms": latency_ms,
                            "http_status": resp.status,
                        }
        except asyncio.TimeoutError:
            latency_ms = int((time.time() - start) * 1000)
            logger.warning(f"External API check timed out after {self.check_timeout}s")
            return {"status": "unhealthy", "latency_ms": latency_ms, "error": "timeout"}
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.warning(f"External API check failed: {str(e)}")
            return {"status": "unhealthy", "latency_ms": latency_ms, "error": str(e)}

    async def check_ready(self) -> Dict[str, Any]:
        """Check if application is ready to serve traffic.

        Returns:
            Dict with overall status and per-dependency checks.
            Status is 'healthy' only if all critical dependencies are healthy.
        """
        checks = {}

        # Run all checks concurrently with timeout
        try:
            db_check = await asyncio.wait_for(
                self.check_database(), timeout=self.check_timeout
            )
            checks["database"] = db_check
        except asyncio.TimeoutError:
            checks["database"] = {"status": "unhealthy", "error": "timeout"}

        try:
            redis_check = await asyncio.wait_for(
                self.check_redis(), timeout=self.check_timeout
            )
            checks["redis"] = redis_check
        except asyncio.TimeoutError:
            checks["redis"] = {"status": "unhealthy", "error": "timeout"}

        try:
            api_check = await asyncio.wait_for(
                self.check_external_api(), timeout=self.check_timeout
            )
            checks["external_api"] = api_check
        except asyncio.TimeoutError:
            checks["external_api"] = {"status": "unhealthy", "error": "timeout"}

        # Determine overall status: unhealthy if any critical check fails
        # Database is critical, Redis and external API are optional
        overall_status = "healthy"
        if checks["database"]["status"] == "unhealthy":
            overall_status = "unhealthy"

        return {"status": overall_status, "checks": checks}

    def check_live(self) -> Dict[str, str]:
        """Check if application is alive (liveness probe).

        Returns:
            Always returns healthy unless app crashed.
        """
        return {"status": "healthy"}
