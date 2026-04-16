"""Subscription plans configuration and limit enforcement.

Defines subscription tiers with feature flags and usage limits.
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# Plan definitions
PLANS = {
    "starter": {
        "name": "Starter",
        "price": 49,
        "currency": "USD",
        "interval": "month",
        "limits": {
            "posts_per_month": 500,
            "platforms": 3,
            "scheduled_posts": 50,
            "team_members": 1,
            "analytics_retention_days": 30,
            "api_calls_per_day": 1000,
        },
        "features": [
            "basic_analytics",
            "scheduling",
            "content_calendar",
        ],
    },
    "pro": {
        "name": "Pro",
        "price": 99,
        "currency": "USD",
        "interval": "month",
        "limits": {
            "posts_per_month": 2000,
            "platforms": 10,
            "scheduled_posts": 200,
            "team_members": 5,
            "analytics_retention_days": 90,
            "api_calls_per_day": 10000,
        },
        "features": [
            "basic_analytics",
            "advanced_analytics",
            "scheduling",
            "content_calendar",
            "ai_content_generation",
            "bulk_scheduling",
            "custom_branding",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": None,  # Custom pricing
        "currency": "USD",
        "interval": "month",
        "limits": {
            "posts_per_month": None,  # Unlimited
            "platforms": None,  # Unlimited
            "scheduled_posts": None,  # Unlimited
            "team_members": None,  # Unlimited
            "analytics_retention_days": 365,
            "api_calls_per_day": None,  # Unlimited
        },
        "features": [
            "all",  # All features enabled
        ],
    },
}


def get_plan_config(plan_name: str) -> Optional[Dict[str, Any]]:
    """Get plan configuration by name.

    Args:
        plan_name: Plan name (starter, pro, enterprise)

    Returns:
        Plan configuration dict or None if not found
    """
    return PLANS.get(plan_name.lower())


def get_plan_limits(plan_name: str) -> Dict[str, Optional[int]]:
    """Get usage limits for a plan.

    Args:
        plan_name: Plan name

    Returns:
        Dict of limit_name -> limit_value (None = unlimited)
    """
    plan = get_plan_config(plan_name)
    if not plan:
        logger.warning(f"Unknown plan: {plan_name}, using starter limits")
        return PLANS["starter"]["limits"]

    return plan["limits"]


def check_feature_enabled(plan_name: str, feature: str) -> bool:
    """Check if a feature is enabled for a plan.

    Args:
        plan_name: Plan name
        feature: Feature name to check

    Returns:
        True if feature is enabled, False otherwise
    """
    plan = get_plan_config(plan_name)
    if not plan:
        return False

    features = plan["features"]

    # Enterprise has all features
    if "all" in features:
        return True

    return feature in features


def get_limit_value(plan_name: str, limit_name: str) -> Optional[int]:
    """Get a specific limit value for a plan.

    Args:
        plan_name: Plan name
        limit_name: Limit name (e.g., 'posts_per_month')

    Returns:
        Limit value (None = unlimited)
    """
    limits = get_plan_limits(plan_name)
    return limits.get(limit_name)


def is_within_limit(current_usage: int, limit: Optional[int]) -> bool:
    """Check if current usage is within limit.

    Args:
        current_usage: Current usage count
        limit: Limit value (None = unlimited)

    Returns:
        True if within limit, False if exceeded
    """
    if limit is None:
        return True  # Unlimited

    return current_usage < limit


def compare_plans(current_plan: str, target_plan: str) -> Dict[str, Any]:
    """Compare two plans for upgrade/downgrade analysis.

    Args:
        current_plan: Current plan name
        target_plan: Target plan name

    Returns:
        Dict with comparison details
    """
    current = get_plan_config(current_plan)
    target = get_plan_config(target_plan)

    if not current or not target:
        return {"error": "Invalid plan names"}

    # Determine if upgrade or downgrade
    plan_order = ["starter", "pro", "enterprise"]
    current_idx = plan_order.index(current_plan.lower())
    target_idx = plan_order.index(target_plan.lower())

    is_upgrade = target_idx > current_idx

    # Compare limits
    limit_changes = {}
    for limit_name in current["limits"]:
        current_val = current["limits"][limit_name]
        target_val = target["limits"][limit_name]

        if current_val != target_val:
            limit_changes[limit_name] = {
                "from": current_val,
                "to": target_val,
                "change": "increase"
                if (
                    target_val is None
                    or (current_val is not None and target_val > current_val)
                )
                else "decrease",
            }

    # Compare features
    current_features = set(current["features"])
    target_features = set(target["features"])

    if "all" in target_features:
        added_features = ["all_features"]
        removed_features = []
    elif "all" in current_features:
        added_features = []
        removed_features = ["all_features"]
    else:
        added_features = list(target_features - current_features)
        removed_features = list(current_features - target_features)

    return {
        "is_upgrade": is_upgrade,
        "price_change": {
            "from": current["price"],
            "to": target["price"],
        },
        "limit_changes": limit_changes,
        "added_features": added_features,
        "removed_features": removed_features,
    }


def get_all_plans() -> List[Dict[str, Any]]:
    """Get all available plans.

    Returns:
        List of plan configurations
    """
    return [{**config, "id": plan_id} for plan_id, config in PLANS.items()]
