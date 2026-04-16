"""Memory/learning system for persistent content improvement."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_MEMORY_PATH = Path(__file__).parent.parent.parent / "data" / "memory.json"


class MemorySystem:
    """Persistent learning system that stores content performance lessons."""

    def __init__(self, memory_path: Optional[str] = None):
        self._path = Path(memory_path) if memory_path else DEFAULT_MEMORY_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lessons: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        return []

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._lessons, indent=2, default=str))

    def save_lesson(self, hook_type: str, result: Dict[str, Any]) -> None:
        """Save a performance lesson.

        Args:
            hook_type: Hook type that was used.
            result: Dict with views, success, platform, etc.
        """
        lesson = {
            "hook_type": hook_type,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._lessons.append(lesson)
        self._save()
        logger.info(f"Lesson saved: {hook_type} → {result.get('views', 0)} views")

    def get_lessons(self, hook_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve learned lessons.

        Args:
            hook_type: Filter by hook type (None for all).

        Returns:
            List of lesson dicts.
        """
        if hook_type:
            return [l for l in self._lessons if l.get("hook_type") == hook_type]
        return list(self._lessons)

    def get_successful_patterns(self) -> List[Dict[str, Any]]:
        """Get lessons from successful content.

        Returns:
            List of lessons where result was successful.
        """
        return [l for l in self._lessons if l.get("result", {}).get("success", False)]

    def evolve_rules(self) -> Dict[str, Any]:
        """Analyze lessons and derive updated rules.

        Returns:
            Dict with evolved rules and patterns.
        """
        success_by_type: Dict[str, int] = {}
        total_by_type: Dict[str, int] = {}

        for lesson in self._lessons:
            hook_type = lesson.get("hook_type", "unknown")
            total_by_type[hook_type] = total_by_type.get(hook_type, 0) + 1
            if lesson.get("result", {}).get("success", False):
                success_by_type[hook_type] = success_by_type.get(hook_type, 0) + 1

        rules = {}
        for hook_type in total_by_type:
            total = total_by_type[hook_type]
            success = success_by_type.get(hook_type, 0)
            rules[hook_type] = {
                "success_rate": round(success / max(total, 1), 2),
                "total_uses": total,
                "recommendation": "increase"
                if success / max(total, 1) > 0.5
                else "decrease",
            }

        logger.info(f"Evolved rules from {len(self._lessons)} lessons")
        return rules

    def clear_old_lessons(self, days: int = 90) -> int:
        """Remove lessons older than N days.

        Args:
            days: Number of days to keep.

        Returns:
            Number of lessons removed.
        """
        cutoff = datetime.utcnow().timestamp() - (days * 86400)
        original_count = len(self._lessons)

        self._lessons = [
            l
            for l in self._lessons
            if datetime.fromisoformat(l.get("timestamp", "2000-01-01")).timestamp()
            >= cutoff
        ]

        removed = original_count - len(self._lessons)
        if removed:
            self._save()
        logger.info(f"Cleared {removed} old lessons (older than {days} days)")
        return removed
