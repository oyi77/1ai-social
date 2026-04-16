"""Viral hook generator using Larry Playbook proven formula."""

from typing import List
from ..models import Hook
from ..logging_config import get_logger

logger = get_logger(__name__)

HOOK_FORMULAS = {
    "landlord_ai": {
        "template": "My landlord said {problem}, so I showed them what AI thinks about {topic}...",
        "confidence": 0.9,
        "cta": "They couldn't believe the result!",
    },
    "parent_ai": {
        "template": "My mum was skeptical about {topic} until I showed her this...",
        "confidence": 0.85,
        "cta": "Now she uses it every day",
    },
    "roommate_ai": {
        "template": "My roommate said {problem}, so I let AI handle it...",
        "confidence": 0.8,
        "cta": "They haven't complained since",
    },
    "curiosity": {
        "template": "I tried {topic} and the result was not what I expected...",
        "confidence": 0.7,
        "cta": "Wait for the ending...",
    },
    "value": {
        "template": "Here's how I use AI to {benefit} — this saves me {time} every week",
        "confidence": 0.6,
        "cta": "Try this yourself",
    },
    "emotional": {
        "template": "When I realized AI could {action}, everything changed...",
        "confidence": 0.5,
        "cta": "This hits different",
    },
}

NICHE_TOPICS = {
    "AI": ("AI tools", "artificial intelligence", "AI automation"),
    "tech": ("new tech", "latest gadgets", "tech innovation"),
    "design": ("interior design", "home makeover", "design trends"),
    "cooking": ("recipe creation", "meal planning", "cooking hacks"),
    "fitness": ("workout planning", "fitness goals", "exercise routines"),
    "business": ("business automation", "revenue growth", "startup tools"),
    "education": ("learning methods", "study hacks", "online courses"),
    "marketing": ("content creation", "social media growth", "brand building"),
}


class HookGenerator:
    """Generates viral hooks using the Larry Playbook proven formula.

    Formula: [Person's problem] + [Doubt/Conflict]
    → "Showed them AI result" → They changed their mind
    """

    def generate_viral_hooks(self, niche: str, count: int = 5) -> List[Hook]:
        """Generate viral hooks for a given niche.

        Args:
            niche: Content niche/topic area.
            count: Number of hooks to generate.

        Returns:
            List of Hook objects sorted by confidence.
        """
        topics = NICHE_TOPICS.get(
            niche.lower(), (niche, f"cool {niche}", f"best {niche}")
        )
        hooks: List[Hook] = []

        formula_items = list(HOOK_FORMULAS.items())
        for i in range(min(count, len(formula_items))):
            hook_type, formula = formula_items[i % len(formula_items)]
            topic = topics[i % len(topics)]

            text = formula["template"].format(
                problem=f"I couldn't {topic[0]}",
                topic=topic[1],
                benefit=f"master {topic[1]}",
                time="5 hours",
                action=f"revolutionize {topic[1]}",
            )
            text += f" {formula['cta']}"

            hooks.append(
                Hook(
                    text=text,
                    confidence=formula["confidence"],
                    type=hook_type,
                )
            )

        logger.info(f"Generated {len(hooks)} hooks for niche '{niche}'")
        return self.rank_hooks_by_confidence(hooks)

    def rank_hooks_by_confidence(self, hooks: List[Hook]) -> List[Hook]:
        """Sort hooks by confidence score (highest first).

        Args:
            hooks: List of Hook objects.

        Returns:
            Sorted list of hooks.
        """
        return sorted(hooks, key=lambda h: h.confidence, reverse=True)

    def select_winner(self, hooks: List[Hook]) -> Hook:
        """Select the single best hook.

        Args:
            hooks: List of Hook objects.

        Returns:
            The hook with highest confidence.

        Raises:
            ValueError: If hooks list is empty.
        """
        if not hooks:
            raise ValueError("No hooks provided")
        ranked = self.rank_hooks_by_confidence(hooks)
        logger.info(
            f"Selected winner: {ranked[0].type} (confidence: {ranked[0].confidence})"
        )
        return ranked[0]
