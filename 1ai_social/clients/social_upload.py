"""Social Upload client for PostBridge multi-platform distribution."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseClient
from ..models import Post, Content, Platform
from ..logging_config import get_logger

logger = get_logger(__name__)


# Optimal posting times by platform (24h format, local time)
OPTIMAL_TIMES = {
    Platform.TIKTOK: [19, 20, 21],        # 7pm-9pm
    Platform.INSTAGRAM: [11, 12, 19, 20],  # 11am-1pm, 7pm-9pm
    Platform.X: [8, 9, 12, 13],            # 8am-10am, 12pm-1pm
    Platform.LINKEDIN: [8, 9],             # 8am-10am weekdays
    Platform.FACEBOOK: [13, 14, 15],       # 1pm-4pm
}


class SocialUploadClient(BaseClient):
    """Client for PostBridge API — multi-platform social media distribution.

    Handles media upload, post creation, scheduling, and account management
    across TikTok, Instagram, X, LinkedIn, and Facebook.
    """

    def __init__(self, config=None):
        """Initialize SocialUploadClient.

        Args:
            config: Config instance. If None, will load on connect.
        """
        self._config = config
        self._session: Optional[requests.Session] = None
        self._connected = False
        self._base_url = "https://api.postbridge.io"

    def health_check(self) -> bool:
        """Check if PostBridge API key is configured.

        Returns:
            True if API key is available.
        """
        if not self._config:
            return False
        api_key = self._config.get("postbridge_api_key", None)
        return bool(api_key)

    def connect(self) -> None:
        """Initialize HTTP session with PostBridge authentication."""
        if self._connected:
            logger.debug("SocialUploadClient already connected")
            return

        self._session = requests.Session()

        if self._config:
            api_key = self._config.get("postbridge_api_key", "")
            self._base_url = self._config.get(
                "postbridge.base_url", "https://api.postbridge.io"
            )
            self._session.headers.update(
                {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
            )

        self._connected = True
        logger.info(f"SocialUploadClient connected to {self._base_url}")

    def disconnect(self) -> None:
        """Close HTTP session."""
        if self._session:
            self._session.close()
            self._session = None
        self._connected = False
        logger.info("SocialUploadClient disconnected")

    def _ensure_connected(self):
        """Ensure client is connected before making API calls."""
        if not self._connected:
            self.connect()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
    def upload_media(self, file_path: str, platform: Platform) -> str:
        """Upload media file to PostBridge.

        Args:
            file_path: Path to media file (image or video).
            platform: Target platform for format validation.

        Returns:
            media_id string from PostBridge.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If format not supported for platform.
            RuntimeError: If upload fails.
        """
        self._ensure_connected()

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {file_path}")

        # Platform format validation
        self._validate_media_format(path, platform)

        logger.info(f"Uploading {file_path} for {platform.value}")

        url = f"{self._base_url}/media/upload"
        with open(path, "rb") as f:
            files = {"file": (path.name, f)}
            # Remove Content-Type header for multipart upload
            headers = dict(self._session.headers)
            headers.pop("Content-Type", None)
            resp = self._session.post(url, files=files, headers=headers, timeout=60)

        resp.raise_for_status()
        data = resp.json()
        media_id = data.get("id", data.get("media_id", ""))

        logger.info(f"Media uploaded: {media_id}")
        return media_id

    def _validate_media_format(self, path: Path, platform: Platform) -> None:
        """Validate media format for target platform.

        Args:
            path: File path.
            platform: Target platform.

        Raises:
            ValueError: If format not supported.
        """
        ext = path.suffix.lower()

        platform_formats = {
            Platform.TIKTOK: [".mp4", ".mov"],
            Platform.INSTAGRAM: [".mp4", ".mov", ".jpg", ".jpeg", ".png"],
            Platform.X: [".mp4", ".mov", ".jpg", ".jpeg", ".png", ".gif"],
            Platform.LINKEDIN: [".mp4", ".mov", ".jpg", ".jpeg", ".png"],
            Platform.FACEBOOK: [".mp4", ".mov", ".jpg", ".jpeg", ".png", ".gif"],
        }

        allowed = platform_formats.get(platform, [])
        if allowed and ext not in allowed:
            raise ValueError(
                f"Format '{ext}' not supported for {platform.value}. "
                f"Allowed: {allowed}"
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
    def create_post(
        self,
        media_id: str,
        caption: str,
        schedule_time: Optional[datetime] = None,
        platforms: Optional[List[Platform]] = None,
    ) -> Post:
        """Create a post on social media platforms.

        Args:
            media_id: ID from upload_media.
            caption: Post caption text.
            schedule_time: When to publish (None = immediate).
            platforms: Target platforms (None = all connected).

        Returns:
            Post model with creation details.
        """
        self._ensure_connected()

        url = f"{self._base_url}/posts"
        platform_values = (
            [p.value for p in platforms] if platforms else []
        )

        payload: Dict[str, Any] = {
            "media_id": media_id,
            "caption": caption,
            "schedule_time": schedule_time.isoformat() if schedule_time else None,
            "platforms": platform_values,
        }

        logger.info(f"Creating post for platforms: {platform_values or 'all'}")

        resp = self._session.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        return Post(
            id=data.get("id", ""),
            content=Content(
                text=caption,
                platform=platforms[0] if platforms else Platform.TIKTOK,
                media_url=media_id,
            ),
            scheduled_time=schedule_time,
            status="scheduled" if schedule_time else "published",
            platform_post_id=data.get("platform_post_id"),
        )

    def get_accounts(self) -> List[Dict[str, Any]]:
        """Get list of connected social media accounts.

        Returns:
            List of account dicts with platform, username, connected status.
        """
        self._ensure_connected()

        url = f"{self._base_url}/accounts"
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json().get("accounts", [])
        except Exception as e:
            logger.warning(f"Failed to get accounts: {e}")
            return []

    def schedule_post(
        self, post: Post, optimal_time: Optional[datetime] = None
    ) -> Post:
        """Schedule a post at optimal time for its platform.

        Args:
            post: Post to schedule.
            optimal_time: Override time (None = calculate optimal).

        Returns:
            Updated Post with scheduled_time set.
        """
        if optimal_time is None:
            optimal_time = self._calculate_optimal_time(
                post.content.platform
            )

        logger.info(
            f"Scheduling post {post.id} for "
            f"{optimal_time.isoformat()} on {post.content.platform.value}"
        )

        return Post(
            id=post.id,
            content=post.content,
            scheduled_time=optimal_time,
            status="scheduled",
            platform_post_id=post.platform_post_id,
        )

    def _calculate_optimal_time(
        self, platform: Platform
    ) -> datetime:
        """Calculate optimal posting time for a platform.

        Args:
            platform: Target platform.

        Returns:
            Next optimal datetime for posting.
        """
        optimal_hours = OPTIMAL_TIMES.get(platform, [12])

        now = datetime.now()
        today_optimal = None

        for hour in sorted(optimal_hours):
            candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate > now:
                today_optimal = candidate
                break

        if today_optimal:
            return today_optimal

        # Schedule for tomorrow's first optimal time
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(
            hour=optimal_hours[0], minute=0, second=0, microsecond=0
        )

    def delete_post(self, post_id: str) -> bool:
        """Delete a scheduled post.

        Args:
            post_id: Post ID to delete.

        Returns:
            True if deleted successfully.
        """
        self._ensure_connected()

        url = f"{self._base_url}/posts/{post_id}"
        try:
            resp = self._session.delete(url, timeout=15)
            resp.raise_for_status()
            logger.info(f"Post {post_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete post {post_id}: {e}")
            return False
