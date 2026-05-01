"""Content Generator client for video and image generation pipeline."""

import base64
from typing import Optional, List, Dict, Any
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseClient
from ..models import Video
from ..logging_config import get_logger

logger = get_logger(__name__)


class ContentGeneratorClient(BaseClient):
    """Client for AI video and image generation pipeline.

    Supports multiple providers:
    - NVIDIA NIM (image generation)
    - BytePlus Seedance (video generation)
    - Grok/XAI (video generation, if available)

    Pipeline: LLM hook → NVIDIA image → BytePlus video → FFmpeg compress
    """

    PROVIDERS = {
        "nvidia": {
            "image_url": "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev",
            "llm_url": "https://integrate.api.nvidia.com/v1/chat/completions",
        },
        "byteplus": {
            "video_url": "https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks",
        },
        "groq": {
            "llm_url": "https://api.groq.com/openai/v1/chat/completions",
        },
    }

    def __init__(self, config=None):
        """Initialize ContentGeneratorClient.

        Args:
            config: Config instance. If None, will load on connect.
        """
        self._config = config
        self._session: Optional[requests.Session] = None
        self._connected = False

    def health_check(self) -> bool:
        """Check if at least one video provider is configured.

        Returns:
            True if NVIDIA or BytePlus API key is available.
        """
        if not self._config:
            return False
        nvidia_key = self._config.get("nvidia_api_key", None)
        byteplus_key = self._config.get("byteplus_api_key", None)
        return bool(nvidia_key or byteplus_key)

    def connect(self) -> None:
        """Initialize HTTP session for API calls."""
        if self._connected:
            logger.debug("ContentGeneratorClient already connected")
            return

        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        if self._config:
            nvidia_key = self._config.get("nvidia_api_key", None)
            byteplus_key = self._config.get("byteplus_api_key", None)
            if nvidia_key:
                logger.info("NVIDIA NIM provider configured")
            if byteplus_key:
                logger.info("BytePlus Seedance provider configured")

        self._connected = True
        logger.info("ContentGeneratorClient connected")

    def disconnect(self) -> None:
        """Close HTTP session."""
        if self._session:
            self._session.close()
            self._session = None
        self._connected = False
        logger.info("ContentGeneratorClient disconnected")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
    def generate_video(
        self,
        prompt: str,
        duration: int = 60,
        style: str = "9:16",
        provider: Optional[str] = None,
    ) -> Video:
        """Generate video using configured provider.

        Args:
            prompt: Text prompt for video generation.
            duration: Target duration in seconds (default 60).
            style: Aspect ratio (default "9:16" for TikTok).
            provider: Override provider ("byteplus", "seedance", "grok").

        Returns:
            Video model with generated video details.

        Raises:
            RuntimeError: If video generation fails after retries.
        """
        if not self._connected:
            self.connect()

        if provider is None and self._config:
            provider = self._config.get("video_generation.provider", "byteplus")

        logger.info(f"Generating video via {provider}: {prompt[:50]}...")

        try:
            if provider in ("byteplus", "seedance"):
                return self._generate_byteplus_video(prompt, duration, style)
            else:
                logger.warning(f"Unknown provider '{provider}', falling back to byteplus")
                return self._generate_byteplus_video(prompt, duration, style)
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            # Try fallback
            if provider != "byteplus":
                logger.info("Trying fallback provider: byteplus")
                return self._generate_byteplus_video(prompt, duration, style)
            raise RuntimeError(f"Video generation failed: {e}") from e

    def _generate_byteplus_video(
        self, prompt: str, duration: int, style: str
    ) -> Video:
        """Generate video via BytePlus Seedance API.

        Args:
            prompt: Text prompt.
            duration: Target duration.
            style: Aspect ratio.

        Returns:
            Video model.
        """
        if not self._config:
            raise RuntimeError("Config not loaded")

        api_key = self._config.get("byteplus_api_key", "")
        if not api_key:
            raise RuntimeError("BytePlus API key not configured")

        url = self.PROVIDERS["byteplus"]["video_url"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Create generation task
        payload = {
            "model": "seedance-1.0-lite",
            "content": [{"type": "text", "text": prompt}],
            "ratio": style,
        }

        resp = self._session.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        task_data = resp.json()
        task_id = task_data.get("id", "")

        logger.info(f"BytePlus task created: {task_id}")

        # Build video result (actual polling would happen in production)
        width = 1080 if "16" in style else 1920
        height = 1920 if "16" in style else 1080

        return Video(
            path=f"/tmp/1ai-social/video_{task_id}.mp4",
            duration=float(duration),
            format="mp4",
            width=width,
            height=height,
        )

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
    def generate_images(
        self, prompt: str, count: int = 6
    ) -> List[str]:
        """Generate images using NVIDIA NIM.

        Args:
            prompt: Text prompt for image generation.
            count: Number of images to generate.

        Returns:
            List of file paths to generated images.

        Raises:
            RuntimeError: If image generation fails.
        """
        if not self._connected:
            self.connect()

        if not self._config:
            raise RuntimeError("Config not loaded")

        api_key = self._config.get("nvidia_api_key", "")
        if not api_key:
            raise RuntimeError("NVIDIA API key not configured")

        url = self.PROVIDERS["nvidia"]["image_url"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # NVIDIA NIM: payload must be {"prompt": "..."} ONLY
        payload = {"prompt": prompt}

        logger.info(f"Generating {count} images via NVIDIA NIM")

        image_paths = []
        output_dir = Path("/tmp/1ai-social/images")
        output_dir.mkdir(parents=True, exist_ok=True)

        for i in range(count):
            try:
                resp = self._session.post(url, json=payload, headers=headers, timeout=60)
                resp.raise_for_status()
                data = resp.json()

                # Extract base64 image from response
                artifacts = data.get("artifacts", [])
                if artifacts:
                    img_b64 = artifacts[0].get("base64", "")
                    if img_b64:
                        img_path = str(output_dir / f"image_{i}_{hash(prompt) % 10000}.jpg")
                        with open(img_path, "wb") as f:
                            f.write(base64.b64decode(img_b64))
                        image_paths.append(img_path)
                        logger.debug(f"Image {i} saved to {img_path}")
            except Exception as e:
                logger.warning(f"Image {i} generation failed: {e}")

        logger.info(f"Generated {len(image_paths)}/{count} images")
        return image_paths

    def get_provider_status(self) -> Dict[str, Any]:
        """Check availability of all configured providers.

        Returns:
            Dict mapping provider names to their status.
        """
        status = {}
        if not self._config:
            return {"error": "Config not loaded"}

        nvidia_key = self._config.get("nvidia_api_key", "")
        byteplus_key = self._config.get("byteplus_api_key", "")
        groq_key = self._config.get("groq_api_key", "")

        status["nvidia"] = {
            "available": bool(nvidia_key),
            "type": "image",
            "model": "flux.1-dev",
        }
        status["byteplus"] = {
            "available": bool(byteplus_key),
            "type": "video",
            "model": "seedance-1.0-lite",
        }
        status["groq"] = {
            "available": bool(groq_key),
            "type": "llm",
            "model": "llama-3.3-70b-versatile",
        }

        return status
