from typing import Dict, Any, Optional, Union
from ..models import Video
from ..logging_config import get_logger
from ..clients.content_generator import ContentGeneratorClient
from ..clients.remotion import RemotionClient

logger = get_logger(__name__)


class VideoPipeline:
    """Routes video generation requests to appropriate providers based on content type."""

    def __init__(self):
        """Initialize pipeline with provider priority list."""
        self.provider_priority = ["remotion", "content_generator", "placeholder"]
        self._content_generator_client: Optional[ContentGeneratorClient] = None
        self._remotion_client: Optional[RemotionClient] = None

    def generate_video(
        self, content_dict: Dict[str, Any], style: str = "9:16"
    ) -> Union[Video, Dict[str, Any]]:
        """
        Generate video by routing to appropriate provider.

        Args:
            content_dict: Dict with keys: text, images, template_id (optional), duration
            style: Video aspect ratio (default "9:16")

        Returns:
            Video model object or dict with path/duration/format
        """
        provider = self._select_provider(content_dict)
        logger.info(f"Selected provider: {provider}")

        try:
            if provider == "remotion":
                return self._generate_with_remotion(content_dict, style)
            elif provider == "content_generator":
                return self._generate_with_content_generator(content_dict, style)
            else:
                return self.fallback_generation(content_dict)
        except Exception as e:
            logger.error(f"Provider {provider} failed: {e}")
            # Try next provider in priority list
            remaining_providers = [p for p in self.provider_priority if p != provider]
            for next_provider in remaining_providers:
                try:
                    if next_provider == "remotion":
                        return self._generate_with_remotion(content_dict, style)
                    elif next_provider == "content_generator":
                        return self._generate_with_content_generator(
                            content_dict, style
                        )
                except Exception as fallback_error:
                    logger.warning(
                        f"Fallback provider {next_provider} failed: {fallback_error}"
                    )
                    continue
            # All providers failed, use placeholder
            return self.fallback_generation(content_dict)

    def _select_provider(self, content: Dict[str, Any]) -> str:
        """
        Determine which provider to use based on content type.

        Args:
            content: Content dictionary with text, images, template_id, duration

        Returns:
            Provider name: "remotion", "content_generator", or "placeholder"
        """
        # Remotion preferred for template-based content
        if content.get("template_id"):
            return "remotion"

        # Content generator for AI video generation
        if content.get("text") and not content.get("template_id"):
            return "content_generator"

        # Fallback for minimal content
        return "placeholder"

    def _generate_with_remotion(
        self, content_dict: Dict[str, Any], style: str
    ) -> Union[Video, Dict[str, Any]]:
        """Generate video using Remotion provider."""
        if self._remotion_client is None:
            self._remotion_client = RemotionClient()

        result = self._remotion_client.generate(
            content=content_dict,
            style=style,
        )
        return result

    def _generate_with_content_generator(
        self, content_dict: Dict[str, Any], style: str
    ) -> Union[Video, Dict[str, Any]]:
        """Generate video using ContentGenerator provider."""
        if self._content_generator_client is None:
            self._content_generator_client = ContentGeneratorClient()

        result = self._content_generator_client.generate(
            content=content_dict,
            style=style,
        )
        return result

    def fallback_generation(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create placeholder video when all providers fail.

        Args:
            content: Content dictionary

        Returns:
            Dict with path, duration, format, width, height
        """
        logger.warning("Using placeholder video generation")
        return {
            "path": "/tmp/placeholder_video.mp4",
            "duration": content.get("duration", 60.0),
            "format": "mp4",
            "width": 1080,
            "height": 1920,
        }
