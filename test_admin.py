"""Test admin dashboard API endpoints."""

import os
import sys
from datetime import datetime, timezone, timedelta

os.environ["DATABASE_URL"] = "postgresql://localhost/1ai_social_test"

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib

admin_module = importlib.import_module("1ai_social.admin")
get_admin_metrics = admin_module.get_admin_metrics
get_admin_users = admin_module.get_admin_users
get_admin_subscriptions = admin_module.get_admin_subscriptions
get_admin_analytics = admin_module.get_admin_analytics
AdminAuthError = admin_module.AdminAuthError

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
    lemonsqueezy_subscription_id = Column(String(255), nullable=False)
    plan = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)


class Post(Base):
    __tablename__ = "posts"
    id = Column(String(255), primary_key=True)
    platform_id = Column(Integer, nullable=False)
    scheduled_time = Column(DateTime, nullable=True)
    published_time = Column(DateTime, nullable=True)
    status = Column(String(50), default="draft", nullable=False)


class AnalyticsRecord(Base):
    __tablename__ = "analytics_records"
    id = Column(Integer, primary_key=True)
    post_id = Column(String(255), nullable=False)
    views = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    engagement_rate = Column(Integer, default=0, nullable=False)
    recorded_at = Column(DateTime, nullable=False)


def setup_test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    tenants = [
        Tenant(
            id="tenant1",
            name="Acme Corp",
            plan="pro",
            status="active",
            created_at=now - timedelta(days=25),
        ),
        Tenant(
            id="tenant2",
            name="Beta Inc",
            plan="starter",
            status="active",
            created_at=now - timedelta(days=5),
        ),
        Tenant(
            id="tenant3",
            name="Gamma LLC",
            plan="enterprise",
            status="active",
            created_at=now - timedelta(days=60),
        ),
    ]

    subscriptions = [
        Subscription(
            id=1,
            tenant_id="tenant1",
            lemonsqueezy_subscription_id="ls_sub_1",
            plan="pro",
            status="active",
            current_period_start=now - timedelta(days=10),
            current_period_end=now + timedelta(days=20),
            cancel_at_period_end=False,
            created_at=now - timedelta(days=25),
        ),
        Subscription(
            id=2,
            tenant_id="tenant2",
            lemonsqueezy_subscription_id="ls_sub_2",
            plan="starter",
            status="active",
            current_period_start=now - timedelta(days=5),
            current_period_end=now + timedelta(days=25),
            cancel_at_period_end=False,
            created_at=now - timedelta(days=5),
        ),
        Subscription(
            id=3,
            tenant_id="tenant3",
            lemonsqueezy_subscription_id="ls_sub_3",
            plan="enterprise",
            status="active",
            current_period_start=now - timedelta(days=15),
            current_period_end=now + timedelta(days=15),
            cancel_at_period_end=False,
            created_at=now - timedelta(days=60),
        ),
    ]

    posts = [
        Post(
            id="post1",
            platform_id=1,
            published_time=now - timedelta(days=5),
            status="published",
        ),
        Post(
            id="post2",
            platform_id=2,
            published_time=now - timedelta(days=10),
            status="published",
        ),
        Post(
            id="post3",
            platform_id=1,
            published_time=now - timedelta(days=15),
            status="published",
        ),
    ]

    analytics = [
        AnalyticsRecord(
            id=1,
            post_id="post1",
            views=1000,
            likes=50,
            shares=10,
            comments=5,
            engagement_rate=6.5,
            recorded_at=now - timedelta(days=5),
        ),
        AnalyticsRecord(
            id=2,
            post_id="post2",
            views=2000,
            likes=100,
            shares=20,
            comments=10,
            engagement_rate=6.5,
            recorded_at=now - timedelta(days=10),
        ),
        AnalyticsRecord(
            id=3,
            post_id="post3",
            views=1500,
            likes=75,
            shares=15,
            comments=8,
            engagement_rate=6.5,
            recorded_at=now - timedelta(days=15),
        ),
    ]

    session.add_all(tenants)
    session.add_all(subscriptions)
    session.add_all(posts)
    session.add_all(analytics)
    session.commit()

    return session


def test_admin_auth():
    print("Testing admin authorization...")
    session = setup_test_db()

    try:
        get_admin_metrics(session, "user")
        print("❌ FAIL: Non-admin should be rejected")
    except AdminAuthError:
        print("✓ PASS: Non-admin rejected")

    session.close()


def test_admin_metrics():
    print("\nTesting admin metrics...")
    session = setup_test_db()

    result = get_admin_metrics(session, "admin")

    print(f"MRR: ${result['mrr']['total_mrr']}")
    print(f"Active Users: {result['active_users']}")
    print(f"New Signups (30d): {result['new_signups_30d']}")
    print(f"Churn Rate: {result['churn_rate']}%")

    assert result["mrr"]["total_mrr"] == 148, (
        f"Expected MRR $148, got ${result['mrr']['total_mrr']}"
    )
    assert result["active_users"] == 3, (
        f"Expected 3 users, got {result['active_users']}"
    )
    assert result["new_signups_30d"] == 2, (
        f"Expected 2 signups, got {result['new_signups_30d']}"
    )

    print("✓ PASS: Admin metrics correct")
    session.close()


def test_admin_users():
    print("\nTesting admin users list...")
    session = setup_test_db()

    result = get_admin_users(session, "admin", page=1, per_page=10)

    print(f"Total Users: {result['pagination']['total']}")
    print(f"Users on page: {len(result['users'])}")

    assert result["pagination"]["total"] == 3
    assert len(result["users"]) == 3

    print("\nTesting search...")
    result = get_admin_users(session, "admin", page=1, per_page=10, search="Acme")
    assert len(result["users"]) == 1
    assert result["users"][0]["name"] == "Acme Corp"

    print("✓ PASS: Admin users list and search work")
    session.close()


def test_admin_subscriptions():
    print("\nTesting admin subscriptions...")
    session = setup_test_db()

    result = get_admin_subscriptions(session, "admin")

    print(f"Total Subscriptions: {result['total']}")
    print(f"Summary: {result['summary']}")

    assert result["total"] == 3
    assert result["summary"]["active"] == 3

    print("\nTesting status filter...")
    result = get_admin_subscriptions(session, "admin", status="active")
    assert result["total"] == 3

    print("✓ PASS: Admin subscriptions work")
    session.close()


def test_admin_analytics():
    print("\nTesting admin analytics...")
    session = setup_test_db()

    result = get_admin_analytics(session, "admin", period="30d")

    print(f"Period: {result['period']}")
    print(f"Posts Published: {result['posts_published']}")
    print(f"Engagement: {result['engagement']}")

    assert result["period"] == "30d"
    assert "posts_published" in result
    assert "engagement" in result

    print("✓ PASS: Admin analytics work")
    session.close()


if __name__ == "__main__":
    print("=" * 50)
    print("Admin Dashboard API Tests")
    print("=" * 50)

    test_admin_auth()
    test_admin_metrics()
    test_admin_users()
    test_admin_subscriptions()
    test_admin_analytics()

    print("\n" + "=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)
