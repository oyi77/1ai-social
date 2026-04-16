"""Billing middleware for plan limit enforcement.

Provides decorators to protect API endpoints with plan limits.
"""

from functools import wraps
from typing import Callable, Optional
import logging

from .plans import get_limit_value, check_feature_enabled, is_within_limit

logger = logging.getLogger(__name__)


class PlanLimitExceeded(Exception):
    """Raised when a plan limit is exceeded."""

    def __init__(self, limit_name: str, current: int, limit: int):
        self.limit_name = limit_name
        self.current = current
        self.limit = limit
        super().__init__(f"Plan limit exceeded: {limit_name} ({current}/{limit})")


class FeatureNotEnabled(Exception):
    """Raised when a feature is not enabled for the plan."""

    def __init__(self, feature: str, plan: str):
        self.feature = feature
        self.plan = plan
        super().__init__(f"Feature '{feature}' not enabled for plan '{plan}'")


def require_plan_limit(limit_name: str, get_current_usage: Callable):
    """Decorator to enforce plan limits on API endpoints.

    Args:
        limit_name: Name of the limit to check (e.g., 'posts_per_month')
        get_current_usage: Function that returns current usage count
                          Signature: (tenant_id: str) -> int

    Usage:
        @require_plan_limit('posts_per_month', get_posts_this_month)
        def create_post(tenant_id: str, ...):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract tenant_id from args/kwargs
            tenant_id = kwargs.get("tenant_id") or kwargs.get("_tenant_id")
            if not tenant_id and args:
                tenant_id = args[0] if isinstance(args[0], str) else None

            if not tenant_id:
                raise ValueError("tenant_id required for plan limit check")

            # Get tenant's plan (would come from database in real implementation)
            # For now, assume it's passed or default to starter
            plan_name = kwargs.get("_plan", "starter")

            # Get limit for this plan
            limit = get_limit_value(plan_name, limit_name)

            # Get current usage
            current_usage = get_current_usage(tenant_id)

            # Check if within limit
            if not is_within_limit(current_usage, limit):
                raise PlanLimitExceeded(limit_name, current_usage, limit)

            # Execute function
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_feature(feature_name: str):
    """Decorator to require a feature to be enabled.

    Args:
        feature_name: Name of the feature to check

    Usage:
        @require_feature('ai_content_generation')
        def generate_ai_content(tenant_id: str, ...):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract tenant_id and plan
            tenant_id = kwargs.get("tenant_id") or kwargs.get("_tenant_id")
            plan_name = kwargs.get("_plan", "starter")

            if not tenant_id:
                raise ValueError("tenant_id required for feature check")

            # Check if feature is enabled
            if not check_feature_enabled(plan_name, feature_name):
                raise FeatureNotEnabled(feature_name, plan_name)

            # Execute function
            return func(*args, **kwargs)

        return wrapper

    return decorator
