"""MCP Server for 1ai-social - Social media automation platform."""

import importlib
import logging
import sys
from typing import Any, Optional

from fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

mcp = FastMCP("1ai-social")


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


@mcp.tool()
def health_check() -> dict[str, str]:
    """Health check endpoint to verify server is running."""
    logger.info("Health check called")
    return {"status": "ok"}


@mcp.tool()
def generate_content(niche: str, count: int = 5) -> dict[str, Any]:
    """Generate viral hooks and content preview for a niche without posting.

    Args:
        niche: Target niche/topic (e.g. 'AI', 'tech', 'cooking', 'fitness').
        count: Number of hooks to generate (default 5).
    """
    try:
        orch = _get_orchestrator()
        result = orch.generate_content_only(
            {
                "niche": niche,
                "count": count,
            }
        )
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"generate_content failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
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
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"generate_and_post failed: {e}")
        return {"status": "error", "message": str(e)}


@mcp.tool()
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
        tracker = _get_analytics_tracker()
        stats = tracker.get_stats(post_id)
        if stats:
            return {"status": "success", "post_id": post_id, "metrics": stats}
        return {"status": "not_found", "post_id": post_id, "message": "No data found"}
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
def get_queue_status() -> dict[str, Any]:
    """Get the current post queue status."""
    try:
        qm = _get_queue_manager()
        return {
            "status": "success",
            "queue_size": qm.size(),
            "failed_count": len(qm.get_failed()),
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
        tracker = _get_analytics_tracker()
        plat = None
        if platform:
            models = importlib.import_module("1ai_social.models")
            plat = models.Platform(platform)
        stats = tracker.aggregate_stats(platform=plat, days=days)
        return {"status": "success", "data": stats}
    except Exception as e:
        logger.error(f"get_aggregate_stats failed: {e}")
        return {"status": "error", "message": str(e)}


def main() -> None:
    """Start the MCP server."""
    logger.info("Starting 1ai-social MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
