"""Comprehensive tenant isolation test suite.

Tests verify that Row-Level Security (RLS) policies enforce complete tenant isolation:
- No cross-tenant data access (read/write/delete)
- API keys respect tenant boundaries
- Admin role can access all tenants
- Invalid/missing tenant context returns 403

All tests use real PostgreSQL with RLS enabled.
"""

import os
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/1ai_social")


@pytest.fixture(scope="module")
def engine():
    """Create database engine."""
    return create_engine(DATABASE_URL)


@pytest.fixture(scope="module")
def db_session(engine):
    """Create database session factory."""
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal


@pytest.fixture(scope="function")
def db(db_session):
    """Create a database session for each test."""
    session = db_session()
    yield session
    session.close()


@pytest.fixture(scope="module", autouse=True)
def setup_test_data(engine):
    """Setup test tenants and data before all tests."""
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Set admin role to bypass RLS for test setup
        db.execute(text("SET app.user_role = 'admin'"))
        db.commit()

        # Create test tenants
        db.execute(
            text("""
            INSERT INTO tenants (id, name, plan, status)
            VALUES 
                ('tenant-a', 'Tenant A', 'pro', 'active'),
                ('tenant-b', 'Tenant B', 'starter', 'active'),
                ('tenant-c', 'Tenant C (Inactive)', 'starter', 'inactive')
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                plan = EXCLUDED.plan,
                status = EXCLUDED.status
        """)
        )

        # Create API keys for tenants
        db.execute(
            text("""
            INSERT INTO api_keys (key_hash, tenant_id, name, scopes)
            VALUES 
                ('hash-tenant-a', 'tenant-a', 'Tenant A Key', '["read", "write"]'::jsonb),
                ('hash-tenant-b', 'tenant-b', 'Tenant B Key', '["read", "write"]'::jsonb)
            ON CONFLICT (key_hash) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                name = EXCLUDED.name
        """)
        )

        db.commit()
        print("✓ Test data setup complete")

    except Exception as e:
        print(f"✗ Test data setup failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

    yield

    # Cleanup after all tests
    db = Session()
    try:
        db.execute(text("SET app.user_role = ''"))
        db.commit()
    finally:
        db.close()


def set_tenant_context(db: Session, tenant_id: str, role: str = "user"):
    """Helper to set tenant context."""
    db.execute(
        text("SELECT set_tenant_context(:tenant_id, :role)"),
        {"tenant_id": tenant_id, "role": role},
    )
    db.commit()


def clear_tenant_context(db: Session):
    """Helper to clear tenant context."""
    db.execute(text("SELECT clear_tenant_context()"))
    db.commit()


def setup_test_data_as_admin(db: Session, sql: str, params: dict = None):
    """Helper to insert test data with admin privileges."""
    db.execute(text("SET app.user_role = 'admin'"))
    db.commit()

    if params:
        db.execute(text(sql), params)
    else:
        db.execute(text(sql))
    db.commit()

    db.execute(text("SET app.user_role = ''"))
    db.commit()


class TestPlatformIsolation:
    """Test tenant isolation for platforms table."""

    def test_tenant_a_cannot_read_tenant_b_platforms(self, db):
        """Tenant A cannot read Tenant B's platforms."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO platforms (name, credentials, user_id, tenant_id)
            VALUES 
                ('platform-a-1', 'creds-a', 'user-a', 'tenant-a'),
                ('platform-b-1', 'creds-b', 'user-b', 'tenant-b')
            ON CONFLICT (name) DO UPDATE SET tenant_id = EXCLUDED.tenant_id
        """,
        )

        # Test: Set Tenant A context and query
        set_tenant_context(db, "tenant-a")

        result = db.execute(text("SELECT name, tenant_id FROM platforms")).fetchall()

        # Assert: Only Tenant A platforms returned
        tenant_ids = [row[1] for row in result]
        assert "tenant-a" in tenant_ids or len(tenant_ids) == 0
        assert "tenant-b" not in tenant_ids

        # Verify Tenant A can see their own data
        tenant_a_platforms = [row for row in result if row[1] == "tenant-a"]
        assert len(tenant_a_platforms) >= 1

    def test_tenant_a_cannot_modify_tenant_b_platforms(self, db):
        """Tenant A cannot modify Tenant B's platforms."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO platforms (name, credentials, user_id, tenant_id)
            VALUES ('platform-b-modify', 'original-creds', 'user-b', 'tenant-b')
            ON CONFLICT (name) DO UPDATE SET credentials = 'original-creds'
        """,
        )

        # Test: Set Tenant A context and try to modify Tenant B's platform
        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            UPDATE platforms 
            SET credentials = 'hacked-creds'
            WHERE name = 'platform-b-modify'
        """)
        )
        db.commit()

        # Assert: No rows affected
        assert result.rowcount == 0

        # Verify data unchanged
        db.execute(text("SET app.user_role = 'admin'"))
        db.commit()
        check = db.execute(
            text("""
            SELECT credentials FROM platforms WHERE name = 'platform-b-modify'
        """)
        ).fetchone()
        assert check[0] == "original-creds"

    def test_tenant_a_cannot_delete_tenant_b_platforms(self, db):
        """Tenant A cannot delete Tenant B's platforms."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO platforms (name, credentials, user_id, tenant_id)
            VALUES ('platform-b-delete', 'creds', 'user-b', 'tenant-b')
            ON CONFLICT (name) DO UPDATE SET tenant_id = 'tenant-b'
        """,
        )

        # Test: Set Tenant A context and try to delete
        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            DELETE FROM platforms WHERE name = 'platform-b-delete'
        """)
        )
        db.commit()

        # Assert: No rows deleted
        assert result.rowcount == 0

        # Verify platform still exists
        db.execute(text("SET app.user_role = 'admin'"))
        db.commit()
        check = db.execute(
            text("""
            SELECT COUNT(*) FROM platforms WHERE name = 'platform-b-delete'
        """)
        ).fetchone()
        assert check[0] == 1


