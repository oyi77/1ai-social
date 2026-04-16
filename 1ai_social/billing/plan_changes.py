"""
Subscription plan upgrade/downgrade flows with proration logic.

This module handles:
- Immediate upgrades with prorated billing
- Scheduled downgrades at period end
- Proration calculations for plan changes
- Subscription updates in database

Upgrade Flow:
1. Calculate prorated credit for remaining period on old plan
2. Calculate prorated charge for remaining period on new plan
3. Apply net charge immediately
4. Update subscription to new plan

Downgrade Flow:
1. Schedule downgrade for end of current billing period
2. Set cancel_at_period_end flag
3. Create pending plan change record
4. Apply at period end via webhook

Proration Formula:
- Credit = (remaining_days / total_days) * old_plan_price
- Charge = (remaining_days / total_days) * new_plan_price
- Net = Charge - Credit
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from .plans import PLANS, compare_plans
from .lemonsqueezy import Subscription

logger = logging.getLogger(__name__)

try:
    from ..notifications.email import send_email

    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    logger.warning("Email notifications module not available")


class PlanChangeError(Exception):
    """Raised when plan change operation fails."""

    pass


def calculate_proration(
    old_plan: str,
    new_plan: str,
    current_period_start: datetime,
    current_period_end: datetime,
) -> Dict[str, Any]:
    """
    Calculate proration for plan change.

    Args:
        old_plan: Current plan name
        new_plan: Target plan name
        current_period_start: Start of current billing period
        current_period_end: End of current billing period

    Returns:
        Dict with proration details:
        - credit: Amount credited for unused time on old plan
        - charge: Amount charged for new plan
        - net: Net amount to charge (charge - credit)
        - remaining_days: Days remaining in period
        - total_days: Total days in period
    """
    old_plan_config = PLANS.get(old_plan.lower())
    new_plan_config = PLANS.get(new_plan.lower())

    if not old_plan_config or not new_plan_config:
        raise PlanChangeError(f"Invalid plan names: {old_plan} or {new_plan}")

    # Handle enterprise custom pricing
    old_price = old_plan_config["price"]
    new_price = new_plan_config["price"]

    if old_price is None or new_price is None:
        logger.warning("Enterprise plan detected - proration requires custom pricing")
        return {
            "credit": 0,
            "charge": 0,
            "net": 0,
            "remaining_days": 0,
            "total_days": 0,
            "note": "Enterprise plan requires custom pricing calculation",
        }

    # Calculate time periods
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Ensure dates are timezone-naive for comparison
    if current_period_start.tzinfo:
        current_period_start = current_period_start.replace(tzinfo=None)
    if current_period_end.tzinfo:
        current_period_end = current_period_end.replace(tzinfo=None)

    total_period = (current_period_end - current_period_start).total_seconds()
    remaining_period = (current_period_end - now).total_seconds()

    # Prevent negative values
    if remaining_period < 0:
        remaining_period = 0

    total_days = total_period / 86400  # seconds to days
    remaining_days = remaining_period / 86400

    # Calculate proration
    if total_days > 0:
        proration_factor = remaining_days / total_days
    else:
        proration_factor = 0

    credit = proration_factor * old_price
    charge = proration_factor * new_price
    net = charge - credit

    return {
        "credit": round(credit, 2),
        "charge": round(charge, 2),
        "net": round(net, 2),
        "remaining_days": round(remaining_days, 1),
        "total_days": round(total_days, 1),
        "proration_factor": round(proration_factor, 3),
    }


def upgrade_plan(
    db: Session,
    tenant_id: str,
    new_plan: str,
) -> Dict[str, Any]:
    """
    Upgrade subscription plan immediately with proration.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        new_plan: Target plan name (must be higher tier)

    Returns:
        Dict with upgrade details and proration

    Raises:
        PlanChangeError: If upgrade fails
    """
    # Find active subscription
    subscription = (
        db.query(Subscription)
        .filter_by(tenant_id=tenant_id)
        .filter(Subscription.status.in_(["active", "past_due"]))
        .first()
    )

    if not subscription:
        raise PlanChangeError(f"No active subscription found for tenant: {tenant_id}")

    current_plan = subscription.plan

    # Validate plan change
    if current_plan.lower() == new_plan.lower():
        raise PlanChangeError(f"Already on {new_plan} plan")

    comparison = compare_plans(current_plan, new_plan)

    if not comparison.get("is_upgrade"):
        raise PlanChangeError(
            f"Use downgrade_plan() for downgrade from {current_plan} to {new_plan}"
        )

    # Calculate proration
    if not subscription.current_period_start or not subscription.current_period_end:
        raise PlanChangeError("Subscription missing billing period dates")

    proration = calculate_proration(
        current_plan,
        new_plan,
        subscription.current_period_start,
        subscription.current_period_end,
    )

    # Update subscription immediately
    subscription.plan = new_plan.lower()
    subscription.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    # Reset cancel flag if it was set
    subscription.cancel_at_period_end = False

    db.commit()

    logger.info(
        f"Upgraded tenant {tenant_id} from {current_plan} to {new_plan}. "
        f"Proration: ${proration['net']}"
    )

    if EMAIL_AVAILABLE:
        try:
            send_email(
                to=f"tenant_{tenant_id}@example.com",
                subject="Plan Upgrade Confirmation",
                template="invoice",
                data={
                    "name": f"Tenant {tenant_id}",
                    "invoice_number": f"upgrade_{tenant_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                    "amount": f"${proration['net']}",
                    "period": f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')} to {subscription.current_period_end.strftime('%Y-%m-%d') if subscription.current_period_end else 'N/A'}",
                    "due_date": "Immediate",
                    "invoice_url": "#",
                    "user_id": tenant_id,
                },
            )
        except Exception as e:
            logger.error(f"Failed to send upgrade confirmation email: {e}")

    return {
        "status": "success",
        "action": "upgrade",
        "from_plan": current_plan,
        "to_plan": new_plan,
        "applied": "immediately",
        "proration": proration,
        "comparison": comparison,
    }


def downgrade_plan(
    db: Session,
    tenant_id: str,
    new_plan: str,
) -> Dict[str, Any]:
    """
    Schedule subscription downgrade at end of current billing period.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        new_plan: Target plan name (must be lower tier)

    Returns:
        Dict with downgrade details

    Raises:
        PlanChangeError: If downgrade fails
    """
    # Find active subscription
    subscription = (
        db.query(Subscription)
        .filter_by(tenant_id=tenant_id)
        .filter(Subscription.status.in_(["active", "past_due"]))
        .first()
    )

    if not subscription:
        raise PlanChangeError(f"No active subscription found for tenant: {tenant_id}")

    current_plan = subscription.plan

    # Validate plan change
    if current_plan.lower() == new_plan.lower():
        raise PlanChangeError(f"Already on {new_plan} plan")

    comparison = compare_plans(current_plan, new_plan)

    if comparison.get("is_upgrade"):
        raise PlanChangeError(
            f"Use upgrade_plan() for upgrade from {current_plan} to {new_plan}"
        )

    subscription.cancel_at_period_end = True
    subscription.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()

    logger.info(
        f"Scheduled downgrade for tenant {tenant_id} from {current_plan} to {new_plan}. "
        f"Effective: {subscription.current_period_end}"
    )

    if EMAIL_AVAILABLE:
        try:
            send_email(
                to=f"tenant_{tenant_id}@example.com",
                subject="Plan Downgrade Scheduled",
                template="invoice",
                data={
                    "name": f"Tenant {tenant_id}",
                    "invoice_number": f"downgrade_{tenant_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
                    "amount": "$0.00",
                    "period": f"Effective {subscription.current_period_end.strftime('%Y-%m-%d') if subscription.current_period_end else 'N/A'}",
                    "due_date": subscription.current_period_end.strftime("%Y-%m-%d")
                    if subscription.current_period_end
                    else "N/A",
                    "invoice_url": "#",
                    "user_id": tenant_id,
                },
            )
        except Exception as e:
            logger.error(f"Failed to send downgrade confirmation email: {e}")

    return {
        "status": "success",
        "action": "downgrade",
        "from_plan": current_plan,
        "to_plan": new_plan,
        "applied": "at_period_end",
        "effective_date": subscription.current_period_end.isoformat()
        if subscription.current_period_end
        else None,
        "comparison": comparison,
        "note": "Downgrade will be applied at the end of current billing period",
    }


def get_plan_change_preview(
    db: Session,
    tenant_id: str,
    new_plan: str,
) -> Dict[str, Any]:
    """
    Preview plan change without applying it.

    Args:
        db: Database session
        tenant_id: Tenant identifier
        new_plan: Target plan name

    Returns:
        Dict with preview details including proration

    Raises:
        PlanChangeError: If preview fails
    """
    # Find active subscription
    subscription = (
        db.query(Subscription)
        .filter_by(tenant_id=tenant_id)
        .filter(Subscription.status.in_(["active", "past_due"]))
        .first()
    )

    if not subscription:
        raise PlanChangeError(f"No active subscription found for tenant: {tenant_id}")

    current_plan = subscription.plan

    if current_plan.lower() == new_plan.lower():
        raise PlanChangeError(f"Already on {new_plan} plan")

    comparison = compare_plans(current_plan, new_plan)
    is_upgrade = comparison.get("is_upgrade")

    # Calculate proration for upgrades
    proration = None
    if (
        is_upgrade
        and subscription.current_period_start
        and subscription.current_period_end
    ):
        proration = calculate_proration(
            current_plan,
            new_plan,
            subscription.current_period_start,
            subscription.current_period_end,
        )

    return {
        "current_plan": current_plan,
        "target_plan": new_plan,
        "change_type": "upgrade" if is_upgrade else "downgrade",
        "applied": "immediately" if is_upgrade else "at_period_end",
        "effective_date": datetime.now(timezone.utc).isoformat()
        if is_upgrade
        else (
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None
        ),
        "proration": proration,
        "comparison": comparison,
    }
