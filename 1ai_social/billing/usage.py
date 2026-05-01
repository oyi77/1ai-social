"""Usage tracking and metering for billing.

Tracks usage events (posts published, API calls, connected accounts) and aggregates
them for billing period calculations and overage detection.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, DateTime, func, and_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

from .plans import get_plan_limits

logger = logging.getLogger(__name__)

Base = declarative_base()

VALID_EVENT_TYPES = {"posts_published", "api_calls", "connected_accounts"}


class UsageEvent(Base):
    """Usage event model for tracking metered usage."""

    __tablename__ = "usage_events"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    event_metadata = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def record_usage(
    session: Session,
    tenant_id: str,
    event_type: str,
    quantity: int = 1,
    metadata: Optional[Dict[str, Any]] = None,
) -> UsageEvent:
    """Record a usage event for billing.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        event_type: Type of event (posts_published, api_calls, connected_accounts)
        quantity: Number of units consumed (default: 1)
        metadata: Optional metadata (must not contain PII)

    Returns:
        Created UsageEvent instance

    Raises:
        ValueError: If event_type is invalid or quantity is non-positive
    """
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(
            f"Invalid event_type: {event_type}. Must be one of {VALID_EVENT_TYPES}"
        )

    if quantity <= 0:
        raise ValueError(f"Quantity must be positive, got: {quantity}")

    session.execute(
        sa.text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant_id},
    )

    event = UsageEvent(
        tenant_id=tenant_id,
        event_type=event_type,
        quantity=quantity,
        event_metadata=metadata,
    )

    session.add(event)
    session.flush()

    result = UsageEvent()
    result.id = event.id
    result.tenant_id = event.tenant_id
    result.event_type = event.event_type
    result.quantity = event.quantity
    result.event_metadata = event.event_metadata
    result.created_at = event.created_at

    session.commit()

    logger.info(
        f"Recorded usage event: tenant={tenant_id}, type={event_type}, quantity={quantity}"
    )

    return result


def get_usage(
    session: Session,
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
) -> Dict[str, int]:
    """Get aggregated usage for a tenant within a time period.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        period_start: Start of period (inclusive)
        period_end: End of period (exclusive)

    Returns:
        Dict mapping event_type to total quantity
    """
    session.execute(
        sa.text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": tenant_id},
    )

    results = (
        session.query(
            UsageEvent.event_type,
            func.sum(UsageEvent.quantity).label("total"),
        )
        .filter(
            and_(
                UsageEvent.tenant_id == tenant_id,
                UsageEvent.created_at >= period_start,
                UsageEvent.created_at < period_end,
            )
        )
        .group_by(UsageEvent.event_type)
        .all()
    )

    usage = {event_type: 0 for event_type in VALID_EVENT_TYPES}
    for event_type, total in results:
        usage[event_type] = int(total) if total else 0

    return usage


def get_current_month_usage(session: Session, tenant_id: str) -> Dict[str, int]:
    """Get usage for the current billing month.

    Args:
        session: Database session
        tenant_id: Tenant identifier

    Returns:
        Dict mapping event_type to total quantity for current month
    """
    now = datetime.utcnow()
    period_start = datetime(now.year, now.month, 1)

    if now.month == 12:
        period_end = datetime(now.year + 1, 1, 1)
    else:
        period_end = datetime(now.year, now.month + 1, 1)

    return get_usage(session, tenant_id, period_start, period_end)


def check_overage(session: Session, tenant_id: str, plan_name: str) -> Dict[str, Any]:
    """Check if tenant has exceeded plan limits.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        plan_name: Subscription plan name

    Returns:
        Dict with overage information:
        {
            "has_overage": bool,
            "usage": {event_type: quantity},
            "limits": {limit_name: limit_value},
            "overages": {limit_name: overage_amount}
        }
    """
    usage = get_current_month_usage(session, tenant_id)
    limits = get_plan_limits(plan_name)

    overages = {}
    has_overage = False

    if limits.get("posts_per_month") is not None:
        posts_usage = usage.get("posts_published", 0)
        posts_limit = limits["posts_per_month"]
        if posts_usage > posts_limit:
            overages["posts_per_month"] = posts_usage - posts_limit
            has_overage = True

    if limits.get("api_calls_per_day") is not None:
        now = datetime.utcnow()
        day_start = datetime(now.year, now.month, now.day)
        day_end = day_start + timedelta(days=1)
        daily_usage = get_usage(session, tenant_id, day_start, day_end)
        api_calls_usage = daily_usage.get("api_calls", 0)
        api_calls_limit = limits["api_calls_per_day"]
        if api_calls_usage > api_calls_limit:
            overages["api_calls_per_day"] = api_calls_usage - api_calls_limit
            has_overage = True

    if limits.get("platforms") is not None:
        accounts_usage = usage.get("connected_accounts", 0)
        platforms_limit = limits["platforms"]
        if accounts_usage > platforms_limit:
            overages["platforms"] = accounts_usage - platforms_limit
            has_overage = True

    return {
        "has_overage": has_overage,
        "usage": usage,
        "limits": limits,
        "overages": overages,
    }


def get_usage_summary(
    session: Session, tenant_id: str, plan_name: str
) -> Dict[str, Any]:
    """Get comprehensive usage summary with limits and percentages.

    Args:
        session: Database session
        tenant_id: Tenant identifier
        plan_name: Subscription plan name

    Returns:
        Dict with usage summary including percentages and warnings
    """
    usage = get_current_month_usage(session, tenant_id)
    limits = get_plan_limits(plan_name)
    overage_check = check_overage(session, tenant_id, plan_name)

    summary = {
        "tenant_id": tenant_id,
        "plan": plan_name,
        "period": "current_month",
        "usage": usage,
        "limits": limits,
        "has_overage": overage_check["has_overage"],
        "overages": overage_check["overages"],
        "usage_percentages": {},
        "warnings": [],
    }

    if limits.get("posts_per_month") is not None:
        posts_usage = usage.get("posts_published", 0)
        posts_limit = limits["posts_per_month"]
        percentage = (posts_usage / posts_limit * 100) if posts_limit > 0 else 0
        summary["usage_percentages"]["posts_per_month"] = round(percentage, 2)
        if percentage >= 90:
            summary["warnings"].append("posts_per_month approaching limit")

    if limits.get("api_calls_per_day") is not None:
        now = datetime.utcnow()
        day_start = datetime(now.year, now.month, now.day)
        day_end = day_start + timedelta(days=1)
        daily_usage = get_usage(session, tenant_id, day_start, day_end)
        api_calls_usage = daily_usage.get("api_calls", 0)
        api_calls_limit = limits["api_calls_per_day"]
        percentage = (
            (api_calls_usage / api_calls_limit * 100) if api_calls_limit > 0 else 0
        )
        summary["usage_percentages"]["api_calls_per_day"] = round(percentage, 2)
        if percentage >= 90:
            summary["warnings"].append("api_calls_per_day approaching limit")

    return summary