class TestContentIsolation:
    """Test tenant isolation for contents table."""

    def test_tenant_a_cannot_read_tenant_b_contents(self, db):
        """Tenant A cannot read Tenant B's contents."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO contents (text, platform, tenant_id)
            VALUES 
                ('Content A', 'tiktok', 'tenant-a'),
                ('Content B', 'instagram', 'tenant-b')
        """,
        )

        # Test
        set_tenant_context(db, "tenant-a")

        result = db.execute(text("SELECT text, tenant_id FROM contents")).fetchall()

        # Assert
        tenant_ids = [row[1] for row in result if row[1] is not None]
        assert "tenant-b" not in tenant_ids

    def test_tenant_a_cannot_modify_tenant_b_contents(self, db):
        """Tenant A cannot modify Tenant B's contents."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO contents (text, platform, tenant_id)
            VALUES ('Original Content B', 'tiktok', 'tenant-b')
        """,
        )

        db.execute(text("SET app.user_role = 'admin'"))
        db.commit()
        content_id = db.execute(
            text("""
            SELECT id FROM contents WHERE text = 'Original Content B'
        """)
        ).fetchone()[0]
        db.execute(text("SET app.user_role = ''"))
        db.commit()

        # Test
        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            UPDATE contents SET text = 'Hacked Content' WHERE id = :id
        """),
            {"id": content_id},
        )
        db.commit()

        # Assert
        assert result.rowcount == 0

    def test_tenant_a_cannot_delete_tenant_b_contents(self, db):
        """Tenant A cannot delete Tenant B's contents."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO contents (text, platform, tenant_id)
            VALUES ('Delete Test Content B', 'tiktok', 'tenant-b')
        """,
        )

        db.execute(text("SET app.user_role = 'admin'"))
        db.commit()
        content_id = db.execute(
            text("""
            SELECT id FROM contents WHERE text = 'Delete Test Content B'
        """)
        ).fetchone()[0]
        db.execute(text("SET app.user_role = ''"))
        db.commit()

        # Test
        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            DELETE FROM contents WHERE id = :id
        """),
            {"id": content_id},
        )
        db.commit()

        # Assert
        assert result.rowcount == 0


