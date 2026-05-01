"""Tests for subscription plan upgrade/downgrade flows."""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, Column, String, DateTime, Column, String, DateTime
from sqlalchemy.orm import sessionmaker

import sys

sys.path.insert(0, "/home/openclaw/projects/1ai-social")

plan_changes = __import__("1ai_social.billing.plan_changes", fromlist=["calculate_proration", "upgrade_plan", "downgrade_plan", "get_plan_change_preview", "PlanChangeError"])
calculate_proration = plan_changes.calculate_proration
upgrade_plan = plan_changes.upgrade_plan
downgrade_plan = plan_changes.downgrade_plan
get_plan_change_preview = plan_changes.get_plan_change_preview
PlanChangeError = plan_changes.PlanChangeError
lemonsqueezy = __import__('1ai_social.billing.lemonsqueezy', fromlist=['Subscription', 'Base'])
Subscription = lemonsqueezy.Subscription
Base = lemonsqueezy.Base

class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = {"extend_existing": True}
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    plan = Column(String(50), nullable=False, default="starter")
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def active_subscription(db_session):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    period_start = now - timedelta(days=10)
    period_end = now + timedelta(days=20)

    subscription = Subscription(
        tenant_id="test-tenant-1",
        lemonsqueezy_subscription_id="sub_123",
        lemonsqueezy_customer_id="cust_123",
        plan="starter",
        status="active",
        current_period_start=period_start,
        current_period_end=period_end,
        cancel_at_period_end=False,
    )
    db_session.add(subscription)
    db_session.commit()
    return subscription


def test_calculate_proration_starter_to_pro():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    period_start = now - timedelta(days=10)
    period_end = now + timedelta(days=20)

    proration = calculate_proration("starter", "pro", period_start, period_end)

    assert proration["total_days"] == 30.0
    assert proration["remaining_days"] == 20.0
    assert proration["proration_factor"] == pytest.approx(0.667, abs=0.01)
    assert proration["credit"] == pytest.approx(32.67, abs=0.5)
    assert proration["charge"] == pytest.approx(66.0, abs=0.5)
    assert proration["net"] == pytest.approx(33.33, abs=0.5)


def test_calculate_proration_pro_to_starter():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    period_start = now - timedelta(days=15)
    period_end = now + timedelta(days=15)

    proration = calculate_proration("pro", "starter", period_start, period_end)

    assert proration["total_days"] == 30.0
    assert proration["remaining_days"] == 15.0
    assert proration["credit"] == pytest.approx(49.5, abs=0.5)
    assert proration["charge"] == pytest.approx(24.5, abs=0.5)
    assert proration["net"] < 0


def test_calculate_proration_enterprise_custom_pricing():
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    period_start = now - timedelta(days=10)
    period_end = now + timedelta(days=20)

    proration = calculate_proration("pro", "enterprise", period_start, period_end)

    assert proration["credit"] == 0
    assert proration["charge"] == 0
    assert proration["net"] == 0
    assert "note" in proration


def test_upgrade_plan_starter_to_pro(db_session, active_subscription):
    result = upgrade_plan(db_session, "test-tenant-1", "pro")

    assert result["status"] == "success"
    assert result["action"] == "upgrade"
    assert result["from_plan"] == "starter"
    assert result["to_plan"] == "pro"
    assert result["applied"] == "immediately"
    assert "proration" in result
    assert result["proration"]["net"] > 0

    updated_sub = (
        db_session.query(Subscription).filter_by(tenant_id="test-tenant-1").first()
    )
    assert updated_sub.plan == "pro"
    assert updated_sub.cancel_at_period_end is False


def test_upgrade_plan_pro_to_enterprise(db_session, active_subscription):
    active_subscription.plan = "pro"
    db_session.commit()

    result = upgrade_plan(db_session, "test-tenant-1", "enterprise")

    assert result["status"] == "success"
    assert result["from_plan"] == "pro"
    assert result["to_plan"] == "enterprise"

    updated_sub = (
        db_session.query(Subscription).filter_by(tenant_id="test-tenant-1").first()
    )
    assert updated_sub.plan == "enterprise"


