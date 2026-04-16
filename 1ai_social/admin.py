"""Admin dashboard API endpoints for metrics, users, and analytics.

Provides admin-only access to:
- MRR (Monthly Recurring Revenue) calculations
- User management and search
- Subscription analytics
- Usage analytics and trends
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

logger = logging.getLogger(__name__)


class AdminAuthError(Exception):
    """Raised when non-admin user attempts admin access."""

    pass


def check_admin_role(user_role: str) -> None:
    """Verify user has admin role.

    Args:
        user_role: User's role string

    Raises:
        AdminAuthError: If user is not admin
    """
    if user_role != "admin":
        logger.warning(f"Unauthorized admin access attempt by role: {user_role}")
        raise AdminAuthError("Admin access required")


def calculate_mrr(session: Session) -> Dict[str, Any]:
    """Calculate Monthly Recurring Revenue from active subscriptions.

    Args:
        session: Database session

    Returns:
        Dict with MRR breakdown by plan
    """
    from .billing.plans import PLANS

    # Import subscription model
    from sqlalchemy import Column, Integer, String, DateTime, Boolean
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class Subscription(Base):
        __tablename__ = "subscriptions"
        id = Column(Integer, primary_key=True)
        tenant_id = Column(String(255), nullable=False)
        plan = Column(String(50), nullable=False)
        status = Column(String(50), nullable=False)
        current_period_start = Column(DateTime, nullable=True)
        current_period_end = Column(DateTime, nullable=True)
        cancel_at_period_end = Column(Boolean, nullable=False, default=False)

    # Query active subscriptions
    active_subs = session.execute(
        select(Subscription.plan, func.count(Subscription.id))
        .where(Subscription.status == "active")
        .group_by(Subscription.plan)
    ).all()

    mrr_by_plan = {}
    total_mrr = 0

    for plan_name, count in active_subs:
        plan_config = PLANS.get(plan_name.lower())
        if plan_config and plan_config["price"]:
            plan_mrr = plan_config["price"] * count
            mrr_by_plan[plan_name] = {
                "count": count,
                "price": plan_config["price"],
                "mrr": plan_mrr,
            }
            total_mrr += plan_mrr

    return {"total_mrr": total_mrr, "by_plan": mrr_by_plan, "currency": "USD"}


def get_admin_metrics(session: Session, user_role: str) -> Dict[str, Any]:
    """Get admin dashboard metrics: MRR, users, churn, signups.

    Args:
        session: Database session
        user_role: User's role for authorization

    Returns:
        Dict with all admin metrics

    Raises:
        AdminAuthError: If user is not admin
    """
    check_admin_role(user_role)

    from sqlalchemy import Column, Integer, String, DateTime, Boolean
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class Subscription(Base):
        __tablename__ = "subscriptions"
        id = Column(Integer, primary_key=True)
        tenant_id = Column(String(255), nullable=False)
        plan = Column(String(50), nullable=False)
        status = Column(String(50), nullable=False)
        created_at = Column(DateTime, nullable=False)
        cancel_at_period_end = Column(Boolean, nullable=False, default=False)

    class Tenant(Base):
        __tablename__ = "tenants"
        id = Column(String(255), primary_key=True)
        name = Column(String(255), nullable=False)
        plan = Column(String(50), nullable=False)
        status = Column(String(50), nullable=False)
        created_at = Column(DateTime, nullable=False)

    # Calculate MRR
    mrr_data = calculate_mrr(session)

    # Active users count
    active_users = session.execute(
        select(func.count(Tenant.id)).where(Tenant.status == "active")
    ).scalar()

    # New signups (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    new_signups = session.execute(
        select(func.count(Tenant.id)).where(Tenant.created_at >= thirty_days_ago)
    ).scalar()

    # Churn rate calculation (cancelled in last 30 days / active at start of period)
    cancelled_count = session.execute(
        select(func.count(Subscription.id)).where(
            and_(
                Subscription.status == "cancelled",
                Subscription.created_at >= thirty_days_ago,
            )
        )
    ).scalar()

    churn_rate = (cancelled_count / active_users * 100) if active_users > 0 else 0

    logger.info(
        f"Admin metrics retrieved: MRR=${mrr_data['total_mrr']}, Users={active_users}"
    )

    return {
        "mrr": mrr_data,
        "active_users": active_users or 0,
        "new_signups_30d": new_signups or 0,
        "churn_rate": round(churn_rate, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_admin_users(
    session: Session,
    user_role: str,
    page: int = 1,
    per_page: int = 50,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Get paginated user list with search/filter.

    Args:
        session: Database session
        user_role: User's role for authorization
        page: Page number (1-indexed)
        per_page: Results per page
        search: Optional search query (name, email, tenant_id)

    Returns:
        Dict with users list and pagination info

    Raises:
        AdminAuthError: If user is not admin
    """
    check_admin_role(user_role)

    from sqlalchemy import Column, Integer, String, DateTime
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class Tenant(Base):
        __tablename__ = "tenants"
        id = Column(String(255), primary_key=True)
        name = Column(String(255), nullable=False)
        plan = Column(String(50), nullable=False)
        status = Column(String(50), nullable=False)
        created_at = Column(DateTime, nullable=False)

    class Subscription(Base):
        __tablename__ = "subscriptions"
        id = Column(Integer, primary_key=True)
        tenant_id = Column(String(255), nullable=False)
        plan = Column(String(50), nullable=False)
        status = Column(String(50), nullable=False)

    # Build query
    query = select(Tenant)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(Tenant.name.ilike(search_pattern), Tenant.id.ilike(search_pattern))
        )

    # Get total count
    total_count = session.execute(
        select(func.count()).select_from(query.subquery())
    ).scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Tenant.created_at.desc()).offset(offset).limit(per_page)

    tenants = session.execute(query).scalars().all()

    # Enrich with subscription data
    users = []
    for tenant in tenants:
        subscription = (
            session.execute(
                select(Subscription)
                .where(Subscription.tenant_id == tenant.id)
                .order_by(Subscription.id.desc())
            )
            .scalars()
            .first()
        )

        users.append(
            {
                "tenant_id": tenant.id,
                "name": tenant.name,
                "plan": tenant.plan,
                "status": tenant.status,
                "subscription_status": subscription.status if subscription else "none",
                "created_at": tenant.created_at.isoformat(),
            }
        )

    total_pages = (total_count + per_page - 1) // per_page

    logger.info(f"Admin users list retrieved: page={page}, count={len(users)}")

    return {
        "users": users,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total_count,
            "total_pages": total_pages,
        },
    }


