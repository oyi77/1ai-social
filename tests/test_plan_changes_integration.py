#!/usr/bin/env python3
import sys

sys.path.insert(0, ".")

from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import sessionmaker

plan_changes = __import__(
    "1ai_social.billing.plan_changes",
    fromlist=[
        "calculate_proration",
        "upgrade_plan",
        "downgrade_plan",
        "get_plan_change_preview",
        "PlanChangeError",
    ],
)
lemonsqueezy = __import__(
    "1ai_social.billing.lemonsqueezy", fromlist=["Subscription", "Base"]
)

calculate_proration = plan_changes.calculate_proration
upgrade_plan = plan_changes.upgrade_plan
downgrade_plan = plan_changes.downgrade_plan
get_plan_change_preview = plan_changes.get_plan_change_preview
PlanChangeError = plan_changes.PlanChangeError
Subscription = lemonsqueezy.Subscription
Base = lemonsqueezy.Base


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    plan = Column(String(50), nullable=False, default="starter")
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    tenant = Tenant(
        id="test-tenant-1", name="Test Tenant", plan="starter", status="active"
    )
    session.add(tenant)
    session.commit()

    return session


def create_test_subscription(db, tenant_id="test-tenant-1", plan="starter"):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    period_start = now - timedelta(days=10)
    period_end = now + timedelta(days=20)

    subscription = Subscription(
        tenant_id=tenant_id,
        lemonsqueezy_subscription_id=f"sub_{tenant_id}",
        lemonsqueezy_customer_id=f"cust_{tenant_id}",
        plan=plan,
        status="active",
        current_period_start=period_start,
        current_period_end=period_end,
        cancel_at_period_end=False,
    )
    db.add(subscription)
    db.commit()
    return subscription


def test_proration():
    print("\n=== Test: Proration Calculation ===")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    period_start = now - timedelta(days=10)
    period_end = now + timedelta(days=20)

    proration = calculate_proration("starter", "pro", period_start, period_end)

    print(f"Total days: {proration['total_days']}")
    print(f"Remaining days: {proration['remaining_days']}")
    print(f"Proration factor: {proration['proration_factor']}")
    print(f"Credit (old plan): ${proration['credit']}")
    print(f"Charge (new plan): ${proration['charge']}")
    print(f"Net charge: ${proration['net']}")

    assert proration["total_days"] == 30.0
    assert proration["remaining_days"] == 20.0
    assert abs(proration["net"] - 33.33) < 1.0
    print("✓ Proration calculation correct")


def test_upgrade_starter_to_pro():
    print("\n=== Test: Upgrade starter -> pro ===")
    db = setup_db()
    create_test_subscription(db, "tenant-1", "starter")

    result = upgrade_plan(db, "tenant-1", "pro")

    print(f"Status: {result['status']}")
    print(f"Action: {result['action']}")
    print(f"From: {result['from_plan']} -> To: {result['to_plan']}")
    print(f"Applied: {result['applied']}")
    print(f"Net charge: ${result['proration']['net']}")

    updated_sub = db.query(Subscription).filter_by(tenant_id="tenant-1").first()
    assert updated_sub.plan == "pro"
    assert result["applied"] == "immediately"
    print("✓ Upgrade applied immediately")


def test_upgrade_pro_to_enterprise():
    print("\n=== Test: Upgrade pro -> enterprise ===")
    db = setup_db()
    create_test_subscription(db, "tenant-2", "pro")

    result = upgrade_plan(db, "tenant-2", "enterprise")

    print(f"From: {result['from_plan']} -> To: {result['to_plan']}")

    updated_sub = db.query(Subscription).filter_by(tenant_id="tenant-2").first()
    assert updated_sub.plan == "enterprise"
    print("✓ Upgrade to enterprise successful")


def test_downgrade_pro_to_starter():
    print("\n=== Test: Downgrade pro -> starter ===")
    db = setup_db()
    create_test_subscription(db, "tenant-3", "pro")

    result = downgrade_plan(db, "tenant-3", "starter")

    print(f"Status: {result['status']}")
    print(f"Action: {result['action']}")
    print(f"From: {result['from_plan']} -> To: {result['to_plan']}")
    print(f"Applied: {result['applied']}")
    print(f"Effective date: {result['effective_date']}")

    updated_sub = db.query(Subscription).filter_by(tenant_id="tenant-3").first()
    assert updated_sub.plan == "pro"
    assert updated_sub.cancel_at_period_end is True
    assert result["applied"] == "at_period_end"
    print("✓ Downgrade scheduled for period end")


def test_downgrade_enterprise_to_pro():
    print("\n=== Test: Downgrade enterprise -> pro ===")
    db = setup_db()
    create_test_subscription(db, "tenant-4", "enterprise")

    result = downgrade_plan(db, "tenant-4", "pro")

    print(f"From: {result['from_plan']} -> To: {result['to_plan']}")

    updated_sub = db.query(Subscription).filter_by(tenant_id="tenant-4").first()
    assert updated_sub.cancel_at_period_end is True
    print("✓ Downgrade from enterprise scheduled")


def test_invalid_same_plan():
    print("\n=== Test: Invalid - same plan ===")
    db = setup_db()
    create_test_subscription(db, "tenant-5", "starter")

    try:
        upgrade_plan(db, "tenant-5", "starter")
        assert False, "Should have raised error"
    except PlanChangeError as e:
        print(f"✓ Correctly rejected: {e}")


def test_invalid_upgrade_as_downgrade():
    print("\n=== Test: Invalid - upgrade using downgrade function ===")
    db = setup_db()
    create_test_subscription(db, "tenant-6", "starter")

    try:
        downgrade_plan(db, "tenant-6", "pro")
        assert False, "Should have raised error"
    except PlanChangeError as e:
        print(f"✓ Correctly rejected: {e}")


def test_preview():
    print("\n=== Test: Plan change preview ===")
    db = setup_db()
    create_test_subscription(db, "tenant-7", "starter")

    preview = get_plan_change_preview(db, "tenant-7", "pro")

    print(f"Current: {preview['current_plan']}")
    print(f"Target: {preview['target_plan']}")
    print(f"Change type: {preview['change_type']}")
    print(f"Applied: {preview['applied']}")
    print(f"Net charge: ${preview['proration']['net']}")

    sub = db.query(Subscription).filter_by(tenant_id="tenant-7").first()
    assert sub.plan == "starter"
    print("✓ Preview doesn't modify subscription")


def test_all_transitions():
    print("\n=== Test: All plan transitions ===")
    transitions = [
        ("starter", "pro", "upgrade"),
        ("pro", "enterprise", "upgrade"),
        ("enterprise", "pro", "downgrade"),
        ("pro", "starter", "downgrade"),
    ]

    for from_plan, to_plan, expected_type in transitions:
        db = setup_db()
        create_test_subscription(db, f"tenant-{from_plan}-{to_plan}", from_plan)

        preview = get_plan_change_preview(db, f"tenant-{from_plan}-{to_plan}", to_plan)
        assert preview["change_type"] == expected_type
        print(f"✓ {from_plan} -> {to_plan}: {expected_type}")


if __name__ == "__main__":
    print("Testing Plan Changes Module")
    print("=" * 50)

    try:
        test_proration()
        test_upgrade_starter_to_pro()
        test_upgrade_pro_to_enterprise()
        test_downgrade_pro_to_starter()
        test_downgrade_enterprise_to_pro()
        test_invalid_same_plan()
        test_invalid_upgrade_as_downgrade()
        test_preview()
        test_all_transitions()

        print("\n" + "=" * 50)
        print("✓ ALL TESTS PASSED")
        print("=" * 50)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
