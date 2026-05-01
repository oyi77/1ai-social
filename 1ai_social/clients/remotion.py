"""Remotion programmatic video rendering client for 1ai-social."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseClient
from ..logging_config import get_logger

logger = get_logger(__name__)


class RemotionClient(BaseClient):
    """Client for rendering videos using Remotion templates."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize Remotion client.

        Args:
            templates_dir: Path to templates directory. Defaults to skills/remotion/templates/
        """
        self.templates_dir = (
            templates_dir
            or Path(__file__).parent.parent.parent / "skills" / "remotion" / "templates"
        )
        self.connected = False
        self.node_available = False
        logger.info(
            f"Initialized RemotionClient with templates_dir: {self.templates_dir}"
        )

    def health_check(self) -> bool:
        """Check if Node.js and Remotion CLI are available.

        Returns:
            bool: True if Node.js is available, False otherwise.
        """
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Node.js available: {result.stdout.strip()}")
                return True
            else:
                logger.warning("Node.js check failed")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Node.js not available: {e}")
            return False

    def connect(self) -> None:
        """Verify Node.js is available and mark as connected."""
        self.node_available = self.health_check()
        if self.node_available:
            logger.info("RemotionClient connected successfully")
            self.connected = True
        else:
            logger.warning(
                "RemotionClient connected but Node.js not available - renders will fail"
            )
            self.connected = True

    def disconnect(self) -> None:
        """Cleanup and disconnect."""
        self.connected = False
        logger.info("RemotionClient disconnected")

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available Remotion templates.

        Returns:
            List of template dictionaries with id, name, description, genre, etc.
        """
        templates = [
            {
                "id": "tiktok-viral-short",
                "name": "TikTok Viral Short",
                "description": "Fast-paced vertical video optimized for TikTok virality",
                "genre": "social",
                "duration_range": (15, 60),
                "required_assets": ["text", "images", "audio"],
            },
            {
                "id": "brand-logo-intro",
                "name": "Brand Logo Intro",
                "description": "Professional logo animation for brand identity",
                "genre": "branding",
                "duration_range": (5, 15),
                "required_assets": ["logo", "colors"],
            },
            {
                "id": "product-launch-commercial",
                "name": "Product Launch Commercial",
                "description": "High-energy commercial for product launches",
                "genre": "advertising",
                "duration_range": (30, 90),
                "required_assets": ["product_images", "text", "audio"],
            },
            {
                "id": "ugc-testimonial-ad",
                "name": "UGC Testimonial Ad",
                "description": "User-generated content style testimonial",
                "genre": "advertising",
                "duration_range": (30, 60),
                "required_assets": ["video_clips", "text"],
            },
            {
                "id": "comedy-meme-pov",
                "name": "Comedy Meme POV",
                "description": "POV-style comedy meme video",
                "genre": "entertainment",
                "duration_range": (15, 45),
                "required_assets": ["text", "images", "audio"],
            },
            {
                "id": "data-story-infographic",
                "name": "Data Story Infographic",
                "description": "Animated infographic for data storytelling",
                "genre": "educational",
                "duration_range": (60, 180),
                "required_assets": ["data", "text", "charts"],
            },
            {
                "id": "gaming-montage",
                "name": "Gaming Montage",
                "description": "Epic gaming highlights montage",
                "genre": "gaming",
                "duration_range": (60, 180),
                "required_assets": ["video_clips", "audio"],
            },
            {
                "id": "movie-trailer-cinematic",
                "name": "Movie Trailer Cinematic",
                "description": "Cinematic movie trailer style video",
                "genre": "entertainment",
                "duration_range": (90, 150),
                "required_assets": ["video_clips", "text", "audio"],
            },
            {
                "id": "music-video-lyric",
                "name": "Music Video Lyric",
                "description": "Lyric video with synchronized text",
                "genre": "music",
                "duration_range": (120, 300),
                "required_assets": ["audio", "lyrics", "images"],
            },
            {
                "id": "podcast-talking-head",
                "name": "Podcast Talking Head",
                "description": "Professional podcast video format",
                "genre": "podcast",
                "duration_range": (300, 3600),
                "required_assets": ["video", "audio", "text"],
            },
            {
                "id": "news-motion-graphics",
                "name": "News Motion Graphics",
                "description": "News-style motion graphics video",
                "genre": "news",
                "duration_range": (60, 180),
                "required_assets": ["text", "images", "data"],
            },
            {
                "id": "sales-vsl",
                "name": "Sales VSL",
                "description": "Video sales letter for conversions",
                "genre": "sales",
                "duration_range": (300, 900),
                "required_assets": ["text", "images", "audio"],
            },
            {
                "id": "documentary-minidoc",
                "name": "Documentary Mini-Doc",
                "description": "Short documentary style video",
                "genre": "documentary",
                "duration_range": (180, 600),
                "required_assets": ["video_clips", "text", "audio"],
            },
            {
                "id": "asmr-product-reveal",
                "name": "ASMR Product Reveal",
                "description": "ASMR-style product showcase",
                "genre": "product",
                "duration_range": (30, 120),
                "required_assets": ["video", "audio"],
            },
            {
                "id": "anime-opening",
                "name": "Anime Opening",
                "description": "Anime-style opening sequence",
                "genre": "anime",
                "duration_range": (60, 90),
                "required_assets": ["images", "text", "audio"],
            },
            {
                "id": "viral-challenge-mrbeast",
                "name": "Viral Challenge MrBeast",
                "description": "MrBeast-style challenge video",
                "genre": "challenge",
                "duration_range": (300, 900),
                "required_assets": ["video_clips", "text", "audio"],
            },
            {
                "id": "viral-challenge-gameshow",
                "name": "Viral Challenge Gameshow",
                "description": "Gameshow-style challenge video",
                "genre": "challenge",
                "duration_range": (300, 600),
                "required_assets": ["video_clips", "text", "audio"],
            },
            {
                "id": "year-in-review-wrapped",
                "name": "Year in Review Wrapped",
                "description": "Spotify Wrapped-style year review",
                "genre": "recap",
                "duration_range": (60, 120),
                "required_assets": ["data", "text", "images"],
            },
            {
                "id": "ted-talk-motivation",
                "name": "TED Talk Motivation",
                "description": "TED Talk-style motivational video",
                "genre": "educational",
                "duration_range": (300, 1200),
                "required_assets": ["video", "text", "audio"],
            },
            {
                "id": "youtube-tutorial",
                "name": "YouTube Tutorial",
                "description": "Professional tutorial video format",
                "genre": "educational",
                "duration_range": (300, 1800),
                "required_assets": ["video", "text", "audio"],
            },
            {
                "id": "ecommerce-story-pack",
                "name": "E-commerce Story Pack",
                "description": "Instagram story-style product showcase",
                "genre": "ecommerce",
                "duration_range": (15, 30),
                "required_assets": ["product_images", "text"],
            },
            {
                "id": "narrated-video-starter",
                "name": "Narrated Video Starter",
                "description": "Simple narrated video template",
                "genre": "educational",
                "duration_range": (60, 300),
                "required_assets": ["images", "audio", "text"],
            },
            {
                "id": "countdown-event-promo",
                "name": "Countdown Event Promo",
                "description": "Event countdown promotional video",
                "genre": "promotional",
                "duration_range": (15, 60),
                "required_assets": ["text", "images", "date"],
            },
        ]

        # Filter to only templates that exist in the templates directory
        if self.templates_dir.exists():
            existing_files = {f.stem for f in self.templates_dir.glob("*.tsx")}
            templates = [t for t in templates if t["id"] in existing_files]
            logger.info(f"Found {len(templates)} templates in {self.templates_dir}")
        else:
            logger.warning(f"Templates directory not found: {self.templates_dir}")

        return templates

    def get_template_info(self, template_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific template.

        Args:
            template_id: Template identifier

        Returns:
            Dictionary with detailed template information

        Raises:
            ValueError: If template not found
        """
        templates = self.list_templates()
        for template in templates:
            if template["id"] == template_id:
                # Add file path information
                template_file = self.templates_dir / f"{template_id}.tsx"
                template["file_path"] = str(template_file)
                template["exists"] = template_file.exists()
                return template

        raise ValueError(f"Template not found: {template_id}")

    def prepare_assets(self, assets: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and prepare assets for rendering.

        Args:
            assets: Dictionary of assets (images, audio, video, etc.)

        Returns:
            Dictionary of validated and prepared assets
        """
        prepared = {}

        # Validate image assets
        if "images" in assets:
            prepared["images"] = []
            for img in assets["images"]:
                if isinstance(img, (str, Path)):
                    img_path = Path(img)
                    if img_path.exists():
                        prepared["images"].append(str(img_path.absolute()))
                        logger.debug(f"Validated image: {img_path}")
                    else:
                        logger.warning(f"Image not found: {img_path}")
                else:
                    prepared["images"].append(img)

        # Validate audio assets
        if "audio" in assets:
            audio_path = Path(assets["audio"])
            if audio_path.exists():
                prepared["audio"] = str(audio_path.absolute())
                logger.debug(f"Validated audio: {audio_path}")
            else:
                logger.warning(f"Audio not found: {audio_path}")
                prepared["audio"] = assets["audio"]

        # Pass through other assets
        for key, value in assets.items():
            if key not in ["images", "audio"]:
                prepared[key] = value

        logger.info(f"Prepared {len(prepared)} asset types")
        return prepared

    def render_template(
        self, template_id: str, data: Dict[str, Any], output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Render a video using a Remotion template.

        Args:
            template_id: Template identifier
            data: Data dictionary containing text, images, audio, colors, fonts, etc.
            output_path: Optional output path for rendered video

        Returns:
            Dictionary with render results:
                - output_path: Path to rendered video
                - duration: Video duration in seconds
                - format: Video format (mp4)
                - template_id: Template used

        Raises:
            ValueError: If template not found
            RuntimeError: If Node.js/Remotion not available or render fails
        """
        # Validate template exists
        template_info = self.get_template_info(template_id)

        if not self.node_available:
            raise RuntimeError("Node.js not available - cannot render video")

        # Prepare output path
        if output_path is None:
            output_path = Path(tempfile.mkdtemp()) / f"{template_id}_output.mp4"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare props JSON
        props_json = json.dumps(data)

        # Build Remotion CLI command
        cmd = [
            "npx",
            "remotion",
            "render",
            template_id,
            str(output_path),
            f"--props={props_json}",
        ]

        logger.info(f"Rendering template '{template_id}' to {output_path}")
        logger.debug(f"Render command: {' '.join(cmd)}")

        try:
            # Execute render command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=self.templates_dir.parent,
            )

            if result.returncode != 0:
                logger.error(f"Render failed: {result.stderr}")
                raise RuntimeError(f"Remotion render failed: {result.stderr}")

            logger.info(f"Render completed successfully: {output_path}")

            # Estimate duration from template info
            duration_range = template_info.get("duration_range", (30, 60))
            estimated_duration = sum(duration_range) / 2

            return {
                "output_path": str(output_path),
                "duration": estimated_duration,
                "format": "mp4",
                "template_id": template_id,
                "success": True,
            }

        except subprocess.TimeoutExpired:
            logger.error("Render timeout after 300 seconds")
            raise RuntimeError("Render timeout - video generation took too long")
        except Exception as e:
            logger.error(f"Render error: {e}")
            raise RuntimeError(f"Render failed: {e}")
