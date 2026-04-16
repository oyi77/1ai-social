"""Cron-based scheduler for automated content generation and posting."""

import re
import time
import threading
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any
from ..logging_config import get_logger

logger = get_logger(__name__)


class Scheduler:
    """Cron-based job scheduler for content automation."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_tick_minute: int = -1

    def validate_cron(self, expression: str) -> bool:
        """Validate a cron expression format.

        Args:
            expression: Cron expression string (e.g. '0 7 * * *').

        Returns:
            True if valid format.
        """
        parts = expression.strip().split()
        if len(parts) != 5:
            return False

        patterns = [
            r"^(\*|[0-9,\-\/]+)$",
            r"^(\*|[0-9,\-\/]+)$",
            r"^(\*|[0-9,\-\/]+)$",
            r"^(\*|[0-9,\-\/]+)$",
            r"^(\*|[0-9,\-\/]+)$",
        ]

        return all(re.match(p, part) for part, p in zip(parts, patterns))

    def schedule_job(
        self, cron_expression: str, callback: Callable, job_name: str = ""
    ) -> str:
        """Schedule a recurring job.

        Args:
            cron_expression: Cron expression for schedule.
            callback: Function to execute.
            job_name: Optional name for the job.

        Returns:
            Job ID string.

        Raises:
            ValueError: If cron expression is invalid.
        """
        if not self.validate_cron(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")

        job_id = job_name or f"job_{len(self._jobs)}"
        self._jobs[job_id] = {
            "cron": cron_expression,
            "callback": callback,
            "active": True,
        }
        logger.info(f"Job '{job_id}' scheduled: {cron_expression}")
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: Job ID to remove.

        Returns:
            True if job was found and removed.
        """
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Job '{job_id}' removed")
            return True
        return False

    def run_daily(self, callback: Optional[Callable] = None) -> str:
        """Schedule a daily content generation and posting job.

        Args:
            callback: Function to execute daily.

        Returns:
            Job ID.
        """
        return self.schedule_job(
            "0 7 * * *", callback or self._default_daily, "daily_content"
        )

    def run_hourly(self, callback: Optional[Callable] = None) -> str:
        """Schedule an hourly engagement check.

        Args:
            callback: Function to execute hourly.

        Returns:
            Job ID.
        """
        return self.schedule_job(
            "0 * * * *", callback or self._default_hourly, "hourly_engagement"
        )

    def get_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get all scheduled jobs.

        Returns:
            Dict of job_id → job info.
        """
        return dict(self._jobs)

    def _matches_cron(self, expression: str, now: datetime) -> bool:
        """Check if current time matches a cron expression.

        Args:
            expression: Cron expression.
            now: Current datetime.

        Returns:
            True if the cron expression matches the current time.
        """
        parts = expression.strip().split()
        if len(parts) != 5:
            return False

        def matches_field(field: str, value: int) -> bool:
            if field == "*":
                return True
            for part in field.split(","):
                if "/" in part:
                    base, step = part.split("/", 1)
                    base_val = int(base) if base != "*" else 0
                    step_val = int(step)
                    if value >= base_val and (value - base_val) % step_val == 0:
                        return True
                elif "-" in part:
                    start, end = part.split("-", 1)
                    if int(start) <= value <= int(end):
                        return True
                else:
                    if int(part) == value:
                        return True
            return False

        return (
            matches_field(parts[0], now.minute)
            and matches_field(parts[1], now.hour)
            and matches_field(parts[2], now.day)
            and matches_field(parts[3], now.month)
            and matches_field(parts[4], now.weekday())
        )

    def tick(self) -> int:
        """Check and execute any jobs whose cron schedule matches current time.

        Should be called periodically (e.g., every minute).

        Returns:
            Number of jobs executed in this tick.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        current_minute = now.hour * 60 + now.minute

        if current_minute == self._last_tick_minute:
            return 0

        self._last_tick_minute = current_minute
        executed = 0

        for job_id, job in self._jobs.items():
            if not job.get("active", True):
                continue
            if self._matches_cron(job["cron"], now):
                try:
                    logger.info(f"Executing scheduled job: {job_id}")
                    job["callback"]()
                    executed += 1
                except Exception as e:
                    logger.error(f"Job '{job_id}' execution failed: {e}")

        return executed

    def start(self, daemon: bool = True) -> None:
        """Start the scheduler loop in a background thread.

        Args:
            daemon: If True, thread exits when main thread exits.
        """
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True

        def _loop():
            logger.info("Scheduler loop started (60s interval)")
            while self._running:
                self.tick()
                time.sleep(60)
            logger.info("Scheduler loop stopped")

        self._thread = threading.Thread(target=_loop, daemon=daemon)
        self._thread.start()
        logger.info("Scheduler started in background thread")

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Scheduler stopped")

    def _default_daily(self):
        logger.info("Daily content generation triggered")

    def _default_hourly(self):
        logger.info("Hourly engagement check triggered")
