"""Queue manager for post scheduling with JSON persistence."""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from ..logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_QUEUE_PATH = Path(__file__).parent.parent.parent / "data" / "queue.json"


class QueueManager:
    """Manages post queue with JSON file persistence."""

    def __init__(self, queue_path: Optional[str] = None):
        self._path = Path(queue_path) if queue_path else DEFAULT_QUEUE_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._queue: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        """Load queue from disk."""
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load queue: {e}")
        return []

    def _save(self) -> None:
        """Persist queue to disk."""
        self._path.write_text(json.dumps(self._queue, indent=2, default=str))

    def enqueue(self, item: Dict[str, Any]) -> int:
        """Add item to the queue.

        Args:
            item: Post data dict.

        Returns:
            Queue position (0-indexed).
        """
        item["enqueued_at"] = (
            datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        )
        item["status"] = "queued"
        self._queue.append(item)
        self._save()
        logger.info(f"Item enqueued: position {len(self._queue) - 1}")
        return len(self._queue) - 1

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """Get and remove the next item from the queue.

        Returns:
            Next queue item or None if empty.
        """
        if not self._queue:
            return None
        item = self._queue.pop(0)
        self._save()
        logger.info("Item dequeued")
        return item

    def peek(self) -> Optional[Dict[str, Any]]:
        """View next item without removing it.

        Returns:
            Next queue item or None if empty.
        """
        return self._queue[0] if self._queue else None

    def size(self) -> int:
        """Get current queue size."""
        return len(self._queue)

    def clear(self) -> int:
        """Clear all items from the queue.

        Returns:
            Number of items cleared.
        """
        count = len(self._queue)
        self._queue.clear()
        self._save()
        logger.info(f"Queue cleared: {count} items removed")
        return count

    def get_failed(self) -> List[Dict[str, Any]]:
        """Get all failed items from the queue.

        Returns:
            List of failed items.
        """
        return [item for item in self._queue if item.get("status") == "failed"]

    def retry_failed(self) -> int:
        """Reset failed items back to queued status.

        Returns:
            Number of items retried.
        """
        count = 0
        for item in self._queue:
            if item.get("status") == "failed":
                item["status"] = "queued"
                item["retry_count"] = item.get("retry_count", 0) + 1
                count += 1
        if count:
            self._save()
        logger.info(f"Retrying {count} failed items")
        return count