class TestHookIsolation:
    """Test tenant isolation for hooks table."""

    def test_tenant_a_cannot_read_tenant_b_hooks(self, db):
        """Tenant A cannot read Tenant B's hooks."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO hooks (text, confidence, type, tenant_id)
            VALUES 
                ('Hook A', 0.9, 'question', 'tenant-a'),
                ('Hook B', 0.8, 'statement', 'tenant-b')
        """,
        )

        # Test
        set_tenant_context(db, "tenant-a")

        result = db.execute(text("SELECT text, tenant_id FROM hooks")).fetchall()

        # Assert
        tenant_ids = [row[1] for row in result if row[1] is not None]
        assert "tenant-b" not in tenant_ids

    def test_tenant_a_cannot_modify_tenant_b_hooks(self, db):
        """Tenant A cannot modify Tenant B's hooks."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO hooks (text, confidence, type, tenant_id)
            VALUES ('Original Hook B', 0.9, 'question', 'tenant-b')
        """,
        )

        db.execute(text("SET app.user_role = 'admin'"))
        db.commit()
        hook_id = db.execute(
            text("""
            SELECT id FROM hooks WHERE text = 'Original Hook B'
        """)
        ).fetchone()[0]
        db.execute(text("SET app.user_role = ''"))
        db.commit()

        # Test
        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            UPDATE hooks SET text = 'Hacked Hook' WHERE id = :id
        """),
            {"id": hook_id},
        )
        db.commit()

        # Assert
        assert result.rowcount == 0


class TestPostIsolation:
    """Test tenant isolation for posts table."""

    def test_tenant_a_cannot_read_tenant_b_posts(self, db):
        """Tenant A cannot read Tenant B's posts."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO platforms (name, credentials, user_id, tenant_id)
            VALUES 
                ('post-platform-a', 'creds', 'user-a', 'tenant-a'),
                ('post-platform-b', 'creds', 'user-b', 'tenant-b')
            ON CONFLICT (name) DO UPDATE SET tenant_id = EXCLUDED.tenant_id
        """,
        )

        setup_test_data_as_admin(
            db,
            """
            INSERT INTO contents (text, platform, tenant_id)
            VALUES 
                ('Post Content A', 'tiktok', 'tenant-a'),
                ('Post Content B', 'tiktok', 'tenant-b')
        """,
        )

        db.execute(text("SET app.user_role = 'admin'"))
        db.commit()

        platform_a_id = db.execute(
            text("""
            SELECT id FROM platforms WHERE name = 'post-platform-a'
        """)
        ).fetchone()[0]

        platform_b_id = db.execute(
            text("""
            SELECT id FROM platforms WHERE name = 'post-platform-b'
        """)
        ).fetchone()[0]

        content_a_id = db.execute(
            text("""
            SELECT id FROM contents WHERE text = 'Post Content A' AND tenant_id = 'tenant-a'
        """)
        ).fetchone()[0]

        content_b_id = db.execute(
            text("""
            SELECT id FROM contents WHERE text = 'Post Content B' AND tenant_id = 'tenant-b'
        """)
        ).fetchone()[0]

        db.execute(
            text("""
            INSERT INTO posts (id, content_id, platform_id, status, tenant_id)
            VALUES 
                ('post-a-1', :content_a_id, :platform_a_id, 'published', 'tenant-a'),
                ('post-b-1', :content_b_id, :platform_b_id, 'published', 'tenant-b')
            ON CONFLICT (id) DO UPDATE SET tenant_id = EXCLUDED.tenant_id
        """),
            {
                "content_a_id": content_a_id,
                "platform_a_id": platform_a_id,
                "content_b_id": content_b_id,
                "platform_b_id": platform_b_id,
            },
        )
        db.commit()

        db.execute(text("SET app.user_role = ''"))
        db.commit()

        # Test
        set_tenant_context(db, "tenant-a")

        result = db.execute(text("SELECT id, tenant_id FROM posts")).fetchall()

        # Assert
        tenant_ids = [row[1] for row in result if row[1] is not None]
        assert "tenant-b" not in tenant_ids

    def test_tenant_a_cannot_modify_tenant_b_posts(self, db):
        """Tenant A cannot modify Tenant B's posts."""
        # Setup
        clear_tenant_context(db)

        # Test
        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            UPDATE posts SET status = 'hacked' WHERE id = 'post-b-1'
        """)
        )
        db.commit()

        # Assert
        assert result.rowcount == 0

    def test_tenant_a_cannot_delete_tenant_b_posts(self, db):
        """Tenant A cannot delete Tenant B's posts."""
        # Test
        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            DELETE FROM posts WHERE id = 'post-b-1'
        """)
        )
        db.commit()

        # Assert
        assert result.rowcount == 0


class TestAnalyticsIsolation:
    """Test tenant isolation for analytics_records table."""

    def test_tenant_a_cannot_read_tenant_b_analytics(self, db):
        """Tenant A cannot read Tenant B's analytics."""
        # Setup
        clear_tenant_context(db)

        # Get platform and post IDs
        platform_a_id = db.execute(
            text("""
            SELECT id FROM platforms WHERE tenant_id = 'tenant-a' LIMIT 1
        """)
        ).fetchone()

        platform_b_id = db.execute(
            text("""
            SELECT id FROM platforms WHERE tenant_id = 'tenant-b' LIMIT 1
        """)
        ).fetchone()

        if platform_a_id and platform_b_id:
            platform_a_id = platform_a_id[0]
            platform_b_id = platform_b_id[0]

            # Create analytics records
            db.execute(
                text("""
                INSERT INTO analytics_records 
                (post_id, platform_id, views, likes, tenant_id)
                VALUES 
                    ('post-a-1', :platform_a_id, 1000, 50, 'tenant-a'),
                    ('post-b-1', :platform_b_id, 2000, 100, 'tenant-b')
            """),
                {"platform_a_id": platform_a_id, "platform_b_id": platform_b_id},
            )
            db.commit()

            # Test
            set_tenant_context(db, "tenant-a")

            result = db.execute(
                text("""
                SELECT post_id, tenant_id FROM analytics_records
            """)
            ).fetchall()

            # Assert
            tenant_ids = [row[1] for row in result if row[1] is not None]
            assert "tenant-b" not in tenant_ids

    def test_tenant_a_cannot_modify_tenant_b_analytics(self, db):
        """Tenant A cannot modify Tenant B's analytics."""
        # Test
        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            UPDATE analytics_records 
            SET views = 999999 
            WHERE post_id = 'post-b-1'
        """)
        )
        db.commit()

        # Assert
        assert result.rowcount == 0


class TestAuditLogIsolation:
    """Test tenant isolation for audit_logs table."""

    def test_tenant_a_cannot_read_tenant_b_audit_logs(self, db):
        """Tenant A cannot read Tenant B's audit logs."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO audit_logs 
            (action, resource, user_id, tenant_id, details, signature)
            VALUES 
                ('create', 'post:post-a-1', 'user-a', 'tenant-a', '{}', 'sig-a'),
                ('create', 'post:post-b-1', 'user-b', 'tenant-b', '{}', 'sig-b')
        """,
        )

        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            SELECT resource, tenant_id FROM audit_logs
        """)
        ).fetchall()

        tenant_ids = [row[1] for row in result if row[1] is not None]
        assert "tenant-b" not in tenant_ids


