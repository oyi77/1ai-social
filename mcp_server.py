"""
MCP Server for 1ai-social - Social media automation platform
"""

import logging
import os
import sys
from typing import Any

import sentry_sdk
from fastmcp import FastMCP

from .health import HealthChecker


def init_sentry():
    """Initialize Sentry error tracking with environment configuration."""
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        environment = os.getenv("ENVIRONMENT", "development")
        release = os.getenv("RELEASE", "unknown")

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            release=release,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            attach_stacktrace=True,
            include_local_variables=True,
        )
        logger_instance = logging.getLogger(__name__)
        logger_instance.info(f"Sentry initialized for environment: {environment}")
    else:
        logger_instance = logging.getLogger(__name__)
        logger_instance.warning("SENTRY_DSN not set - error tracking disabled")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

init_sentry()

# Initialize FastMCP server
mcp = FastMCP("1ai-social")

# Initialize health checker
_health_checker = None


def _get_health_checker() -> HealthChecker:
    """Get or create health checker instance."""
    global _health_checker
    if _health_checker is None:
        db_url = os.getenv("DATABASE_URL", "postgresql://localhost/1ai_social")
        redis_url = os.getenv("REDIS_URL")
        external_api_url = os.getenv("EXTERNAL_API_URL")
        _health_checker = HealthChecker(db_url, redis_url, external_api_url)
    return _health_checker


@mcp.tool()
def health_check() -> dict[str, str]:
    """Health check endpoint to verify server is running."""
    logger.info("Health check called")
    return {"status": "ok"}


@mcp.tool()
def health_live() -> dict[str, str]:
    """Liveness probe - returns 200 if app is running."""
    checker = _get_health_checker()
    result = checker.check_live()
    logger.info(f"Liveness check: {result['status']}")
    return result


@mcp.tool()
async def health_ready() -> dict[str, Any]:
    """Readiness probe - checks all dependencies."""
    checker = _get_health_checker()
    result = await checker.check_ready()
    logger.info(f"Readiness check: {result['status']}")
    return result


@mcp.tool()
def test_error() -> dict[str, str]:
    """Test error endpoint to verify Sentry error capture."""
    user_id = os.getenv("TEST_USER_ID", "test-user-123")
    tenant_id = os.getenv("TEST_TENANT_ID", "test-tenant-456")

    with sentry_sdk.push_scope() as scope:
        scope.set_user({"id": user_id, "tenant_id": tenant_id})
        scope.set_context(
            "test_context", {"endpoint": "test_error", "purpose": "sentry_verification"}
        )
        scope.add_breadcrumb(
            category="test",
            message="Test error endpoint called",
            level="info",
        )

        try:
            raise ValueError("This is a test error for Sentry verification")
        except ValueError as e:
            sentry_sdk.capture_exception(e)
            logger.error(f"Test error captured: {str(e)}")
            return {"status": "error_captured", "message": str(e)}


def set_user_context(user_id: str, tenant_id: str = None) -> None:
    """Attach user context to Sentry for all subsequent errors."""
    with sentry_sdk.push_scope() as scope:
        user_data = {"id": user_id}
        if tenant_id:
            user_data["tenant_id"] = tenant_id
        scope.set_user(user_data)


def add_breadcrumb(
    category: str, message: str, level: str = "info", data: dict = None
) -> None:
    """Add breadcrumb for debugging context."""
    sentry_sdk.add_breadcrumb(
        category=category,
        message=message,
        level=level,
        data=data or {},
    )


# Placeholder for tool definitions
# Tools will be implemented in subsequent tasks:
# - Social media posting tools
# - Content generation tools
# - Analytics tools
# - Engagement automation tools


def main() -> None:
    """Start the MCP server."""
    logger.info("Starting 1ai-social MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
