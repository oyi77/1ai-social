"""Humanizer client for polishing AI-generated captions to sound natural."""

import re
from typing import List, Dict
import requests

from .base import BaseClient
from ..models import Platform
from ..config import Config
from ..logging_config import get_logger

logger = get_logger(__name__)


class HumanizerClient(BaseClient):
    """Client for humanizing AI-generated captions with platform-specific tone adaptation."""

    # AI writing patterns to detect
    AI_PATTERNS = {
        "significance_inflation": [
            r"\b(crucial|vital|essential|critical|paramount|pivotal)\b",
            r"\b(game-changer|revolutionary|transformative|groundbreaking)\b",
        ],
        "copula_avoidance": [
            r"\b(serves as|functions as|acts as|represents)\b",
            r"\b(stands as|emerges as|proves to be)\b",
        ],
        "formulaic_challenges": [
            r"\b(navigating|landscape|journey|realm|sphere)\b",
            r"\b(delve into|dive into|explore the nuances)\b",
        ],
        "ai_vocabulary": [
            r"\b(utilize|leverage|facilitate|optimize|enhance)\b",
            r"\b(robust|comprehensive|holistic|multifaceted)\b",
            r"\b(it's important to note|it's worth noting)\b",
        ],
    }

    # Platform-specific tone guidelines
    PLATFORM_TONES = {
        Platform.TIKTOK: {
            "style": "casual, slang-friendly, emoji-heavy, short sentences",
            "max_length": 150,
            "emoji_density": "high",
        },
        Platform.INSTAGRAM: {
            "style": "aesthetic, aspirational, storytelling, emoji-moderate",
            "max_length": 2200,
            "emoji_density": "medium",
        },
        Platform.X: {
            "style": "concise, witty, hashtag-heavy, punchy",
            "max_length": 280,
            "emoji_density": "low",
        },
        Platform.LINKEDIN: {
            "style": "professional, value-driven, thought leadership",
            "max_length": 3000,
            "emoji_density": "minimal",
        },
        Platform.FACEBOOK: {
            "style": "friendly, community-oriented, conversational",
            "max_length": 63206,
            "emoji_density": "low",
        },
    }

    # Hashtag optimization rules
    HASHTAG_RULES = {
        Platform.TIKTOK: {"min": 3, "max": 5, "strategy": "trending + niche mix"},
        Platform.INSTAGRAM: {"min": 20, "max": 30, "strategy": "mixed sizes"},
        Platform.X: {"min": 1, "max": 3, "strategy": "concise and relevant"},
        Platform.LINKEDIN: {"min": 3, "max": 5, "strategy": "professional keywords"},
        Platform.FACEBOOK: {"min": 0, "max": 2, "strategy": "minimal usage"},
    }

    def __init__(self, config: Config):
        """Initialize the Humanizer client.

        Args:
            config: Configuration instance with Groq API key.
        """
        self.config = config
        self.groq_api_key = config.get("groq_api_key")
        self.groq_base_url = "https://api.groq.com/openai/v1/chat/completions"
        self._connected = False

    def connect(self) -> None:
        """Establish connection (initialize client)."""
        if not self.groq_api_key:
            logger.warning(
                "Groq API key not configured, will use fallback humanization"
            )
        self._connected = True
        logger.info("HumanizerClient connected")

    def disconnect(self) -> None:
        """Close connection (cleanup)."""
        self._connected = False
        logger.info("HumanizerClient disconnected")

    def health_check(self) -> bool:
        """Check if the client is healthy.

        Returns:
            bool: True if Groq API key is configured, False otherwise.
        """
        is_healthy = bool(self.groq_api_key)
        logger.debug(f"HumanizerClient health check: {is_healthy}")
        return is_healthy

    def detect_ai_patterns(self, text: str) -> List[str]:
        """Detect AI writing patterns in text.

        Args:
            text: Text to analyze.

        Returns:
            List of detected pattern types.
        """
        detected = []
        text_lower = text.lower()

        for pattern_type, patterns in self.AI_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    if pattern_type not in detected:
                        detected.append(pattern_type)
                    break

        logger.debug(f"Detected AI patterns: {detected}")
        return detected

    def humanize(self, text: str, platform: Platform) -> str:
        """Humanize AI-generated text with platform-specific tone.

        Args:
            text: Text to humanize.
            platform: Target platform for tone adaptation.

        Returns:
            Humanized text string.
        """
        logger.info(f"Humanizing text for platform: {platform.value}")

        # Detect AI patterns
        ai_patterns = self.detect_ai_patterns(text)
        if ai_patterns:
            logger.debug(f"Found AI patterns to fix: {ai_patterns}")

        # Get platform tone guidelines
        tone_guide = self.PLATFORM_TONES.get(
            platform, self.PLATFORM_TONES[Platform.INSTAGRAM]
        )

        # Try LLM-based humanization first
        if self.groq_api_key:
            try:
                humanized = self._humanize_with_llm(
                    text, platform, tone_guide, ai_patterns
                )
                logger.info("Successfully humanized text with LLM")
                return humanized
            except Exception as e:
                logger.warning(
                    f"LLM humanization failed: {e}, falling back to template-based"
                )

        # Fallback to template-based humanization
        humanized = self._humanize_with_templates(text, platform, tone_guide)
        logger.info("Humanized text with template-based approach")
        return humanized

    def _humanize_with_llm(
        self, text: str, platform: Platform, tone_guide: Dict, ai_patterns: List[str]
    ) -> str:
        """Humanize text using Groq LLM API.

        Args:
            text: Text to humanize.
            platform: Target platform.
            tone_guide: Platform tone guidelines.
            ai_patterns: Detected AI patterns.

        Returns:
            Humanized text.
        """
        prompt = self._build_humanization_prompt(
            text, platform, tone_guide, ai_patterns
        )

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert social media copywriter who makes AI-generated text sound natural and human.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 1024,
        }

        response = requests.post(
            self.groq_base_url,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        humanized_text = result["choices"][0]["message"]["content"].strip()

        return humanized_text

    def _build_humanization_prompt(
        self, text: str, platform: Platform, tone_guide: Dict, ai_patterns: List[str]
    ) -> str:
        """Build prompt for LLM humanization.

        Args:
            text: Original text.
            platform: Target platform.
            tone_guide: Platform tone guidelines.
            ai_patterns: Detected AI patterns.

        Returns:
            Prompt string.
        """
        patterns_str = ", ".join(ai_patterns) if ai_patterns else "none detected"

        prompt = f"""Rewrite this social media caption to sound natural and human, not AI-generated.

Platform: {platform.value.upper()}
Tone: {tone_guide["style"]}
Max length: {tone_guide["max_length"]} characters

Detected AI patterns to fix: {patterns_str}

Original caption:
{text}

Instructions:
- Remove AI writing patterns (corporate jargon, formulaic phrases, significance inflation)
- Use natural, conversational language
- Match the platform's tone and style
- Keep it authentic and relatable
- Preserve the core message and intent
- Do NOT add hashtags or emojis (those will be added separately)
- Return ONLY the rewritten caption, no explanations

Rewritten caption:"""

        return prompt

    def _humanize_with_templates(
        self, text: str, platform: Platform, tone_guide: Dict
    ) -> str:
        """Fallback template-based humanization.

        Args:
            text: Text to humanize.
            platform: Target platform.
            tone_guide: Platform tone guidelines.

        Returns:
            Humanized text.
        """
        # Remove common AI patterns with simple replacements
        replacements = {
            r"\butilize\b": "use",
            r"\bleverage\b": "use",
            r"\bfacilitate\b": "help",
            r"\boptimize\b": "improve",
            r"\benhance\b": "improve",
            r"\brobust\b": "strong",
            r"\bcomprehensive\b": "complete",
            r"\bit's important to note that\b": "",
            r"\bit's worth noting that\b": "",
            r"\bserves as\b": "is",
            r"\bfunctions as\b": "works as",
            r"\bacts as\b": "is",
            r"\bdelve into\b": "explore",
            r"\bdive into\b": "look at",
            r"\bnavigating the\b": "dealing with",
            r"\blandscape of\b": "world of",
        }

        humanized = text
        for pattern, replacement in replacements.items():
            humanized = re.sub(pattern, replacement, humanized, flags=re.IGNORECASE)

        # Trim to platform max length if needed
        max_length = tone_guide["max_length"]
        if len(humanized) > max_length:
            humanized = humanized[: max_length - 3] + "..."

        return humanized.strip()

    def optimize_hashtags(self, tags: List[str], platform: Platform) -> List[str]:
        """Optimize hashtags for platform-specific best practices.

        Args:
            tags: List of hashtags (with or without # prefix).
            platform: Target platform.

        Returns:
            Optimized list of hashtags.
        """
        rules = self.HASHTAG_RULES.get(platform, self.HASHTAG_RULES[Platform.INSTAGRAM])

        # Normalize hashtags (remove # prefix, lowercase)
        normalized = []
        for tag in tags:
            clean_tag = tag.strip().lstrip("#").lower()
            if clean_tag and clean_tag not in normalized:
                normalized.append(clean_tag)

        # Apply platform-specific limits
        min_count = rules["min"]
        max_count = rules["max"]

        if len(normalized) < min_count:
            logger.warning(
                f"Only {len(normalized)} hashtags provided, {platform.value} recommends {min_count}-{max_count}"
            )
        elif len(normalized) > max_count:
            logger.info(
                f"Trimming hashtags from {len(normalized)} to {max_count} for {platform.value}"
            )
            normalized = normalized[:max_count]

        # Add # prefix back
        optimized = [f"#{tag}" for tag in normalized]

        logger.debug(
            f"Optimized {len(tags)} hashtags to {len(optimized)} for {platform.value}"
        )
        return optimized

    def add_emoji(self, text: str, style: str = "balanced") -> str:
        """Add platform-appropriate emojis to text.

        Args:
            text: Text to add emojis to.
            style: Emoji style - "minimal", "balanced", "heavy".

        Returns:
            Text with emojis added.
        """
        # Simple emoji mapping based on keywords
        emoji_map = {
            r"\b(love|heart|like)\b": "❤️",
            r"\b(fire|hot|amazing)\b": "🔥",
            r"\b(star|best|top)\b": "⭐",
            r"\b(rocket|growth|launch)\b": "🚀",
            r"\b(celebrate|party|win)\b": "🎉",
            r"\b(think|idea|brain)\b": "💡",
            r"\b(money|cash|profit)\b": "💰",
            r"\b(time|clock|schedule)\b": "⏰",
            r"\b(check|done|complete)\b": "✅",
            r"\b(warning|alert|caution)\b": "⚠️",
        }

        emoji_density = {"minimal": 1, "balanced": 2, "heavy": 4}
        max_emojis = emoji_density.get(style, 2)

        result = text
        added_count = 0

        for pattern, emoji in emoji_map.items():
            if added_count >= max_emojis:
                break
            if re.search(pattern, text, re.IGNORECASE):
                # Add emoji at the end of matching sentence
                result = re.sub(
                    f"({pattern}[^.!?]*[.!?])",
                    f"\\1 {emoji}",
                    result,
                    count=1,
                    flags=re.IGNORECASE,
                )
                added_count += 1

        logger.debug(f"Added {added_count} emojis with style '{style}'")
        return result
