"""Test API key tenant isolation with database"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

api_keys = importlib.import_module("1ai_social.api_keys")
create_api_key = api_keys.create_api_key
validate_api_key = api_keys.validate_api_key
set_tenant_context_from_key = api_keys.set_tenant_context_from_key
InvalidAPIKeyError = api_keys.InvalidAPIKeyError
ExpiredAPIKeyError = api_keys.ExpiredAPIKeyError
InsufficientScopeError = api_keys.InsufficientScopeError


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/1ai_social"
)


def setup_test_tenants(session):
    """Create test tenants"""
    session.execute(text("SELECT set_config('app.user_role', 'admin', false)"))
    session.execute(
        text("""
        INSERT INTO tenants (id, name, plan, status)
        VALUES 
            ('tenant-alpha', 'Alpha Corp', 'enterprise', 'active'),
            ('tenant-beta', 'Beta Inc', 'starter', 'active')
        ON CONFLICT (id) DO NOTHING
    """)
    )
    session.commit()
    session.execute(text("SELECT set_config('app.user_role', '', false)"))


def test_cross_tenant_access_blocked():
    """Test that API keys cannot access other tenants' data"""
    print("Testing cross-tenant access blocking...")

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        setup_test_tenants(session)

        key_alpha = create_api_key(
            session,
            tenant_id="tenant-alpha",
            scopes=["read", "write"],
            name="Alpha Key",
        )

        key_beta = create_api_key(
            session,
            tenant_id="tenant-beta",
            scopes=["read", "write"],
            name="Beta Key",
        )

        print(f"✓ Created Alpha key: {key_alpha['api_key'][:40]}...")
        print(f"✓ Created Beta key: {key_beta['api_key'][:40]}...")

        session.execute(text("SET app.current_tenant_id = ''"))
        session.execute(text("SET app.user_role = ''"))
        session.commit()

        set_tenant_context_from_key(session, key_alpha["api_key"])
        session.execute(text("SET app.user_role = ''"))

        result = session.execute(
            text("""
            SELECT COUNT(*) as count FROM api_keys
        """)
        ).fetchone()

        print(f"✓ Alpha can see {result.count} key(s) (should be 1 - only their own)")
        assert result.count == 1, f"Alpha should only see 1 key, saw {result.count}"

        session.execute(text("SET app.current_tenant_id = ''"))
        session.execute(text("SET app.user_role = ''"))

        set_tenant_context_from_key(session, key_beta["api_key"])
        session.execute(text("SET app.user_role = ''"))

        result = session.execute(
            text("""
            SELECT COUNT(*) as count FROM api_keys
        """)
        ).fetchone()

        print(f"✓ Beta can see {result.count} key(s) (should be 1 - only their own)")
        assert result.count == 1, f"Beta should only see 1 key, saw {result.count}"

        print("✓ Cross-tenant access successfully blocked by RLS\n")

    finally:
        session.execute(text("SET app.current_tenant_id = ''"))
        session.execute(text("SET app.user_role = 'admin'"))
        session.execute(
            text(
                "DELETE FROM api_keys WHERE tenant_id IN ('tenant-alpha', 'tenant-beta')"
            )
        )
        session.commit()
        session.close()


def test_scope_enforcement():
    """Test that API key scopes are enforced"""
    print("Testing scope enforcement...")

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        setup_test_tenants(session)

        read_only_key = create_api_key(
            session, tenant_id="tenant-alpha", scopes=["read"], name="Read Only Key"
        )

        print(f"✓ Created read-only key: {read_only_key['api_key'][:40]}...")

        key_data = validate_api_key(
            session, read_only_key["api_key"], required_scopes=["read"]
        )
        print(f"✓ Key validated with 'read' scope")

        try:
            validate_api_key(
                session, read_only_key["api_key"], required_scopes=["write"]
            )
            assert False, "Should have raised InsufficientScopeError"
        except InsufficientScopeError as e:
            print(f"✓ Key correctly rejected for 'write' scope: {e}")

        try:
            validate_api_key(
                session, read_only_key["api_key"], required_scopes=["admin"]
            )
            assert False, "Should have raised InsufficientScopeError"
        except InsufficientScopeError as e:
            print(f"✓ Key correctly rejected for 'admin' scope: {e}")

        print("✓ Scope enforcement working correctly\n")

    finally:
        session.execute(text("SELECT clear_tenant_context()"))
        session.execute(text("DELETE FROM api_keys WHERE tenant_id = 'tenant-alpha'"))
        session.commit()
        session.close()


def test_invalid_key_rejected():
    """Test that invalid keys are rejected"""
    print("Testing invalid key rejection...")

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        fake_key = "sk_live_fakekeyfakekeyfakekey_abc123"

        try:
            validate_api_key(session, fake_key)
            assert False, "Should have raised InvalidAPIKeyError"
        except InvalidAPIKeyError as e:
            print(f"✓ Invalid key rejected: {e}")

        malformed_key = "not_a_valid_key"

        try:
            validate_api_key(session, malformed_key)
            assert False, "Should have raised InvalidAPIKeyError"
        except InvalidAPIKeyError as e:
            print(f"✓ Malformed key rejected: {e}")

        print("✓ Invalid key rejection working correctly\n")

    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("API Key Tenant Isolation Tests")
    print("=" * 60 + "\n")

    try:
        test_cross_tenant_access_blocked()
        test_scope_enforcement()
        test_invalid_key_rejected()

        print("=" * 60)
        print("✓ ALL ISOLATION TESTS PASSED")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
