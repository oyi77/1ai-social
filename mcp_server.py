"""
MCP Server for 1ai-social - Social media automation platform
"""

import logging
import os
import sys
from typing import Any

import sentry_sdk
from fastmcp import FastMCP
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .health import HealthChecker
from .billing.dashboard import (
    get_billing_overview,
    get_usage_details,
    get_invoices,
    get_payment_methods,
)
from .admin import (
    get_admin_metrics,
    get_admin_users,
    get_admin_subscriptions,
    get_admin_analytics,
    AdminAuthError,
)


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

# Database session factory
_session_factory = None


def _get_session_factory():
    """Get or create database session factory."""
    global _session_factory
    if _session_factory is None:
        db_url = os.getenv("DATABASE_URL", "postgresql://localhost/1ai_social")
        engine = create_engine(db_url)
        _session_factory = sessionmaker(bind=engine)
    return _session_factory


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


@mcp.tool()
def billing_overview(tenant_id: str, plan_name: str) -> dict[str, Any]:
    """Get current billing overview with plan, usage, and next billing date."""
    try:
        session_factory = _get_session_factory()
        session = session_factory()
        result = get_billing_overview(session, tenant_id, plan_name)
        session.close()
        logger.info(f"Billing overview retrieved for tenant: {tenant_id}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving billing overview: {str(e)}")
        sentry_sdk.capture_exception(e)
        return {"error": str(e), "tenant_id": tenant_id}


@mcp.tool()
def billing_usage_details(
    tenant_id: str,
    plan_name: str,
    period_start: str = None,
    period_end: str = None,
) -> dict[str, Any]:
    """Get detailed usage metrics with progress bars for a billing period."""
    try:
        from datetime import datetime

        session_factory = _get_session_factory()
        session = session_factory()

        start = datetime.fromisoformat(period_start) if period_start else None
        end = datetime.fromisoformat(period_end) if period_end else None

        result = get_usage_details(session, tenant_id, plan_name, start, end)
        session.close()
        logger.info(f"Usage details retrieved for tenant: {tenant_id}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving usage details: {str(e)}")
        sentry_sdk.capture_exception(e)
        return {"error": str(e), "tenant_id": tenant_id}


@mcp.tool()
def billing_invoices(tenant_id: str, limit: int = 12) -> dict[str, Any]:
    """Get list of past invoices for a tenant."""
    try:
        session_factory = _get_session_factory()
        session = session_factory()
        result = get_invoices(session, tenant_id, limit)
        session.close()
        logger.info(f"Invoices retrieved for tenant: {tenant_id}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving invoices: {str(e)}")
        sentry_sdk.capture_exception(e)
        return {"error": str(e), "tenant_id": tenant_id}


@mcp.tool()
def billing_payment_methods(tenant_id: str) -> dict[str, Any]:
    """Get payment methods on file for a tenant (no sensitive details exposed)."""
    try:
        session_factory = _get_session_factory()
        session = session_factory()
        result = get_payment_methods(session, tenant_id)
        session.close()
        logger.info(f"Payment methods retrieved for tenant: {tenant_id}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving payment methods: {str(e)}")
        sentry_sdk.capture_exception(e)
        return {"error": str(e), "tenant_id": tenant_id}


@mcp.tool()
def admin_metrics(user_role: str) -> dict[str, Any]:
    """Get admin dashboard metrics: MRR, active users, churn rate, new signups."""
    try:
        session_factory = _get_session_factory()
        session = session_factory()
        result = get_admin_metrics(session, user_role)
        session.close()
        logger.info("Admin metrics retrieved")
        return result
    except AdminAuthError as e:
        logger.warning(f"Admin auth failed: {str(e)}")
        return {"error": "unauthorized", "message": str(e)}
    except Exception as e:
        logger.error(f"Error retrieving admin metrics: {str(e)}")
        sentry_sdk.capture_exception(e)
        return {"error": str(e)}


@mcp.tool()
def admin_users(
    user_role: str, page: int = 1, per_page: int = 50, search: str = None
) -> dict[str, Any]:
    """Get paginated user list with search/filter capability."""
    try:
        session_factory = _get_session_factory()
        session = session_factory()
        result = get_admin_users(session, user_role, page, per_page, search)
        session.close()
        logger.info(f"Admin users retrieved: page={page}")
        return result
    except AdminAuthError as e:
        logger.warning(f"Admin auth failed: {str(e)}")
        return {"error": "unauthorized", "message": str(e)}
    except Exception as e:
        logger.error(f"Error retrieving admin users: {str(e)}")
        sentry_sdk.capture_exception(e)
        return {"error": str(e)}


@mcp.tool()
def admin_subscriptions(user_role: str, status: str = None) -> dict[str, Any]:
    """Get subscription management data with optional status filter."""
    try:
        session_factory = _get_session_factory()
        session = session_factory()
        result = get_admin_subscriptions(session, user_role, status)
        session.close()
        logger.info(f"Admin subscriptions retrieved: status={status}")
        return result
    except AdminAuthError as e:
        logger.warning(f"Admin auth failed: {str(e)}")
        return {"error": "unauthorized", "message": str(e)}
    except Exception as e:
        logger.error(f"Error retrieving admin subscriptions: {str(e)}")
        sentry_sdk.capture_exception(e)
        return {"error": str(e)}


@mcp.tool()
def admin_analytics(user_role: str, period: str = "30d") -> dict[str, Any]:
    """Get usage analytics for specified period (7d, 30d, 90d, 1y)."""
    try:
        session_factory = _get_session_factory()
        session = session_factory()
        result = get_admin_analytics(session, user_role, period)
        session.close()
        logger.info(f"Admin analytics retrieved: period={period}")
        return result
    except AdminAuthError as e:
        logger.warning(f"Admin auth failed: {str(e)}")
        return {"error": "unauthorized", "message": str(e)}
    except Exception as e:
        logger.error(f"Error retrieving admin analytics: {str(e)}")
        sentry_sdk.capture_exception(e)
        return {"error": str(e)}


def main() -> None:
    """Start the MCP server."""
    logger.info("Starting 1ai-social MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
