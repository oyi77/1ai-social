"""Billing dashboard API endpoints.

Provides comprehensive billing information including current plan, usage metrics,
invoices, and payment methods.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from .plans import get_plan_config, get_plan_limits
from .usage import get_current_month_usage, get_usage_summary

logger = logging.getLogger(__name__)


def get_billing_overview(
    session: Session, tenant_id: str, plan_name: str
) -> Dict[str, Any]:
    """Get current billing overview with plan and usage summary.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        plan_name: Current subscription plan name

    Returns:
        Dict with plan info, usage, limits, and next billing date
    """
    plan_config = get_plan_config(plan_name)
    if not plan_config:
        logger.warning(f"Unknown plan: {plan_name}")
        return {"error": "Invalid plan"}

    usage_summary = get_usage_summary(session, tenant_id, plan_name)

    # Calculate next billing date (1st of next month)
    now = datetime.utcnow()
    if now.month == 12:
        next_billing = datetime(now.year + 1, 1, 1)
    else:
        next_billing = datetime(now.year, now.month + 1, 1)

    days_until_billing = (next_billing - now).days

    return {
        "tenant_id": tenant_id,
        "current_plan": {
            "id": plan_name,
            "name": plan_config["name"],
            "price": plan_config["price"],
            "currency": plan_config["currency"],
            "interval": plan_config["interval"],
            "features": plan_config["features"],
        },
        "usage": usage_summary["usage"],
        "limits": usage_summary["limits"],
        "usage_percentages": usage_summary["usage_percentages"],
        "has_overage": usage_summary["has_overage"],
        "overages": usage_summary["overages"],
        "warnings": usage_summary["warnings"],
        "billing_cycle": {
            "current_period_start": datetime(now.year, now.month, 1).isoformat(),
            "current_period_end": next_billing.isoformat(),
            "days_until_next_billing": days_until_billing,
        },
    }


def get_usage_details(
    session: Session,
    tenant_id: str,
    plan_name: str,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Get detailed usage for a specific billing period.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        plan_name: Subscription plan name
        period_start: Start of period (defaults to current month start)
        period_end: End of period (defaults to current month end)

    Returns:
        Dict with detailed usage breakdown and progress bars
    """
    now = datetime.utcnow()

    if period_start is None:
        period_start = datetime(now.year, now.month, 1)

    if period_end is None:
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1)
        else:
            period_end = datetime(now.year, now.month + 1, 1)

    usage = get_current_month_usage(session, tenant_id)
    limits = get_plan_limits(plan_name)

    # Build usage details with progress bars
    usage_details = {
        "tenant_id": tenant_id,
        "plan": plan_name,
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "metrics": {},
    }

    # Posts per month
    if limits.get("posts_per_month") is not None:
        posts_used = usage.get("posts_published", 0)
        posts_limit = limits["posts_per_month"]
        posts_pct = (posts_used / posts_limit * 100) if posts_limit > 0 else 0
        usage_details["metrics"]["posts_per_month"] = {
            "used": posts_used,
            "limit": posts_limit,
            "percentage": round(posts_pct, 2),
            "remaining": max(0, posts_limit - posts_used),
            "progress_bar": _build_progress_bar(posts_pct),
        }
    else:
        posts_used = usage.get("posts_published", 0)
        usage_details["metrics"]["posts_per_month"] = {
            "used": posts_used,
            "limit": None,
            "percentage": 0,
            "remaining": None,
            "progress_bar": "unlimited",
        }

    # API calls per day
    if limits.get("api_calls_per_day") is not None:
        day_start = datetime(now.year, now.month, now.day)
        day_end = day_start + timedelta(days=1)
        from .usage import get_usage

        daily_usage = get_usage(session, tenant_id, day_start, day_end)
        api_calls_used = daily_usage.get("api_calls", 0)
        api_calls_limit = limits["api_calls_per_day"]
        api_calls_pct = (
            (api_calls_used / api_calls_limit * 100) if api_calls_limit > 0 else 0
        )
        usage_details["metrics"]["api_calls_per_day"] = {
            "used": api_calls_used,
            "limit": api_calls_limit,
            "percentage": round(api_calls_pct, 2),
            "remaining": max(0, api_calls_limit - api_calls_used),
            "progress_bar": _build_progress_bar(api_calls_pct),
        }
    else:
        day_start = datetime(now.year, now.month, now.day)
        day_end = day_start + timedelta(days=1)
        from .usage import get_usage

        daily_usage = get_usage(session, tenant_id, day_start, day_end)
        api_calls_used = daily_usage.get("api_calls", 0)
        usage_details["metrics"]["api_calls_per_day"] = {
            "used": api_calls_used,
            "limit": None,
            "percentage": 0,
            "remaining": None,
            "progress_bar": "unlimited",
        }

    # Platforms/connected accounts
    if limits.get("platforms") is not None:
        accounts_used = usage.get("connected_accounts", 0)
        accounts_limit = limits["platforms"]
        accounts_pct = (
            (accounts_used / accounts_limit * 100) if accounts_limit > 0 else 0
        )
        usage_details["metrics"]["platforms"] = {
            "used": accounts_used,
            "limit": accounts_limit,
            "percentage": round(accounts_pct, 2),
            "remaining": max(0, accounts_limit - accounts_used),
            "progress_bar": _build_progress_bar(accounts_pct),
        }
    else:
        accounts_used = usage.get("connected_accounts", 0)
        usage_details["metrics"]["platforms"] = {
            "used": accounts_used,
            "limit": None,
            "percentage": 0,
            "remaining": None,
            "progress_bar": "unlimited",
        }

    return usage_details