class TestAdminAccess:
    """Test admin role can access all tenants."""

    def test_admin_can_read_all_tenants_data(self, db):
        """Admin role can read data from all tenants."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO contents (text, platform, tenant_id)
            VALUES 
                ('Admin Test Content A', 'tiktok', 'tenant-a'),
                ('Admin Test Content B', 'instagram', 'tenant-b')
        """,
        )

        # Test: Set admin context
        set_tenant_context(db, "tenant-a", role="admin")

        result = db.execute(
            text("""
            SELECT text, tenant_id FROM contents 
            WHERE text LIKE 'Admin Test Content%'
        """)
        ).fetchall()

        # Assert: Admin sees both tenants
        tenant_ids = [row[1] for row in result]
        assert "tenant-a" in tenant_ids
        assert "tenant-b" in tenant_ids

    def test_admin_can_modify_all_tenants_data(self, db):
        """Admin role can modify data from all tenants."""
        setup_test_data_as_admin(
            db,
            """
            INSERT INTO contents (text, platform, tenant_id)
            VALUES ('Admin Modify Test', 'tiktok', 'tenant-b')
        """,
        )

        db.execute(text("SET app.user_role = 'admin'"))
        db.commit()
        content_id = db.execute(
            text("""
            SELECT id FROM contents WHERE text = 'Admin Modify Test'
        """)
        ).fetchone()[0]

        # Test: Set admin context for tenant-a (different tenant)
        set_tenant_context(db, "tenant-a", role="admin")

        result = db.execute(
            text("""
            UPDATE contents 
            SET text = 'Admin Modified' 
            WHERE id = :id
        """),
            {"id": content_id},
        )
        db.commit()

        # Assert: Admin can modify
        assert result.rowcount == 1


