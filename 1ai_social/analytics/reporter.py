"""Performance reporter for generating content analytics reports."""

from ..logging_config import get_logger

logger = get_logger(__name__)


class PerformanceReporter:
    """Generates performance reports from tracked analytics."""

    def __init__(self, tracker=None, confidence=None):
        self._tracker = tracker
        self._confidence = confidence

    def _get_tracker(self):
        if self._tracker is None:
            from .tracker import AnalyticsTracker

            self._tracker = AnalyticsTracker()
        return self._tracker

    def _get_confidence(self):
        if self._confidence is None:
            from .confidence import ConfidenceUpdater

            self._confidence = ConfidenceUpdater()
        return self._confidence

    def generate_daily_report(self) -> str:
        """Generate a daily performance summary.

        Returns:
            Markdown-formatted report string.
        """
        tracker = self._get_tracker()
        stats = tracker.aggregate_stats(days=1)

        lines = [
            "# Daily Report",
            "",
            f"- **Posts**: {stats['total_posts']}",
            f"- **Total Views**: {stats['total_views']:,}",
            f"- **Total Likes**: {stats['total_likes']:,}",
            f"- **Total Comments**: {stats['total_comments']:,}",
            f"- **Total Shares**: {stats['total_shares']:,}",
            f"- **Engagement Rate**: {stats['engagement_rate']}%",
            f"- **Avg Views/Post**: {stats['avg_views_per_post']}",
        ]
        return "\n".join(lines)

    def generate_weekly_report(self) -> str:
        """Generate a weekly performance summary.

        Returns:
            Markdown-formatted report string.
        """
        tracker = self._get_tracker()
        confidence = self._get_confidence()
        stats = tracker.aggregate_stats(days=7)
        top_hooks = confidence.get_top_hooks(limit=3)

        lines = [
            "# Weekly Performance Report",
            "",
            "## Overview",
            f"- **Posts**: {stats['total_posts']}",
            f"- **Total Views**: {stats['total_views']:,}",
            f"- **Engagement Rate**: {stats['engagement_rate']}%",
            f"- **Avg Views/Post**: {stats['avg_views_per_post']}",
            "",
            "## Top Performing Hooks",
        ]
        for hook_type, score in top_hooks:
            lines.append(f"- **{hook_type}**: {score:.2f} confidence")

        return "\n".join(lines)

    def export_json(self) -> dict:
        """Export analytics data as JSON-serializable dict.

        Returns:
            Dict with stats and confidence data.
        """
        tracker = self._get_tracker()
        confidence = self._get_confidence()
        return {
            "stats": tracker.aggregate_stats(),
            "top_hooks": confidence.get_top_hooks(),
            "all_scores": confidence.get_all_scores(),
        }
