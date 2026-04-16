"""Test RBAC permission enforcement."""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(__file__))

import importlib

rbac = importlib.import_module("1ai_social.auth.rbac")
check_permission = rbac.check_permission
invite_team_member = rbac.invite_team_member
accept_invitation = rbac.accept_invitation
remove_team_member = rbac.remove_team_member
list_team_members = rbac.list_team_members
get_user_role = rbac.get_user_role
PermissionDeniedError = rbac.PermissionDeniedError

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/1ai_social"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def setup_test_data(db):
    """Create test tenant and users."""
    db.execute(
        text("""
            INSERT INTO tenants (id, name, status, created_at)
            VALUES ('test-tenant-1', 'Test Tenant', 'active', NOW())
            ON CONFLICT (id) DO NOTHING
        """)
    )

    db.execute(text("SET app.current_tenant_id = 'test-tenant-1'"))

    admin_role_id = db.execute(
        text("SELECT id FROM roles WHERE name = 'admin'")
    ).scalar()

    db.execute(
        text("""
            INSERT INTO team_members (tenant_id, user_id, role_id, accepted_at)
            VALUES ('test-tenant-1', 'admin-user', :role_id, NOW())
            ON CONFLICT (tenant_id, user_id) DO NOTHING
        """),
        {"role_id": admin_role_id},
    )

    viewer_role_id = db.execute(
        text("SELECT id FROM roles WHERE name = 'viewer'")
    ).scalar()

    db.execute(
        text("""
            INSERT INTO team_members (tenant_id, user_id, role_id, accepted_at)
            VALUES ('test-tenant-1', 'viewer-user', :role_id, NOW())
            ON CONFLICT (tenant_id, user_id) DO NOTHING
        """),
        {"role_id": viewer_role_id},
    )

    db.commit()
    print("✓ Test data created")


def test_permission_checks(db):
    """Test permission checking."""
    print("\n=== Testing Permission Checks ===")

    admin_can_manage = check_permission(
        "admin-user", "test-tenant-1", "manage_team", db
    )
    print(f"✓ Admin can manage_team: {admin_can_manage}")
    assert admin_can_manage, "Admin should have manage_team permission"

    admin_can_create = check_permission(
        "admin-user", "test-tenant-1", "create_post", db
    )
    print(f"✓ Admin can create_post: {admin_can_create}")
    assert admin_can_create, "Admin should have create_post permission"

    viewer_can_view = check_permission(
        "viewer-user", "test-tenant-1", "view_analytics", db
    )
    print(f"✓ Viewer can view_analytics: {viewer_can_view}")
    assert viewer_can_view, "Viewer should have view_analytics permission"

    viewer_cannot_create = check_permission(
        "viewer-user", "test-tenant-1", "create_post", db
    )
    print(f"✓ Viewer cannot create_post: {not viewer_cannot_create}")
    assert not viewer_cannot_create, "Viewer should NOT have create_post permission"

    viewer_cannot_manage = check_permission(
        "viewer-user", "test-tenant-1", "manage_team", db
    )
    print(f"✓ Viewer cannot manage_team: {not viewer_cannot_manage}")
    assert not viewer_cannot_manage, "Viewer should NOT have manage_team permission"


def test_team_invites(db):
    """Test team invitation flow."""
    print("\n=== Testing Team Invites ===")

    invite = invite_team_member(
        tenant_id="test-tenant-1",
        email="newuser@example.com",
        role_name="manager",
        invited_by="admin-user",
        db=db,
    )

    print(f"✓ Invite created: {invite['email']} as {invite['role']}")
    print(f"  Token: {invite['token'][:20]}...")
    print(f"  Expires: {invite['expires_at']}")

    result = accept_invitation(
        token=invite["token"],
        user_id="new-manager-user",
        db=db,
    )

    print(f"✓ Invite accepted by user: {result['role']}")
    assert result["role"] == "manager", "Should be manager role"

    manager_can_create = check_permission(
        "new-manager-user", "test-tenant-1", "create_post", db
    )
    print(f"✓ New manager can create_post: {manager_can_create}")
    assert manager_can_create, "Manager should have create_post permission"

    manager_cannot_manage = check_permission(
        "new-manager-user", "test-tenant-1", "manage_team", db
    )
    print(f"✓ New manager cannot manage_team: {not manager_cannot_manage}")
    assert not manager_cannot_manage, "Manager should NOT have manage_team permission"


def test_team_listing(db):
    """Test listing team members."""
    print("\n=== Testing Team Listing ===")

    members = list_team_members("test-tenant-1", db)
    print(f"✓ Found {len(members)} team members:")

    for member in members:
        print(f"  - {member['user_id']}: {member['role']}")

    assert len(members) >= 3, "Should have at least 3 members"


def test_role_retrieval(db):
    """Test getting user roles."""
    print("\n=== Testing Role Retrieval ===")

    admin_role = get_user_role("admin-user", "test-tenant-1", db)
    print(f"✓ Admin user role: {admin_role}")
    assert admin_role == "admin", "Should be admin"

    viewer_role = get_user_role("viewer-user", "test-tenant-1", db)
    print(f"✓ Viewer user role: {viewer_role}")
    assert viewer_role == "viewer", "Should be viewer"

    manager_role = get_user_role("new-manager-user", "test-tenant-1", db)
    print(f"✓ Manager user role: {manager_role}")
    assert manager_role == "manager", "Should be manager"


def test_remove_member(db):
    """Test removing team member."""
    print("\n=== Testing Member Removal ===")

    remove_team_member(
        tenant_id="test-tenant-1",
        user_id="viewer-user",
        removed_by="admin-user",
        db=db,
    )

    print("✓ Viewer user removed")

    viewer_role = get_user_role("viewer-user", "test-tenant-1", db)
    print(f"✓ Viewer role after removal: {viewer_role}")
    assert viewer_role is None, "Viewer should have no role after removal"


def main():
    """Run all RBAC tests."""
    db = SessionLocal()

    try:
        print("Starting RBAC tests...")

        setup_test_data(db)
        test_permission_checks(db)
        test_team_invites(db)
        test_team_listing(db)
        test_role_retrieval(db)
        test_remove_member(db)

        print("\n" + "=" * 50)
        print("✓ ALL RBAC TESTS PASSED")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
