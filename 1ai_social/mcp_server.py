"""MCP Server for 1ai-social - Social media automation platform."""

import importlib
import logging
import sys
import time
from typing import Any, Optional

from fastmcp import FastMCP
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from . import security_headers
from .cache import Cache
from .rate_limiter import rate_limit, RateLimitExceeded, get_user_id_from_kwargs
from .tenant_context import get_tenant_middleware, require_tenant_context
from .webhooks import WebhookVerificationError, create_verifier
from .billing.lemonsqueezy import (
    LemonSqueezyWebhookVerifier,
    LemonSqueezyWebhookHandler,
    get_webhook_secret as get_lemonsqueezy_secret,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

mcp = FastMCP("1ai-social")
security_middleware = security_headers.get_security_middleware()

_db_engine = None
_db_session_factory = None
_tenant_middleware = None
_redis_client = None
_cache = None


def _get_db_engine():
    """Get or create database engine with connection pooling."""
    global _db_engine
    if _db_engine is None:
        import os

        db_url = os.getenv("DATABASE_URL", "postgresql://localhost/1ai_social")
        _db_engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=10,
            pool_recycle=3600,
            pool_timeout=30,
            echo=False,
        )
    return _db_engine


def _get_db_session_factory():
    """Get or create database session factory."""
    global _db_session_factory
    if _db_session_factory is None:
        engine = _get_db_engine()
        _db_session_factory = sessionmaker(bind=engine)
    return _db_session_factory


def get_db_session() -> Session:
    """Create a new database session."""
    factory = _get_db_session_factory()
    return factory()


def _get_tenant_middleware():
    """Get or create tenant middleware instance."""
    global _tenant_middleware
    if _tenant_middleware is None:
        _tenant_middleware = get_tenant_middleware(get_db_session)
    return _tenant_middleware


def _get_redis_client():
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        import os
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(redis_url, decode_responses=False)
    return _redis_client


def get_cache() -> Cache:
    """Get or create cache instance."""
    global _cache
    if _cache is None:
        redis_client = _get_redis_client()
        _cache = Cache(redis_client)
    return _cache


def _get_orchestrator():
    mod = importlib.import_module("1ai_social.orchestrators.orchestrator")
    return mod.Orchestrator()


def _get_remotion_client():
    mod = importlib.import_module("1ai_social.clients.remotion")
    return mod.RemotionClient()


def _get_analytics_tracker():
    mod = importlib.import_module("1ai_social.analytics.tracker")
    return mod.AnalyticsTracker()


def _get_performance_reporter():
    mod = importlib.import_module("1ai_social.analytics.reporter")
    return mod.PerformanceReporter()


def _get_queue_manager():
    mod = importlib.import_module("1ai_social.schedulers.queue_manager")
    return mod.QueueManager()


def _get_metrics():
    mod = importlib.import_module("1ai_social.metrics")
    return mod.metrics


