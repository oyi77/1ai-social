"""Main orchestrator tying together the full content pipeline."""

from typing import Dict, List, Any, Optional
from ..models import Platform, Post
from ..logging_config import get_logger

logger = get_logger(__name__)


class Orchestrator:
    """Orchestrates the full content generation and distribution pipeline.

    Pipeline: Generate hooks → Create video → Polish caption → Distribute
    """

    def __init__(self):
        self._planner = None
        self._hook_generator = None
        self._video_pipeline = None
        self._caption_polisher = None
        self._post_distributor = None

    def _get_planner(self):
        if self._planner is None:
            from .planner import ContentPlanner

            self._planner = ContentPlanner()
        return self._planner

    def _get_hook_generator(self):
        if self._hook_generator is None:
            from ..generators.hook_generator import HookGenerator

            self._hook_generator = HookGenerator()
        return self._hook_generator

    def _get_video_pipeline(self):
        if self._video_pipeline is None:
            from ..generators.video_pipeline import VideoPipeline

            self._video_pipeline = VideoPipeline()
        return self._video_pipeline

    def _get_caption_polisher(self):
        if self._caption_polisher is None:
            from ..generators.caption_polisher import CaptionPolisher

            self._caption_polisher = CaptionPolisher()
        return self._caption_polisher

    def _get_post_distributor(self):
        if self._post_distributor is None:
            from .post_distributor import PostDistributor

            self._post_distributor = PostDistributor()
        return self._post_distributor

    def generate_and_post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Run the full content pipeline: hooks → video → caption → distribute.

        Args:
            request: Dict with keys: niche, platforms, content_type, count.

        Returns:
            Result dict with status, posts, hooks, errors.
        """
        niche = request.get("niche", "AI")
        platforms_input = request.get("platforms", ["tiktok"])
        content_type = request.get("content_type", "video")
        count = request.get("count", 1)

        platforms = []
        for p in platforms_input:
            if isinstance(p, str):
                platforms.append(Platform(p))
            else:
                platforms.append(p)

        errors: List[str] = []
        hooks_used: List[Dict[str, Any]] = []
        posts_results: List[Dict[str, Any]] = []

        # Step 1: Generate hooks
        try:
            hook_gen = self._get_hook_generator()
            hooks = hook_gen.generate_viral_hooks(niche, count=3)
            winner = hook_gen.select_winner(hooks)
            hooks_used.append(
                {
                    "text": winner.text,
                    "type": winner.type,
                    "confidence": winner.confidence,
                }
            )
            logger.info(f"Hook selected: {winner.type} ({winner.confidence})")
        except Exception as e:
            errors.append(f"Hook generation failed: {e}")
            logger.error(f"Hook generation failed: {e}")

        # Step 2: Generate video/image
        video_result = None
        try:
            pipeline = self._get_video_pipeline()
            content_dict = {
                "text": hooks_used[0]["text"]
                if hooks_used
                else f"Amazing {niche} content",
                "template_id": "tiktok-viral-short",
                "duration": 60,
            }
            video_result = pipeline.generate_video(content_dict, style="9:16")
            logger.info(f"Video generated: {getattr(video_result, 'path', 'N/A')}")
        except Exception as e:
            errors.append(f"Video generation failed: {e}")
            logger.error(f"Video generation failed: {e}")

        # Step 3: Polish captions per platform
        captions = {}
        try:
            polisher = self._get_caption_polisher()
            raw_caption = (
                hooks_used[0]["text"]
                if hooks_used
                else f"Check out this {niche} content!"
            )
            for platform in platforms:
                captions[platform.value] = polisher.polish(raw_caption, platform)
        except Exception as e:
            errors.append(f"Caption polishing failed: {e}")
            for platform in platforms:
                captions[platform.value] = f"Check out this {niche} content!"

        # Step 4: Distribute
        try:
            distributor = self._get_post_distributor()
            content = {
                "text": hooks_used[0]["text"] if hooks_used else "",
                "media_path": getattr(video_result, "path", "") if video_result else "",
                "caption": captions.get(platforms[0].value, "") if platforms else "",
            }
            dist_results = distributor.distribute(content, platforms)
            posts_results.append(dist_results)
        except Exception as e:
            errors.append(f"Distribution failed: {e}")
            logger.error(f"Distribution failed: {e}")

        status = "success" if not errors else ("partial" if posts_results else "failed")

        return {
            "status": status,
            "posts": posts_results,
            "hooks_used": hooks_used,
            "errors": errors,
        }

    def generate_content_only(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate content without posting (preview mode).

        Args:
            request: Dict with niche, content_type, count.

        Returns:
            Preview dict with hooks, caption, video info.
        """
        niche = request.get("niche", "AI")
        content_type = request.get("content_type", "video")

        try:
            hook_gen = self._get_hook_generator()
            hooks = hook_gen.generate_viral_hooks(niche, count=5)
            winner = hook_gen.select_winner(hooks)
        except Exception as e:
            logger.error(f"Hook generation failed: {e}")
            winner = None
            hooks = []

        try:
            polisher = self._get_caption_polisher()
            caption = polisher.polish(
                winner.text if winner else f"Amazing {niche} content",
                Platform.TIKTOK,
            )
        except Exception as e:
            logger.error(f"Polish failed: {e}")
            caption = winner.text if winner else ""

        return {
            "hooks": [
                {"text": h.text, "type": h.type, "confidence": h.confidence}
                for h in hooks
            ],
            "winner": {"text": winner.text, "type": winner.type} if winner else None,
            "caption": caption,
            "niche": niche,
        }

    def schedule_campaign(
        self, request: Dict[str, Any], days: int = 7
    ) -> Dict[str, Any]:
        """Create and schedule a full content campaign.

        Args:
            request: Dict with niche, platforms.
            days: Number of days for the campaign.

        Returns:
            Campaign dict with calendar and scheduled posts.
        """
        niche = request.get("niche", "AI")
        platforms_input = request.get("platforms", ["tiktok"])

        platforms = []
        for p in platforms_input:
            if isinstance(p, str):
                platforms.append(Platform(p))
            else:
                platforms.append(p)

        try:
            planner = self._get_planner()
            calendar = planner.generate_calendar(niche, days)
        except Exception as e:
            logger.error(f"Calendar generation failed: {e}")
            calendar = []

        scheduled_posts = []
        for day_plan in calendar:
            result = self.generate_and_post(
                {
                    "niche": niche,
                    "platforms": [p.value for p in platforms],
                    "content_type": day_plan.get("content_type", "video"),
                }
            )
            if result.get("posts"):
                scheduled_posts.append(result)

        return {
            "niche": niche,
            "days": days,
            "calendar": calendar,
            "scheduled_count": len(scheduled_posts),
            "results": scheduled_posts,
        }
