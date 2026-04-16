"""Integration test for usage tracking with real database."""

import os
import sys
import importlib
import sqlalchemy as sa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

usage_module = importlib.import_module("1ai_social.billing.usage")
record_usage = usage_module.record_usage
get_current_month_usage = usage_module.get_current_month_usage
check_overage = usage_module.check_overage
VALID_EVENT_TYPES = usage_module.VALID_EVENT_TYPES

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/1ai_social")


def test_usage_tracking_integration():
    """Test usage tracking with real database."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        test_tenant = "test-tenant-usage-001"

        session.execute(sa.text("SET LOCAL app.user_role = 'admin'"))
        session.execute(
            sa.text(
                "INSERT INTO tenants (id, name, created_at) VALUES (:id, :name, NOW()) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": test_tenant, "name": "Test Tenant"},
        )
        session.commit()

        event = record_usage(
            session,
            test_tenant,
            "posts_published",
            quantity=10,
            metadata={"test": "integration"},
        )

        assert event.id is not None
        assert event.tenant_id == test_tenant
        assert event.event_type == "posts_published"
        assert event.quantity == 10

        usage = get_current_month_usage(session, test_tenant)
        print(f"Usage: {usage}")
        assert usage["posts_published"] >= 10

        overage = check_overage(session, test_tenant, "starter")
        assert "has_overage" in overage
        assert "usage" in overage
        assert "limits" in overage

        print("✓ Usage tracking integration test passed")

    finally:
        session.close()


def test_event_type_validation():
    """Test event type validation."""
    assert "posts_published" in VALID_EVENT_TYPES
    assert "api_calls" in VALID_EVENT_TYPES
    assert "connected_accounts" in VALID_EVENT_TYPES
    assert len(VALID_EVENT_TYPES) == 3
    print("✓ Event type validation test passed")


def test_invalid_event_type():
    """Test invalid event type raises error."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        try:
            record_usage(session, "test-tenant", "invalid_type")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Invalid event_type" in str(e)
            print("✓ Invalid event type test passed")
    finally:
        session.close()


def test_invalid_quantity():
    """Test invalid quantity raises error."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        try:
            record_usage(session, "test-tenant", "posts_published", quantity=0)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Quantity must be positive" in str(e)

        try:
            record_usage(session, "test-tenant", "posts_published", quantity=-5)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Quantity must be positive" in str(e)

        print("✓ Invalid quantity test passed")
    finally:
        session.close()


if __name__ == "__main__":
    test_event_type_validation()
    test_invalid_event_type()
    test_invalid_quantity()
    test_usage_tracking_integration()
    print("\n✓ All usage tracking tests passed!")
