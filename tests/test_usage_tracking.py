"""Test usage tracking and metering functionality."""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import sys
import os
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

usage_module = importlib.import_module("1ai_social.billing.usage")
plans_module = importlib.import_module("1ai_social.billing.plans")

UsageEvent = usage_module.UsageEvent
record_usage = usage_module.record_usage
get_usage = usage_module.get_usage
get_current_month_usage = usage_module.get_current_month_usage
check_overage = usage_module.check_overage
get_usage_summary = usage_module.get_usage_summary
VALID_EVENT_TYPES = usage_module.VALID_EVENT_TYPES
get_plan_limits = plans_module.get_plan_limits


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE tenants (
                id VARCHAR(255) PRIMARY KEY
            )
        """)
        )

        conn.execute(
            text("""
            CREATE TABLE usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id VARCHAR(255) NOT NULL,
                event_type VARCHAR(100) NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                metadata TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        """)
        )

        conn.execute(text("INSERT INTO tenants (id) VALUES ('tenant-123')"))
        conn.commit()

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    engine.dispose()


def test_record_usage_valid(db_session):
    event = record_usage(
        db_session,
        "tenant-123",
        "posts_published",
        quantity=5,
        metadata={"platform": "twitter"},
    )

    assert event.id is not None
    assert event.tenant_id == "tenant-123"
    assert event.event_type == "posts_published"
    assert event.quantity == 5
    assert event.event_metadata == {"platform": "twitter"}


def test_record_usage_invalid_event_type(db_session):
    with pytest.raises(ValueError, match="Invalid event_type"):
        record_usage(db_session, "tenant-123", "invalid_type")


def test_record_usage_invalid_quantity(db_session):
    with pytest.raises(ValueError, match="Quantity must be positive"):
        record_usage(db_session, "tenant-123", "posts_published", quantity=0)

    with pytest.raises(ValueError, match="Quantity must be positive"):
        record_usage(db_session, "tenant-123", "posts_published", quantity=-5)


def test_get_usage(db_session):
    now = datetime.utcnow()
    period_start = now - timedelta(days=7)
    period_end = now + timedelta(days=1)

    record_usage(db_session, "tenant-123", "posts_published", 10)
    record_usage(db_session, "tenant-123", "posts_published", 5)
    record_usage(db_session, "tenant-123", "api_calls", 100)

    usage = get_usage(db_session, "tenant-123", period_start, period_end)

    assert usage["posts_published"] == 15
    assert usage["api_calls"] == 100
    assert usage["connected_accounts"] == 0


def test_get_current_month_usage(db_session):
    record_usage(db_session, "tenant-123", "posts_published", 25)
    record_usage(db_session, "tenant-123", "api_calls", 500)

    usage = get_current_month_usage(db_session, "tenant-123")

    assert usage["posts_published"] == 25
    assert usage["api_calls"] == 500


def test_check_overage_no_overage(db_session):
    record_usage(db_session, "tenant-123", "posts_published", 100)

    result = check_overage(db_session, "tenant-123", "starter")

    assert result["has_overage"] is False
    assert result["overages"] == {}
    assert result["usage"]["posts_published"] == 100


def test_check_overage_with_overage(db_session):
    record_usage(db_session, "tenant-123", "posts_published", 600)

    result = check_overage(db_session, "tenant-123", "starter")

    assert result["has_overage"] is True
    assert "posts_per_month" in result["overages"]
    assert result["overages"]["posts_per_month"] == 100


def test_check_overage_enterprise_unlimited(db_session):
    record_usage(db_session, "tenant-123", "posts_published", 10000)

    result = check_overage(db_session, "tenant-123", "enterprise")

    assert result["has_overage"] is False


def test_get_usage_summary(db_session):
    record_usage(db_session, "tenant-123", "posts_published", 450)

    summary = get_usage_summary(db_session, "tenant-123", "starter")

    assert summary["tenant_id"] == "tenant-123"
    assert summary["plan"] == "starter"
    assert summary["usage"]["posts_published"] == 450
    assert summary["usage_percentages"]["posts_per_month"] == 90.0
    assert "posts_per_month approaching limit" in summary["warnings"]


def test_valid_event_types():
    assert "posts_published" in VALID_EVENT_TYPES
    assert "api_calls" in VALID_EVENT_TYPES
    assert "connected_accounts" in VALID_EVENT_TYPES
    assert len(VALID_EVENT_TYPES) == 3