def track_metrics(endpoint: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            metrics = _get_metrics()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                status = (
                    result.get("status", "unknown")
                    if isinstance(result, dict)
                    else "success"
                )
                metrics.record_http_request(
                    "POST", endpoint, 200 if status == "success" else 500, duration
                )

                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.record_http_request("POST", endpoint, 500, duration)
                metrics.record_http_error("POST", endpoint, type(e).__name__)
                raise

        return wrapper

    return decorator


@mcp.tool()
def health_check() -> dict[str, str]:
    """Health check endpoint to verify server is running."""
    logger.info("Health check called")
    result = {"status": "ok"}
    return security_middleware.apply_to_response(result)


@mcp.tool()
@rate_limit(limit_type="api", get_user_id=get_user_id_from_kwargs)
@track_metrics("/generate_content")
def generate_content(niche: str, count: int = 5) -> dict[str, Any]:
    """Generate viral hooks and content preview for a niche without posting.

    Args:
        niche: Target niche/topic (e.g. 'AI', 'tech', 'cooking', 'fitness').
        count: Number of hooks to generate (default 5).
    """
    try:
        schema = PostCreateSchema(
            niche=niche, count=count, platforms=["tiktok"], content_type="video"
        )

        orch = _get_orchestrator()
        result = orch.generate_content_only(
            {
                "niche": schema.niche,
                "count": schema.count,
            }
        )
        metrics = _get_metrics()
        metrics.record_content_generated(schema.niche, "hook")
        return {"status": "success", "data": result}
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        return {"status": "error", "message": f"Validation error: {e.errors()}"}
    except Exception as e:
        logger.error(f"generate_content failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
@rate_limit(limit_type="api", get_user_id=get_user_id_from_kwargs)
@track_metrics("/generate_and_post")
def generate_and_post(
    niche: str,
    platforms: list[str] | None = None,
    content_type: str = "video",
    count: int = 1,
) -> dict[str, Any]:
    """Full pipeline: generate hooks, create video, polish caption, distribute.

    Args:
        niche: Target niche/topic (e.g. 'AI', 'tech', 'cooking').
        platforms: List of platforms to post to (default: ['tiktok']).
        content_type: Type of content to generate (default 'video').
        count: Number of posts to generate (default 1).
    """
    try:
        orch = _get_orchestrator()
        result = orch.generate_and_post(
            {
                "niche": niche,
                "platforms": platforms or ["tiktok"],
                "content_type": content_type,
                "count": count,
            }
        )
        metrics = _get_metrics()
        for platform in platforms or ["tiktok"]:
            metrics.record_post_published(platform, "success")
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"generate_and_post failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
@rate_limit(limit_type="api", get_user_id=get_user_id_from_kwargs)
@track_metrics("/schedule_campaign")
def schedule_campaign(
    niche: str,
    platforms: list[str] | None = None,
    days: int = 7,
) -> dict[str, Any]:
    """Schedule a multi-day content campaign with daily posts.

    Args:
        niche: Target niche/topic.
        platforms: List of platforms (default: ['tiktok']).
        days: Number of days for the campaign (default 7).
    """
    try:
        orch = _get_orchestrator()
        result = orch.schedule_campaign(
            {
                "niche": niche,
                "platforms": platforms or ["tiktok"],
            },
            days=days,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"schedule_campaign failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def list_templates() -> dict[str, Any]:
    """List all available Remotion video templates."""
    try:
        client = _get_remotion_client()
        templates = client.list_templates()
        return {
            "status": "success",
            "count": len(templates),
            "templates": templates,
        }
    except Exception as e:
        logger.error(f"list_templates failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def track_analytics(post_id: str) -> dict[str, Any]:
    """Get analytics metrics for a specific post.

    Args:
        post_id: The post identifier to look up.
    """
    try:
        schema = AnalyticsQuerySchema(post_id=post_id)

        tracker = _get_analytics_tracker()
        stats = tracker.get_stats(schema.post_id)
        if stats:
            return {"status": "success", "post_id": schema.post_id, "metrics": stats}
        return {
            "status": "not_found",
            "post_id": schema.post_id,
            "message": "No data found",
        }
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        return {"status": "error", "message": f"Validation error: {e.errors()}"}
    except Exception as e:
        logger.error(f"track_analytics failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_performance_report(report_type: str = "daily") -> dict[str, Any]:
    """Generate a performance report (daily or weekly).

    Args:
        report_type: Type of report - 'daily' or 'weekly' (default 'daily').
    """
    try:
        reporter = _get_performance_reporter()
        if report_type == "weekly":
            report = reporter.generate_weekly_report()
        else:
            report = reporter.generate_daily_report()
        return {"status": "success", "report_type": report_type, "report": report}
    except Exception as e:
        logger.error(f"get_performance_report failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/get_queue_status")
def get_queue_status() -> dict[str, Any]:
    """Get the current post queue status."""
    try:
        qm = _get_queue_manager()
        queue_size = qm.size()
        failed_count = len(qm.get_failed())

        metrics = _get_metrics()
        metrics.set_queue_size(queue_size)
        metrics.set_queue_failed(failed_count)

        return {
            "status": "success",
            "queue_size": queue_size,
            "failed_count": failed_count,
        }
    except Exception as e:
        logger.error(f"get_queue_status failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_aggregate_stats(
    platform: str | None = None,
    days: int = 30,
) -> dict[str, Any]:
    """Get aggregated analytics across all posts.

    Args:
        platform: Filter by platform name (e.g. 'tiktok') or None for all.
        days: Number of days to look back (default 30).
    """
    try:
        schema = AnalyticsQuerySchema(platform=platform, days=days)

        tracker = _get_analytics_tracker()
        plat = None
        if schema.platform:
            models = importlib.import_module("1ai_social.models")
            plat = models.Platform(schema.platform)
        stats = tracker.aggregate_stats(platform=plat, days=schema.days)
        return {"status": "success", "data": stats}
    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        return {"status": "error", "message": f"Validation error: {e.errors()}"}
    except Exception as e:
        logger.error(f"get_aggregate_stats failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_metrics() -> dict[str, Any]:
    """Get Prometheus metrics in text format."""
    try:
        metrics = _get_metrics()
        metrics_output, content_type = metrics.get_metrics()
        return {
            "status": "success",
            "metrics": metrics_output.decode("utf-8"),
            "content_type": content_type,
        }
    except Exception as e:
        logger.error(f"get_metrics failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(request):
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok", "service": "1ai-social"})


def main() -> None:
    """Start the MCP server."""
    import os

    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    logger.info(f"Starting 1ai-social MCP server with transport: {transport}")

    if transport in ("http", "sse", "streamable-http"):
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8200"))
        logger.info(f"HTTP mode: listening on {host}:{port}")
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        logger.info("STDIO mode: using standard input/output")
        mcp.run()


if __name__ == "__main__":
    main()


@mcp.tool()
@track_metrics("/webhook")
def process_webhook(
    provider: str,
    signature: str,
    timestamp: str,
    webhook_id: str,
    body: str,
) -> dict[str, Any]:
    """Process incoming webhook with signature verification.

    Args:
        provider: Provider name (e.g., 'stripe', 'github', 'twitter')
        signature: Signature from X-Webhook-Signature header
        timestamp: Timestamp from X-Webhook-Timestamp header
        webhook_id: Webhook ID from X-Webhook-ID header
        body: Raw request body as string
    """
    try:
        redis_client = _get_redis_client()
        verifier = create_verifier(provider, redis_client=redis_client)

        body_bytes = body.encode("utf-8")
        verifier.verify_webhook(signature, timestamp, webhook_id, body_bytes)

        logger.info(f"Webhook verified: provider={provider}, id={webhook_id}")

        return {
            "status": "success",
            "message": "Webhook verified and processed",
            "webhook_id": webhook_id,
        }
    except WebhookVerificationError as e:
        logger.warning(f"Webhook verification failed: {e}")
        return {
            "status": "unauthorized",
            "message": str(e),
        }
    except ValueError as e:
        logger.error(f"Webhook configuration error: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
    except Exception as e:
        logger.error(f"process_webhook failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/webhooks/lemonsqueezy")
def lemonsqueezy_webhook(signature: str, body: str) -> dict[str, Any]:
    """Process LemonSqueezy webhook events.

    Args:
        signature: Signature from X-Signature header
        body: Raw request body as JSON string
    """
    try:
        import json

        secret = get_lemonsqueezy_secret()
        verifier = LemonSqueezyWebhookVerifier(secret)

        body_bytes = body.encode("utf-8")
        if not verifier.verify_signature(signature, body_bytes):
            logger.warning("LemonSqueezy webhook signature verification failed")
            return {
                "status": "unauthorized",
                "message": "Invalid signature",
            }

        payload = json.loads(body)

        db_session = get_db_session()
        redis_client = _get_redis_client()
        handler = LemonSqueezyWebhookHandler(db_session, redis_client)

        result = handler.handle_webhook(payload)

        db_session.close()

        logger.info(f"LemonSqueezy webhook processed: {result}")
        return result

    except ValueError as e:
        logger.error(f"LemonSqueezy webhook configuration error: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        return {
            "status": "error",
            "message": "Invalid JSON payload",
        }
    except Exception as e:
        logger.error(f"lemonsqueezy_webhook failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/usage/record")
@require_tenant_context(get_db_session)
def record_usage_event(
    event_type: str,
    quantity: int = 1,
    metadata: Optional[dict] = None,
    _tenant_id: str = None,
    _db_session: Session = None,
) -> dict[str, Any]:
    """Record a usage event for billing metering.

    Args:
        event_type: Type of event (posts_published, api_calls, connected_accounts)
        quantity: Number of units consumed (default: 1)
        metadata: Optional metadata (must not contain PII)
    """
    try:
        from .billing.usage import record_usage

        event = record_usage(
            _db_session,
            _tenant_id,
            event_type,
            quantity,
            metadata,
        )

        return {
            "status": "success",
            "event_id": event.id,
            "tenant_id": event.tenant_id,
            "event_type": event.event_type,
            "quantity": event.quantity,
            "created_at": event.created_at.isoformat(),
        }

    except ValueError as e:
        logger.error(f"Invalid usage event: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"record_usage_event failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/usage/current")
@require_tenant_context(get_db_session)
def get_current_usage(
    _tenant_id: str = None,
    _db_session: Session = None,
) -> dict[str, Any]:
    """Get current month usage for the tenant.

    Returns:
        Usage counts by event type for the current billing month
    """
    try:
        from .billing.usage import get_current_month_usage

        usage = get_current_month_usage(_db_session, _tenant_id)

        return {
            "status": "success",
            "tenant_id": _tenant_id,
            "period": "current_month",
            "usage": usage,
        }

    except Exception as e:
        logger.error(f"get_current_usage failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/usage/overage")
@require_tenant_context(get_db_session)
def check_usage_overage(
    plan_name: str,
    _tenant_id: str = None,
    _db_session: Session = None,
) -> dict[str, Any]:
    """Check if tenant has exceeded plan limits.

    Args:
        plan_name: Subscription plan name (starter, pro, enterprise)

    Returns:
        Overage information with usage, limits, and overage amounts
    """
    try:
        from .billing.usage import check_overage

        result = check_overage(_db_session, _tenant_id, plan_name)

        return {
            "status": "success",
            "tenant_id": _tenant_id,
            "plan": plan_name,
            **result,
        }

    except Exception as e:
        logger.error(f"check_usage_overage failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/usage/summary")
@require_tenant_context(get_db_session)
def get_usage_summary(
    plan_name: str,
    _tenant_id: str = None,
    _db_session: Session = None,
) -> dict[str, Any]:
    """Get comprehensive usage summary with limits and percentages.

    Args:
        plan_name: Subscription plan name (starter, pro, enterprise)

    Returns:
        Complete usage summary including percentages and warnings
    """
    try:
        from .billing.usage import get_usage_summary as get_summary

        summary = get_summary(_db_session, _tenant_id, plan_name)

        return {
            "status": "success",
            **summary,
        }

    except Exception as e:
        logger.error(f"get_usage_summary failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/gdpr/consent")
@require_tenant_context(get_db_session)
def record_consent(
    user_id: str,
    consent_type: str,
    consented: bool,
    ip_address: str = None,
    user_agent: str = None,
    metadata: dict = None,
    _tenant_id: str = None,
    _db_session: Session = None,
) -> dict[str, Any]:
    """Record user consent for GDPR compliance."""
    try:
        from .gdpr import GDPRManager

        manager = GDPRManager(_db_session)
        consent_id = manager.record_consent(
            user_id=user_id,
            tenant_id=_tenant_id,
            consent_type=consent_type,
            consented=consented,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )

        return {
            "status": "success",
            "consent_id": consent_id,
            "user_id": user_id,
            "consent_type": consent_type,
            "consented": consented,
        }

    except Exception as e:
        logger.error(f"record_consent failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/gdpr/data-export")
@require_tenant_context(get_db_session)
def export_user_data(
    user_id: str,
    _tenant_id: str = None,
    _db_session: Session = None,
) -> dict[str, Any]:
    """Export all user data for DSAR (Data Subject Access Request)."""
    try:
        from .gdpr import GDPRManager

        manager = GDPRManager(_db_session)
        export_data = manager.export_user_data(user_id=user_id, tenant_id=_tenant_id)

        return {"status": "success", **export_data}

    except Exception as e:
        logger.error(f"export_user_data failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/gdpr/delete-account")
@require_tenant_context(get_db_session)
def delete_user_data(
    user_id: str,
    reason: str = None,
    _tenant_id: str = None,
    _db_session: Session = None,
) -> dict[str, Any]:
    """Delete user data (anonymize PII) for GDPR right to be forgotten."""
    try:
        from .gdpr import GDPRManager

        manager = GDPRManager(_db_session)
        deletion_summary = manager.delete_user_data(
            user_id=user_id, tenant_id=_tenant_id, reason=reason
        )

        return {"status": "success", **deletion_summary}

    except Exception as e:
        logger.error(f"delete_user_data failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@mcp.tool()
@track_metrics("/gdpr/consent-history")
@require_tenant_context(get_db_session)
def get_consent_history(
    user_id: str,
    consent_type: str = None,
    _tenant_id: str = None,
    _db_session: Session = None,
) -> dict[str, Any]:
    """Get consent history for a user."""
    try:
        from .gdpr import GDPRManager

        manager = GDPRManager(_db_session)
        history = manager.get_consent_history(
            user_id=user_id, tenant_id=_tenant_id, consent_type=consent_type
        )

        return {"status": "success", "user_id": user_id, "consent_history": history}

    except Exception as e:
        logger.error(f"get_consent_history failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
