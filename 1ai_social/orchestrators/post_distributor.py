"""Post distributor for multi-platform social media distribution."""

from typing import Dict, List, Any, Optional
from datetime import datetime

from ..models import Platform, Post, Content
from ..logging_config import get_logger

logger = get_logger(__name__)


class PostDistributor:
    """Distributes content across multiple social media platforms."""

    def __init__(self):
        self._upload_client = None

    def _get_upload_client(self):
        if self._upload_client is None:
            from ..clients.social_upload import SocialUploadClient

            self._upload_client = SocialUploadClient()
        return self._upload_client

    def distribute(
        self, content: Dict[str, Any], platforms: List[Platform]
    ) -> Dict[str, Dict[str, Any]]:
        """Distribute content to multiple platforms.

        Args:
            content: Dict with keys: text, media_path, caption, hashtags.
            platforms: List of Platform values to distribute to.

        Returns:
            Dict mapping platform name to result: {post_id, status, error}.
        """
        client = self._get_upload_client()
        results: Dict[str, Dict[str, Any]] = {}

        for platform in platforms:
            try:
                media_path = content.get("media_path", "")
                media_id = ""
                if media_path:
                    media_id = client.upload_media(media_path, platform)

                caption = content.get("caption", content.get("text", ""))
                post = client.create_post(
                    media_id=media_id,
                    caption=caption,
                    platforms=[platform],
                )

                results[platform.value] = {
                    "post_id": post.id,
                    "status": "success",
                    "error": None,
                }
                logger.info(f"Distributed to {platform.value}: {post.id}")

            except Exception as e:
                results[platform.value] = {
                    "post_id": None,
                    "status": "failed",
                    "error": str(e),
                }
                logger.error(f"Failed to distribute to {platform.value}: {e}")

        success_count = sum(1 for r in results.values() if r["status"] == "success")
        logger.info(
            f"Distribution complete: {success_count}/{len(platforms)} succeeded"
        )
        return results

    def schedule_batch(self, posts: List[Dict[str, Any]]) -> List[Post]:
        """Schedule multiple posts at optimal times.

        Args:
            posts: List of dicts with content and platform info.

        Returns:
            List of scheduled Post objects.
        """
        client = self._get_upload_client()
        scheduled: List[Post] = []

        for post_data in posts:
            try:
                platform = post_data.get("platform", Platform.TIKTOK)
                if isinstance(platform, str):
                    platform = Platform(platform)

                content = Content(
                    text=post_data.get("caption", ""),
                    platform=platform,
                    media_url=post_data.get("media_path"),
                )
                post = Post(
                    id=post_data.get("id", f"sched_{len(scheduled)}"),
                    content=content,
                    status="draft",
                )
                scheduled_post = client.schedule_post(post)
                scheduled.append(scheduled_post)

            except Exception as e:
                logger.error(f"Failed to schedule post: {e}")

        logger.info(f"Scheduled {len(scheduled)} posts")
        return scheduled

    def retry_failed(
        self, results: Dict[str, Dict[str, Any]], content: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """Retry failed platform distributions.

        Args:
            results: Previous results dict from distribute().
            content: Original content dict.

        Returns:
            Updated results dict with retry outcomes.
        """
        failed_platforms = [
            Platform(p) for p, r in results.items() if r["status"] == "failed"
        ]

        if not failed_platforms:
            logger.info("No failed distributions to retry")
            return results

        logger.info(f"Retrying {len(failed_platforms)} failed distributions")
        retry_results = self.distribute(content, failed_platforms)

        results.update(retry_results)
        return results
