"""Test tenant context middleware functionality."""

import os
import jwt
import importlib
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ["JWT_SECRET_KEY"] = "test-secret-key-12345"
os.environ["DATABASE_URL"] = "postgresql://localhost/1ai_social"

tenant_context_module = importlib.import_module("1ai_social.tenant_context")
TenantContextMiddleware = tenant_context_module.TenantContextMiddleware


def setup_test_data():
    """Setup test tenants and API keys."""
    engine = create_engine(os.getenv("DATABASE_URL"))
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        db.execute(
            text("""
            INSERT INTO tenants (id, name, plan, status)
            VALUES 
                ('tenant-001', 'Test Tenant 1', 'starter', 'active'),
                ('tenant-002', 'Test Tenant 2', 'pro', 'active'),
                ('tenant-003', 'Inactive Tenant', 'starter', 'inactive')
            ON CONFLICT (id) DO NOTHING
        """)
        )

        db.execute(
            text("""
            INSERT INTO api_keys (key, tenant_id, name, is_active)
            VALUES 
                ('test-api-key-001', 'tenant-001', 'Test Key 1', true),
                ('test-api-key-002', 'tenant-002', 'Test Key 2', true),
                ('test-api-key-inactive', 'tenant-001', 'Inactive Key', false)
            ON CONFLICT (key) DO NOTHING
        """)
        )

        db.commit()
        print("✓ Test data setup complete")
    except Exception as e:
        print(f"✗ Test data setup failed: {e}")
        db.rollback()
    finally:
        db.close()


def test_jwt_extraction():
    """Test JWT token extraction."""
    print("\n=== Test 1: JWT Token Extraction ===")

    engine = create_engine(os.getenv("DATABASE_URL"))
    Session = sessionmaker(bind=engine)

    middleware = TenantContextMiddleware(Session)

    payload = {
        "tenant_id": "tenant-001",
        "user_id": "user-123",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    token = jwt.encode(payload, os.getenv("JWT_SECRET_KEY"), algorithm="HS256")

    tenant_id = middleware.extract_tenant_from_jwt(token)

    if tenant_id == "tenant-001":
        print("✓ JWT extraction successful")
    else:
        print(f"✗ JWT extraction failed: got {tenant_id}")


def test_api_key_extraction():
    """Test API key extraction."""
    print("\n=== Test 2: API Key Extraction ===")

    engine = create_engine(os.getenv("DATABASE_URL"))
    Session = sessionmaker(bind=engine)
    db = Session()

    middleware = TenantContextMiddleware(Session)

    try:
        tenant_id = middleware.extract_tenant_from_api_key("test-api-key-001", db)

        if tenant_id == "tenant-001":
            print("✓ API key extraction successful")
        else:
            print(f"✗ API key extraction failed: got {tenant_id}")
    finally:
        db.close()


def test_tenant_validation():
    """Test tenant validation."""
    print("\n=== Test 3: Tenant Validation ===")

    engine = create_engine(os.getenv("DATABASE_URL"))
    Session = sessionmaker(bind=engine)
    db = Session()

    middleware = TenantContextMiddleware(Session)

    try:
        valid = middleware.validate_tenant("tenant-001", db)
        if valid:
            print("✓ Active tenant validation passed")
        else:
            print("✗ Active tenant validation failed")

        invalid = middleware.validate_tenant("tenant-003", db)
        if not invalid:
            print("✓ Inactive tenant validation correctly rejected")
        else:
            print("✗ Inactive tenant validation should have failed")

        nonexistent = middleware.validate_tenant("tenant-999", db)
        if not nonexistent:
            print("✓ Nonexistent tenant validation correctly rejected")
        else:
            print("✗ Nonexistent tenant validation should have failed")
    finally:
        db.close()


def test_set_tenant_context():
    """Test setting PostgreSQL session variables."""
    print("\n=== Test 4: Set Tenant Context ===")

    engine = create_engine(os.getenv("DATABASE_URL"))
    Session = sessionmaker(bind=engine)
    db = Session()

    middleware = TenantContextMiddleware(Session)

    try:
        middleware.set_tenant_context("tenant-001", db, "user")

        result = db.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        ).fetchone()
        tenant_id = result[0] if result else None

        role_result = db.execute(
            text("SELECT current_setting('app.user_role', true)")
        ).fetchone()
        role = role_result[0] if role_result else None

        if tenant_id == "tenant-001" and role == "user":
            print(f"✓ Tenant context set correctly: tenant_id={tenant_id}, role={role}")
        else:
            print(f"✗ Tenant context failed: tenant_id={tenant_id}, role={role}")
    except Exception as e:
        print(f"✗ Set tenant context failed: {e}")
    finally:
        db.close()


def test_expired_jwt():
    """Test expired JWT token rejection."""
    print("\n=== Test 5: Expired JWT Rejection ===")

    engine = create_engine(os.getenv("DATABASE_URL"))
    Session = sessionmaker(bind=engine)

    middleware = TenantContextMiddleware(Session)

    payload = {
        "tenant_id": "tenant-001",
        "user_id": "user-123",
        "exp": datetime.utcnow() - timedelta(hours=1),
    }
    token = jwt.encode(payload, os.getenv("JWT_SECRET_KEY"), algorithm="HS256")

    tenant_id = middleware.extract_tenant_from_jwt(token)

    if tenant_id is None:
        print("✓ Expired JWT correctly rejected")
    else:
        print(f"✗ Expired JWT should have been rejected: got {tenant_id}")


def test_inactive_api_key():
    """Test inactive API key rejection."""
    print("\n=== Test 6: Inactive API Key Rejection ===")

    engine = create_engine(os.getenv("DATABASE_URL"))
    Session = sessionmaker(bind=engine)
    db = Session()

    middleware = TenantContextMiddleware(Session)

    try:
        tenant_id = middleware.extract_tenant_from_api_key("test-api-key-inactive", db)

        if tenant_id is None:
            print("✓ Inactive API key correctly rejected")
        else:
            print(f"✗ Inactive API key should have been rejected: got {tenant_id}")
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting tenant context middleware tests...")
    print("=" * 50)

    setup_test_data()
    test_jwt_extraction()
    test_api_key_extraction()
    test_tenant_validation()
    test_set_tenant_context()
    test_expired_jwt()
    test_inactive_api_key()

    print("\n" + "=" * 50)
    print("Tests complete!")
