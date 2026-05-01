"""Billing dashboard API endpoints.

Provides comprehensive billing information including current plan, usage metrics,
invoices, and payment methods.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from .plans import get_plan_config, get_plan_limits
from .usage import get_current_month_usage, get_usage_summary
from .lemonsqueezy import Subscription

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
    subscription = session.query(Subscription).filter_by(tenant_id=tenant_id).first()

    if not subscription:
        return {
            "tenant_id": tenant_id,
            "invoices": [],
            "total_count": 0,
            "limit": limit,
        }

    from .plans import get_plan_config

    plan_config = get_plan_config(subscription.plan)
    plan_price = plan_config.get("price", 0) if plan_config else 0
    plan_name = (
        plan_config.get("name", subscription.plan) if plan_config else subscription.plan
    )

    invoices = []

    if subscription.current_period_start and subscription.current_period_end:
        current_start = subscription.current_period_start

        for i in range(limit):
            period_start = current_start - timedelta(days=30 * i)
            period_end = (
                current_start - timedelta(days=30 * (i - 1))
                if i > 0
                else subscription.current_period_end
            )

            if period_start < subscription.created_at:
                break

            invoice_date = period_start.strftime("%Y-%m-%d")
            invoice_id = f"inv_{tenant_id}_{period_start.strftime('%Y%m')}"

            status = "paid"
            if subscription.status == "past_due" and i == 0:
                status = "past_due"
            elif subscription.status == "cancelled" and i == 0:
                status = "cancelled"

            invoices.append(
                {
                    "id": invoice_id,
                    "date": invoice_date,
                    "amount": plan_price if plan_price else 0,
                    "currency": "USD",
                    "status": status,
                    "period_start": period_start.strftime("%Y-%m-%d"),
                    "period_end": period_end.strftime("%Y-%m-%d"),
                    "description": f"{plan_name} - {period_start.strftime('%B %Y')}",
                }
            )

    return {
        "tenant_id": tenant_id,
        "invoices": invoices,
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
    subscription = session.query(Subscription).filter_by(tenant_id=tenant_id).first()

    payment_methods = []
    default_method_id = None

    if subscription and subscription.lemonsqueezy_customer_id:
        payment_methods.append(
            {
                "id": f"ls_{subscription.lemonsqueezy_customer_id}",
                "type": "lemonsqueezy",
                "provider": "LemonSqueezy",
                "status": subscription.status,
                "is_default": True,
            }
        )
        default_method_id = f"ls_{subscription.lemonsqueezy_customer_id}"

    return {
        "tenant_id": tenant_id,
        "payment_methods": payment_methods,
        "default_method_id": default_method_id,
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
