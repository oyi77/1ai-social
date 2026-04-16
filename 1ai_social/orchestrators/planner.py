from datetime import datetime, timedelta
from typing import Dict, List
from ..models import Platform
from ..logging_config import get_logger

logger = get_logger(__name__)


class ContentPlanner:
    """Generates content calendars and optimal posting timing strategies."""

    def __init__(self):
        """Initialize ContentPlanner."""
        pass

    def generate_calendar(self, niche: str, days: int = 7) -> List[Dict]:
        """
        Generate a content calendar for the specified niche and duration.

        Args:
            niche: Content niche/topic
            days: Number of days to plan for (default: 7)

        Returns:
            List of dicts with date, platforms, content_type, optimal_times, hooks_suggestions
        """
        calendar = []
        start_date = datetime.now()

        # Content type distribution: 40% video, 30% slideshow, 20% image, 10% text
        content_types = ["video"] * 4 + ["slideshow"] * 3 + ["image"] * 2 + ["text"]

        # Platform rotation - max 3 per day
        all_platforms = [
            Platform.TIKTOK,
            Platform.INSTAGRAM,
            Platform.X,
            Platform.LINKEDIN,
            Platform.FACEBOOK,
        ]

        for day_idx in range(days):
            current_date = start_date + timedelta(days=day_idx)
            date_str = current_date.strftime("%Y-%m-%d")

            # Rotate content type
            content_type = content_types[day_idx % len(content_types)]

            # Select 2-3 platforms for this day
            num_platforms = 2 if day_idx % 3 == 0 else 3
            platforms = all_platforms[
                day_idx % len(all_platforms) : day_idx % len(all_platforms)
                + num_platforms
            ]
            if len(platforms) < num_platforms:
                platforms.extend(all_platforms[: num_platforms - len(platforms)])
            platforms = platforms[:3]  # Ensure max 3

            # Generate optimal times for selected platforms
            optimal_times = {}
            for platform in platforms:
                optimal_times[platform.value] = self._get_optimal_hour(platform)

            # Generate hook suggestions based on larry-playbook formula
            hooks = self._generate_hooks(niche, content_type)

            calendar.append(
                {
                    "date": date_str,
                    "platforms": [p.value for p in platforms],
                    "content_type": content_type,
                    "optimal_times": optimal_times,
                    "hooks_suggestions": hooks,
                }
            )

        return calendar

    def suggest_timing(self, platform: str) -> Dict:
        """
        Get optimal posting timing for a specific platform.

        Args:
            platform: Platform name (e.g., "tiktok", "instagram")

        Returns:
            Dict with best_hours, best_days, avoid_hours
        """
        timing_map = {
            "tiktok": {
                "best_hours": [19, 20, 21],
                "best_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "avoid_hours": [0, 1, 2, 3, 4, 5],
            },
            "instagram": {
                "best_hours": [11, 12, 13, 19, 20, 21],
                "best_days": ["tuesday", "wednesday", "thursday", "friday"],
                "avoid_hours": [0, 1, 2, 3, 4, 5],
            },
            "x": {
                "best_hours": [8, 9, 10, 12, 13],
                "best_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "avoid_hours": [22, 23, 0, 1, 2, 3, 4, 5],
            },
            "linkedin": {
                "best_hours": [8, 9, 10],
                "best_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "avoid_hours": [18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5],
            },
            "facebook": {
                "best_hours": [13, 14, 15],
                "best_days": ["tuesday", "wednesday", "thursday", "friday"],
                "avoid_hours": [0, 1, 2, 3, 4, 5],
            },
        }

        platform_lower = platform.lower()
        return timing_map.get(
            platform_lower,
            {
                "best_hours": [12],
                "best_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "avoid_hours": [0, 1, 2, 3, 4, 5],
            },
        )

    def _get_optimal_hour(self, platform: Platform) -> int:
        """Get a single optimal hour for a platform."""
        timing = self.suggest_timing(platform.value)
        return timing["best_hours"][0]

    def _generate_hooks(self, niche: str, content_type: str) -> List[str]:
        """
        Generate hook suggestions based on larry-playbook formula.

        Hook patterns:
        - Pattern 1: Curiosity gap
        - Pattern 2: Controversy/bold claim
        - Pattern 3: Relatable problem
        - Pattern 4: Trend/FOMO
        """
        hooks = [
            f"Most {niche} creators don't know this...",
            f"This {niche} hack changed everything",
            f"Why {niche} is harder than you think",
            f"The {niche} secret nobody talks about",
            f"{niche} in 2026 is completely different",
        ]

        return hooks[:3]
