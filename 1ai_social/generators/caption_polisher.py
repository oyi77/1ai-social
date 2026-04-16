"""Caption polisher using humanizer for platform-specific optimization."""

from typing import List, Optional
from ..models import Platform
from ..logging_config import get_logger

logger = get_logger(__name__)

PLATFORM_CTA = {
    Platform.TIKTOK: "link in bio 🔗",
    Platform.INSTAGRAM: "save for later 📌",
    Platform.X: "RT if you agree 💬",
    Platform.LINKEDIN: "What do you think? Comment below 👇",
    Platform.FACEBOOK: "Share with a friend who needs this 🤝",
}

PLATFORM_HASHTAGS = {
    Platform.TIKTOK: ["#fyp", "#viral", "#ai", "#tech", "#foryou"],
    Platform.INSTAGRAM: [
        "#ai",
        "#artificialintelligence",
        "#tech",
        "#innovation",
        "#digital",
        "#future",
        "#automation",
        "#machinelearning",
        "#aitools",
        "#creative",
        "#contentcreator",
        "#viral",
        "#trending",
        "#reels",
        "#instagood",
        "#inspiration",
        "#techcommunity",
        "#aiart",
        "#growth",
        "#mindset",
    ],
    Platform.X: ["#AI", "#Tech"],
    Platform.LINKEDIN: [
        "#AI",
        "#Innovation",
        "#FutureOfWork",
        "#TechTrends",
        "#DigitalTransformation",
    ],
    Platform.FACEBOOK: ["#AI", "#Tech"],
}


class CaptionPolisher:
    """Polishes captions using humanizer with platform-specific optimization."""

    def __init__(self):
        self._humanizer = None

    def _get_humanizer(self):
        if self._humanizer is None:
            from ..clients.humanizer import HumanizerClient
            from ..config import Config

            config = Config.load()
            self._humanizer = HumanizerClient(config)
        return self._humanizer

    def polish(self, caption: str, platform: Platform) -> str:
        """Polish caption for a specific platform.

        Args:
            caption: Raw caption text.
            platform: Target platform.

        Returns:
            Platform-optimized caption string.
        """
        humanizer = self._get_humanizer()

        try:
            humanized = humanizer.humanize(caption, platform.value)
        except Exception as e:
            logger.warning(f"Humanizer failed, using original: {e}")
            humanized = caption

        cta = PLATFORM_CTA.get(platform, "")
        hashtags = self._format_hashtags(platform)

        parts = [humanized]
        if cta:
            parts.append(f"\n\n{cta}")
        if hashtags:
            parts.append(f"\n\n{hashtags}")

        result = "".join(parts)
        logger.info(f"Caption polished for {platform.value}: {len(result)} chars")
        return result

    def add_hooks(self, cta_type: str) -> str:
        """Generate CTA string by type.

        Args:
            cta_type: One of "engagement", "share", "follow", "link".

        Returns:
            CTA text string.
        """
        cta_templates = {
            "engagement": "Drop a 🔥 if you agree! Comment your thoughts below.",
            "share": "Share this with someone who needs to see it! 🔄",
            "follow": "Follow for more AI content daily! 🚀",
            "link": "Full guide in bio — click the link! 🔗",
        }
        return cta_templates.get(cta_type, "")

    def optimize_for_algorithm(self, platform: Platform) -> List[str]:
        """Get recommended hashtags for a platform.

        Args:
            platform: Target platform.

        Returns:
            List of recommended hashtags.
        """
        return PLATFORM_HASHTAGS.get(platform, [])

    def _format_hashtags(self, platform: Platform) -> str:
        """Format hashtags for a platform.

        Args:
            platform: Target platform.

        Returns:
            Formatted hashtag string.
        """
        tags = PLATFORM_HASHTAGS.get(platform, [])[:5]
        return " ".join(tags)
