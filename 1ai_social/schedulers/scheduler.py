"""Cron-based scheduler for automated content generation and posting."""

import re
from typing import Callable, Optional, Dict, Any
from ..logging_config import get_logger

logger = get_logger(__name__)


class Scheduler:
    """Cron-based job scheduler for content automation."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}

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
            r"^(\*|[0-9,\-\/]+)$",  # minute (0-59)
            r"^(\*|[0-9,\-\/]+)$",  # hour (0-23)
            r"^(\*|[0-9,\-\/]+)$",  # day of month (1-31)
            r"^(\*|[0-9,\-\/]+)$",  # month (1-12)
            r"^(\*|[0-9,\-\/]+)$",  # day of week (0-6)
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

    def _default_daily(self):
        logger.info("Daily content generation triggered")

    def _default_hourly(self):
        logger.info("Hourly engagement check triggered")
