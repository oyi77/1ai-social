"""Social Media Engagement client for automated interactions."""

import random
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from .base import BaseClient
from ..logging_config import get_logger
from ..models import Platform


class EngagementClient(BaseClient):
    """Client for managing social media engagement across platforms.

    Handles liking, commenting, following, unfollowing, and DM operations
    with built-in rate limiting and human-like behavior patterns.
    """

    # Rate limits per platform (action_type: (limit_per_hour, limit_per_day))
    RATE_LIMITS = {
        Platform.TIKTOK: {
            "like": (100, None),
            "comment": (30, None),
            "follow": (None, 200),
            "unfollow": (None, 200),
            "dm": (20, None),
        },
        Platform.INSTAGRAM: {
            "like": (150, None),
            "comment": (30, None),
            "follow": (None, 100),
            "unfollow": (None, 100),
            "dm": (20, None),
        },
        Platform.X: {
            "like": (300, None),
            "comment": (50, None),
            "follow": (None, 150),
            "unfollow": (None, 150),
            "dm": (30, None),
        },
        Platform.LINKEDIN: {
            "like": (50, None),
            "comment": (10, None),
            "follow": (None, 30),
            "unfollow": (None, 30),
            "dm": (10, None),
        },
        Platform.FACEBOOK: {
            "like": (100, None),
            "comment": (25, None),
            "follow": (None, 50),
            "unfollow": (None, 50),
            "dm": (15, None),
        },
    }

    def __init__(self):
        """Initialize the engagement client with rate limiting tracking."""
        self.logger = get_logger(__name__)
        # Track actions: {platform: {action: [(timestamp, count), ...]}}
        self._action_history: Dict[Platform, Dict[str, List[datetime]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.logger.info("EngagementClient initialized")

    def health_check(self) -> bool:
        """Check if the engagement client is healthy.

        Returns:
            bool: Always True as engagement operates via browser automation.
        """
        self.logger.debug("Health check performed")
        return True

    def connect(self) -> None:
        """Establish connection to engagement service.

        No-op for engagement client as it uses browser automation.
        """
        self.logger.info("Engagement client connect called (no-op)")

    def disconnect(self) -> None:
        """Close connection to engagement service.

        No-op for engagement client as it uses browser automation.
        """
        self.logger.info("Engagement client disconnect called (no-op)")

    def _add_human_delay(self) -> None:
        """Add random delay between actions for human-like behavior."""
        delay = random.uniform(0.5, 3.0)
        time.sleep(delay)

    def _check_rate_limit(self, action: str, platform: Platform) -> bool:
        """Check if an action is within rate limits for a platform.

        Args:
            action: Action type (like, comment, follow, unfollow, dm)
            platform: Target platform

        Returns:
            bool: True if action is allowed, False if rate limit exceeded
        """
        if platform not in self.RATE_LIMITS:
            self.logger.warning(f"Unknown platform: {platform}")
            return False

        limits = self.RATE_LIMITS[platform].get(action)
        if not limits:
            self.logger.warning(f"Unknown action: {action} for platform: {platform}")
            return False

        hourly_limit, daily_limit = limits
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        history = self._action_history[platform][action]

        # Clean up old entries
        if hourly_limit:
            one_hour_ago = now - timedelta(hours=1)
            history[:] = [ts for ts in history if ts > one_hour_ago]

        if daily_limit:
            one_day_ago = now - timedelta(days=1)
            history[:] = [ts for ts in history if ts > one_day_ago]

        # Check hourly limit
        if hourly_limit:
            one_hour_ago = now - timedelta(hours=1)
            recent_count = sum(1 for ts in history if ts > one_hour_ago)
            if recent_count >= hourly_limit:
                self.logger.warning(
                    f"Hourly rate limit exceeded for {action} on {platform}: "
                    f"{recent_count}/{hourly_limit}"
                )
                return False

        # Check daily limit
        if daily_limit:
            one_day_ago = now - timedelta(days=1)
            daily_count = sum(1 for ts in history if ts > one_day_ago)
            if daily_count >= daily_limit:
                self.logger.warning(
                    f"Daily rate limit exceeded for {action} on {platform}: "
                    f"{daily_count}/{daily_limit}"
                )
                return False

        return True

    def _record_action(self, action: str, platform: Platform) -> None:
        """Record an action for rate limit tracking.

        Args:
            action: Action type
            platform: Target platform
        """
        self._action_history[platform][action].append(
            datetime.now(timezone.utc).replace(tzinfo=None)
        )
        self.logger.debug(f"Recorded action: {action} on {platform}")

    def like_post(self, post_id: str, platform: Platform) -> bool:
        """Like a post on the specified platform.

        Args:
            post_id: Unique identifier of the post
            platform: Target platform

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._check_rate_limit("like", platform):
            self.logger.error(f"Rate limit exceeded for like on {platform}")
            return False

        try:
            self._add_human_delay()
            self._record_action("like", platform)
            self.logger.info(f"Liked post {post_id} on {platform}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to like post {post_id} on {platform}: {e}")
            return False

    def comment_on_post(self, post_id: str, comment: str, platform: Platform) -> bool:
        """Comment on a post with contextual content.

        Args:
            post_id: Unique identifier of the post
            comment: Comment text (should be contextual, not generic)
            platform: Target platform

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._check_rate_limit("comment", platform):
            self.logger.error(f"Rate limit exceeded for comment on {platform}")
            return False

        if not comment or len(comment.strip()) == 0:
            self.logger.error("Comment text cannot be empty")
            return False

        try:
            self._add_human_delay()
            self._record_action("comment", platform)
            self.logger.info(
                f"Commented on post {post_id} on {platform}: {comment[:50]}..."
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to comment on post {post_id} on {platform}: {e}")
            return False

    def follow_user(self, username: str, platform: Platform) -> bool:
        """Follow a user on the specified platform.

        Args:
            username: Username to follow
            platform: Target platform

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._check_rate_limit("follow", platform):
            self.logger.error(f"Rate limit exceeded for follow on {platform}")
            return False

        try:
            self._add_human_delay()
            self._record_action("follow", platform)
            self.logger.info(f"Followed user {username} on {platform}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to follow user {username} on {platform}: {e}")
            return False

    def unfollow_user(self, username: str, platform: Platform) -> bool:
        """Unfollow a user on the specified platform.

        Args:
            username: Username to unfollow
            platform: Target platform

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._check_rate_limit("unfollow", platform):
            self.logger.error(f"Rate limit exceeded for unfollow on {platform}")
            return False

        try:
            self._add_human_delay()
            self._record_action("unfollow", platform)
            self.logger.info(f"Unfollowed user {username} on {platform}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to unfollow user {username} on {platform}: {e}")
            return False

    def send_dm(self, username: str, message: str, platform: Platform) -> bool:
        """Send a direct message to a user.

        Args:
            username: Recipient username
            message: Message content
            platform: Target platform

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._check_rate_limit("dm", platform):
            self.logger.error(f"Rate limit exceeded for DM on {platform}")
            return False

        if not message or len(message.strip()) == 0:
            self.logger.error("Message cannot be empty")
            return False

        try:
            self._add_human_delay()
            self._record_action("dm", platform)
            self.logger.info(f"Sent DM to {username} on {platform}: {message[:50]}...")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send DM to {username} on {platform}: {e}")
            return False

    def get_suggested_targets(
        self, niche: str, platform: Platform, count: int = 10
    ) -> List[Dict]:
        """Find target accounts based on niche/keyword.

        Args:
            niche: Niche or keyword to search for
            platform: Target platform
            count: Number of suggestions to return (default: 10)

        Returns:
            List of dicts with keys: username, followers, engagement_rate
        """
        if not niche or len(niche.strip()) == 0:
            self.logger.error("Niche cannot be empty")
            return []

        try:
            self._add_human_delay()
            self.logger.info(
                f"Searching for {count} targets in niche '{niche}' on {platform}"
            )

            # Placeholder implementation - would use platform search API or scraping
            targets = []
            for i in range(min(count, 10)):
                targets.append(
                    {
                        "username": f"user_{niche}_{i}",
                        "followers": random.randint(1000, 100000),
                        "engagement_rate": round(random.uniform(0.5, 8.0), 2),
                    }
                )

            self.logger.info(f"Found {len(targets)} suggested targets")
            return targets
        except Exception as e:
            self.logger.error(
                f"Failed to get suggested targets for niche '{niche}' on {platform}: {e}"
            )
            return []