def get_invoices(
    session: Session,
    tenant_id: str,
    limit: int = 12,
) -> Dict[str, Any]:
    """Get list of past invoices for a tenant.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        limit: Maximum number of invoices to return (default: 12)

    Returns:
        Dict with invoice list and summary
    """
    # Mock invoice data - in production, would query from invoices table
    invoices = [
        {
            "id": f"inv_{tenant_id}_202604",
            "date": "2026-04-01",
            "amount": 99.00,
            "currency": "USD",
            "status": "paid",
            "period_start": "2026-04-01",
            "period_end": "2026-05-01",
            "description": "Pro Plan - April 2026",
        },
        {
            "id": f"inv_{tenant_id}_202603",
            "date": "2026-03-01",
            "amount": 99.00,
            "currency": "USD",
            "status": "paid",
            "period_start": "2026-03-01",
            "period_end": "2026-04-01",
            "description": "Pro Plan - March 2026",
        },
        {
            "id": f"inv_{tenant_id}_202602",
            "date": "2026-02-01",
            "amount": 99.00,
            "currency": "USD",
            "status": "paid",
            "period_start": "2026-02-01",
            "period_end": "2026-03-01",
            "description": "Pro Plan - February 2026",
        },
    ]

    return {
        "tenant_id": tenant_id,
        "invoices": invoices[:limit],
        "total_count": len(invoices),
        "limit": limit,
    }


def get_payment_methods(session: Session, tenant_id: str) -> Dict[str, Any]:
    """Get payment methods on file for a tenant.

    Args:
        session: Database session
        tenant_id: Tenant identifier

    Returns:
        Dict with payment methods (no sensitive details exposed)
    """
    # Mock payment methods - in production, would query from payment_methods table
    # Never expose full card numbers or sensitive data
    payment_methods = [
        {
            "id": "pm_1234567890",
            "type": "card",
            "brand": "visa",
            "last_four": "4242",
            "exp_month": 12,
            "exp_year": 2026,
            "is_default": True,
        },
        {
            "id": "pm_0987654321",
            "type": "card",
            "brand": "mastercard",
            "last_four": "5555",
            "exp_month": 6,
            "exp_year": 2027,
            "is_default": False,
        },
    ]

    return {
        "tenant_id": tenant_id,
        "payment_methods": payment_methods,
        "default_method_id": "pm_1234567890",
    }


def _build_progress_bar(percentage: float, width: int = 20) -> str:
    """Build a text-based progress bar.

    Args:
        percentage: Usage percentage (0-100)
        width: Width of progress bar in characters

    Returns:
        Text representation of progress bar
    """
    if percentage > 100:
        percentage = 100

    filled = int(width * percentage / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {percentage:.1f}%"