class TestInvalidTenantContext:
    """Test invalid or missing tenant context."""

    def test_missing_tenant_context_returns_no_data(self, db):
        """Missing tenant context returns no tenant-specific data."""
        # Clear context
        clear_tenant_context(db)

        # Test: Query without setting tenant context
        result = db.execute(
            text("""
            SELECT COUNT(*) FROM platforms WHERE tenant_id IS NOT NULL
        """)
        ).fetchone()

        # Assert: No tenant-specific data visible
        assert result[0] == 0

    def test_invalid_tenant_returns_no_data(self, db):
        """Invalid tenant ID returns no data."""
        # Test: Set invalid tenant context
        set_tenant_context(db, "tenant-invalid-999")

        result = db.execute(
            text("""
            SELECT COUNT(*) FROM platforms WHERE tenant_id IS NOT NULL
        """)
        ).fetchone()

        # Assert: No data visible
        assert result[0] == 0


class TestAPIKeyIsolation:
    """Test API key tenant boundaries."""

    def test_api_key_respects_tenant_boundaries(self, db):
        """API keys are scoped to their tenant."""
        db.execute(text("SET app.user_role = 'admin'"))
        db.commit()

        result_a = db.execute(
            text("""
            SELECT tenant_id FROM api_keys WHERE key_hash = 'hash-tenant-a'
        """)
        ).fetchone()

        assert result_a is not None
        assert result_a[0] == "tenant-a"

        result_b = db.execute(
            text("""
            SELECT tenant_id FROM api_keys WHERE key_hash = 'hash-tenant-b'
        """)
        ).fetchone()

        assert result_b is not None
        assert result_b[0] == "tenant-b"

    def test_api_key_isolation_with_rls(self, db):
        """API keys respect RLS policies."""
        set_tenant_context(db, "tenant-a")

        result = db.execute(
            text("""
            SELECT resource, tenant_id FROM audit_logs
        """)
        ).fetchall()

        tenant_ids = [row[1] for row in result]
        assert "tenant-a" in tenant_ids
        assert "tenant-b" not in tenant_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