def get_admin_subscriptions(
    session: Session, user_role: str, status: Optional[str] = None
) -> Dict[str, Any]:
    """Get subscription management data with optional status filter.

    Args:
        session: Database session
        user_role: User's role for authorization
        status: Optional status filter (active, cancelled, past_due, etc.)

    Returns:
        Dict with subscriptions list and summary stats

    Raises:
        AdminAuthError: If user is not admin
    """
    check_admin_role(user_role)

    from sqlalchemy import Column, Integer, String, DateTime, Boolean
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class Subscription(Base):
        __tablename__ = "subscriptions"
        id = Column(Integer, primary_key=True)
        tenant_id = Column(String(255), nullable=False)
        lemonsqueezy_subscription_id = Column(String(255), nullable=False)
        plan = Column(String(50), nullable=False)
        status = Column(String(50), nullable=False)
        current_period_start = Column(DateTime, nullable=True)
        current_period_end = Column(DateTime, nullable=True)
        cancel_at_period_end = Column(Boolean, nullable=False, default=False)
        created_at = Column(DateTime, nullable=False)

    class Tenant(Base):
        __tablename__ = "tenants"
        id = Column(String(255), primary_key=True)
        name = Column(String(255), nullable=False)

    # Build query
    query = select(Subscription)

    if status:
        query = query.where(Subscription.status == status)

    subscriptions_data = (
        session.execute(query.order_by(Subscription.created_at.desc())).scalars().all()
    )

    # Enrich with tenant names
    subscriptions = []
    for sub in subscriptions_data:
        tenant = (
            session.execute(select(Tenant).where(Tenant.id == sub.tenant_id))
            .scalars()
            .first()
        )

        subscriptions.append(
            {
                "id": sub.id,
                "tenant_id": sub.tenant_id,
                "tenant_name": tenant.name if tenant else "Unknown",
                "plan": sub.plan,
                "status": sub.status,
                "lemonsqueezy_id": sub.lemonsqueezy_subscription_id,
                "current_period_start": sub.current_period_start.isoformat()
                if sub.current_period_start
                else None,
                "current_period_end": sub.current_period_end.isoformat()
                if sub.current_period_end
                else None,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "created_at": sub.created_at.isoformat(),
            }
        )

    # Summary stats by status
    status_counts = session.execute(
        select(Subscription.status, func.count(Subscription.id)).group_by(
            Subscription.status
        )
    ).all()

    summary = {status: count for status, count in status_counts}

    logger.info(
        f"Admin subscriptions retrieved: count={len(subscriptions)}, filter={status}"
    )

    return {
        "subscriptions": subscriptions,
        "summary": summary,
        "total": len(subscriptions),
    }


def get_admin_analytics(
    session: Session, user_role: str, period: str = "30d"
) -> Dict[str, Any]:
    """Get usage analytics for specified period.

    Args:
        session: Database session
        user_role: User's role for authorization
        period: Time period (7d, 30d, 90d, 1y)

    Returns:
        Dict with analytics data and trends

    Raises:
        AdminAuthError: If user is not admin
    """
    check_admin_role(user_role)

    from .db_models import PostModel, AnalyticsRecordModel

    # Parse period
    period_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}

    days = period_map.get(period, 30)
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Posts published in period
    posts_count = session.execute(
        select(func.count(PostModel.id)).where(
            and_(
                PostModel.published_time >= start_date, PostModel.status == "published"
            )
        )
    ).scalar()

    # Posts by platform
    posts_by_platform = session.execute(
        select(PostModel.platform_id, func.count(PostModel.id))
        .where(
            and_(
                PostModel.published_time >= start_date, PostModel.status == "published"
            )
        )
        .group_by(PostModel.platform_id)
    ).all()

    # Total engagement metrics
    engagement = session.execute(
        select(
            func.sum(AnalyticsRecordModel.views),
            func.sum(AnalyticsRecordModel.likes),
            func.sum(AnalyticsRecordModel.shares),
            func.sum(AnalyticsRecordModel.comments),
        ).where(AnalyticsRecordModel.recorded_at >= start_date)
    ).first()

    total_views = engagement[0] or 0
    total_likes = engagement[1] or 0
    total_shares = engagement[2] or 0
    total_comments = engagement[3] or 0

    # Average engagement rate
    avg_engagement = session.execute(
        select(func.avg(AnalyticsRecordModel.engagement_rate)).where(
            AnalyticsRecordModel.recorded_at >= start_date
        )
    ).scalar()

    logger.info(f"Admin analytics retrieved: period={period}, posts={posts_count}")

    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": datetime.now(timezone.utc).isoformat(),
        "posts_published": posts_count or 0,
        "posts_by_platform": dict(posts_by_platform) if posts_by_platform else {},
        "engagement": {
            "total_views": total_views,
            "total_likes": total_likes,
            "total_shares": total_shares,
            "total_comments": total_comments,
            "avg_engagement_rate": round(avg_engagement or 0, 2),
        },
    }
