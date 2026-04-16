"""Confidence score updater based on post performance with persistence."""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from ..logging_config import get_logger

logger = get_logger(__name__)

BASE_CONFIDENCE = {
    "landlord_ai": 0.9,
    "parent_ai": 0.85,
    "roommate_ai": 0.8,
    "curiosity": 0.7,
    "value": 0.6,
    "emotional": 0.5,
}

VIEW_THRESHOLDS = [
    (100000, 0.15),
    (50000, 0.10),
    (10000, 0.05),
    (1000, 0.02),
]

DEFAULT_SCORES_PATH = (
    Path(__file__).parent.parent.parent / "data" / "confidence_scores.json"
)


class ConfidenceUpdater:
    """Updates hook confidence scores based on actual performance data with persistence."""

    def __init__(self, scores_path: str = None):
        self._path = Path(scores_path) if scores_path else DEFAULT_SCORES_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._scores: Dict[str, float] = self._load()

    def _load(self) -> Dict[str, float]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return dict(BASE_CONFIDENCE)

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._scores, indent=2))

    def update_hook_confidence(self, hook_type: str, views: int) -> float:
        """Update confidence for a hook based on view count.

        Args:
            hook_type: Hook type identifier.
            views: Number of views the post received.

        Returns:
            Updated confidence score.
        """
        current = self._scores.get(hook_type, 0.5)
        boost = 0.0
        for threshold, increment in VIEW_THRESHOLDS:
            if views >= threshold:
                boost = increment
                break

        new_score = min(current + boost, 1.0)
        self._scores[hook_type] = new_score
        self._save()
        logger.info(
            f"Confidence updated: {hook_type} {current:.2f} → {new_score:.2f} (views: {views})"
        )
        return new_score

    def get_confidence(self, hook_type: str) -> float:
        """Get current confidence score for a hook type.

        Args:
            hook_type: Hook type identifier.

        Returns:
            Confidence score (0-1).
        """
        return self._scores.get(hook_type, 0.5)

    def get_top_hooks(self, limit: int = 5) -> List[Tuple[str, float]]:
        """Get top performing hooks by confidence.

        Args:
            limit: Max number to return.

        Returns:
            List of (hook_type, confidence) tuples sorted by confidence.
        """
        sorted_hooks = sorted(self._scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_hooks[:limit]

    def decay_old_hooks(self, decay_factor: float = 0.95) -> int:
        """Reduce confidence of hooks that haven't been updated.

        Args:
            decay_factor: Multiplier for decay (0.95 = 5% reduction).

        Returns:
            Number of hooks decayed.
        """
        count = 0
        for hook_type in self._scores:
            if self._scores[hook_type] > BASE_CONFIDENCE.get(hook_type, 0.5):
                self._scores[hook_type] *= decay_factor
                count += 1
        if count:
            self._save()
        logger.info(f"Decayed {count} hooks by factor {decay_factor}")
        return count

    def get_all_scores(self) -> Dict[str, float]:
        """Get all current confidence scores."""
        return dict(self._scores)