def test_upgrade_plan_same_plan_fails(db_session, active_subscription):
    with pytest.raises(PlanChangeError, match="Already on starter plan"):
        upgrade_plan(db_session, "test-tenant-1", "starter")


def test_upgrade_plan_downgrade_fails(db_session, active_subscription):
    active_subscription.plan = "pro"
    db_session.commit()

    with pytest.raises(PlanChangeError, match="Use downgrade_plan"):
        upgrade_plan(db_session, "test-tenant-1", "starter")


def test_upgrade_plan_no_subscription_fails(db_session):
    with pytest.raises(PlanChangeError, match="No active subscription"):
        upgrade_plan(db_session, "nonexistent-tenant", "pro")


def test_downgrade_plan_pro_to_starter(db_session, active_subscription):
    active_subscription.plan = "pro"
    db_session.commit()

    result = downgrade_plan(db_session, "test-tenant-1", "starter")

    assert result["status"] == "success"
    assert result["action"] == "downgrade"
    assert result["from_plan"] == "pro"
    assert result["to_plan"] == "starter"
    assert result["applied"] == "at_period_end"
    assert result["effective_date"] is not None

    updated_sub = (
        db_session.query(Subscription).filter_by(tenant_id="test-tenant-1").first()
    )
    assert updated_sub.plan == "pro"
    assert updated_sub.cancel_at_period_end is True


def test_downgrade_plan_enterprise_to_pro(db_session, active_subscription):
    active_subscription.plan = "enterprise"
    db_session.commit()

    result = downgrade_plan(db_session, "test-tenant-1", "pro")

    assert result["status"] == "success"
    assert result["from_plan"] == "enterprise"
    assert result["to_plan"] == "pro"


def test_downgrade_plan_same_plan_fails(db_session, active_subscription):
    with pytest.raises(PlanChangeError, match="Already on starter plan"):
        downgrade_plan(db_session, "test-tenant-1", "starter")


def test_downgrade_plan_upgrade_fails(db_session, active_subscription):
    with pytest.raises(PlanChangeError, match="Use upgrade_plan"):
        downgrade_plan(db_session, "test-tenant-1", "pro")


def test_get_plan_change_preview_upgrade(db_session, active_subscription):
    preview = get_plan_change_preview(db_session, "test-tenant-1", "pro")

    assert preview["current_plan"] == "starter"
    assert preview["target_plan"] == "pro"
    assert preview["change_type"] == "upgrade"
    assert preview["applied"] == "immediately"
    assert preview["proration"] is not None
    assert preview["proration"]["net"] > 0


def test_get_plan_change_preview_downgrade(db_session, active_subscription):
    active_subscription.plan = "pro"
    db_session.commit()

    preview = get_plan_change_preview(db_session, "test-tenant-1", "starter")

    assert preview["current_plan"] == "pro"
    assert preview["target_plan"] == "starter"
    assert preview["change_type"] == "downgrade"
    assert preview["applied"] == "at_period_end"
    assert preview["proration"] is None


def test_all_plan_transitions(db_session, active_subscription):
    transitions = [
        ("starter", "pro", "upgrade"),
        ("pro", "enterprise", "upgrade"),
        ("enterprise", "pro", "downgrade"),
        ("pro", "starter", "downgrade"),
    ]

    for from_plan, to_plan, expected_type in transitions:
        active_subscription.plan = from_plan
        active_subscription.cancel_at_period_end = False
        db_session.commit()

        preview = get_plan_change_preview(db_session, "test-tenant-1", to_plan)
        assert preview["change_type"] == expected_type, (
            f"Failed: {from_plan} -> {to_plan}"
        )
