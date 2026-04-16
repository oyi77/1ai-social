"""Analytics tracker for post performance metrics."""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..models import Platform
from ..logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "analytics.json"


class AnalyticsTracker:
    """Tracks and stores post performance metrics."""

    def __init__(self, data_path: Optional[str] = None):
        self._path = Path(data_path) if data_path else DEFAULT_DATA_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._records: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._records, indent=2, default=str))

    def track_post(self, post_id: str, metrics: Dict[str, Any]) -> None:
        """Record metrics for a post.

        Args:
            post_id: Post identifier.
            metrics: Dict with keys like views, likes, shares, comments.
        """
        self._records[post_id] = {
            "post_id": post_id,
            "metrics": metrics,
            "recorded_at": datetime.utcnow().isoformat(),
        }
        self._save()
        logger.info(f"Tracked post {post_id}: {metrics}")

    def get_stats(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific post.

        Args:
            post_id: Post identifier.

        Returns:
            Metrics dict or None if not found.
        """
        record = self._records.get(post_id)
        return record.get("metrics") if record else None

    def aggregate_stats(
        self, platform: Optional[Platform] = None, days: int = 30
    ) -> Dict[str, Any]:
        """Aggregate statistics across posts.

        Args:
            platform: Filter by platform (None for all).
            days: Number of days to look back.

        Returns:
            Aggregated stats dict.
        """
        total_views = 0
        total_likes = 0
        total_shares = 0
        total_comments = 0
        post_count = 0

        for record in self._records.values():
            metrics = record.get("metrics", {})
            total_views += metrics.get("views", 0)
            total_likes += metrics.get("likes", 0)
            total_shares += metrics.get("shares", 0)
            total_comments += metrics.get("comments", 0)
            post_count += 1

        engagement_rate = 0.0
        if total_views > 0:
            engagement_rate = (
                (total_likes + total_comments + total_shares) / total_views
            ) * 100

        return {
            "total_posts": post_count,
            "total_views": total_views,
            "total_likes": total_likes,
            "total_shares": total_shares,
            "total_comments": total_comments,
            "engagement_rate": round(engagement_rate, 2),
            "avg_views_per_post": round(total_views / max(post_count, 1), 1),
        }

    def get_all_records(self) -> Dict[str, Dict[str, Any]]:
        """Get all tracked records.

        Returns:
            Dict of post_id → record data.
        """
        return dict(self._records)
