"""Add Row-Level Security (RLS) policies for tenant isolation

Revision ID: 004_rls_policies
Revises: 003_add_tenant_id
Create Date: 2026-04-16 09:56:17.898000

This migration implements PostgreSQL Row-Level Security to enforce tenant isolation
at the database level. Each tenant can only access their own data, while admin users
can access all tenants' data.

RLS Policies:
1. tenant_isolation_policy: Restricts access to rows matching current tenant_id
2. admin_access_policy: Allows admin role to bypass tenant restrictions

Usage:
- Set tenant context: SET app.current_tenant_id = 'tenant-uuid';
- Set admin context: SET app.user_role = 'admin';

"""

from alembic import op


revision = "004_rls_policies"
down_revision = "003_add_tenant_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Enable RLS on all tables with tenant_id and create policies for:
    - Tenant isolation (users see only their tenant's data)
    - Admin access (admins see all data)
    """

    # List of tables that require RLS
    tables_with_rls = [
        "platforms",
        "contents",
        "hooks",
        "posts",
        "analytics_records",
        "audit_logs",
    ]

    for table in tables_with_rls:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")

        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            FOR ALL
            USING (
                COALESCE(NULLIF(current_setting('app.user_role', true), ''), 'user') = 'admin'
                OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::VARCHAR
                OR tenant_id IS NULL
            )
            WITH CHECK (
                COALESCE(NULLIF(current_setting('app.user_role', true), ''), 'user') = 'admin'
                OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::VARCHAR
            );
        """)

    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY tenant_access_policy ON tenants
        FOR ALL
        USING (
            COALESCE(NULLIF(current_setting('app.user_role', true), ''), 'user') = 'admin'
            OR id = NULLIF(current_setting('app.current_tenant_id', true), '')::VARCHAR
        )
        WITH CHECK (
            COALESCE(NULLIF(current_setting('app.user_role', true), ''), 'user') = 'admin'
            OR id = NULLIF(current_setting('app.current_tenant_id', true), '')::VARCHAR
        );
    """)

    # Create helper function to set tenant context
    op.execute("""
        CREATE OR REPLACE FUNCTION set_tenant_context(tenant_uuid VARCHAR, user_role VARCHAR DEFAULT NULL)
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.current_tenant_id', tenant_uuid, false);
            IF user_role IS NOT NULL THEN
                PERFORM set_config('app.user_role', user_role, false);
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create helper function to clear tenant context
    op.execute("""
        CREATE OR REPLACE FUNCTION clear_tenant_context()
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.current_tenant_id', '', false);
            PERFORM set_config('app.user_role', '', false);
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    """
    Remove RLS policies and disable RLS on all tables
    """

    op.execute("DROP FUNCTION IF EXISTS clear_tenant_context();")
    op.execute("DROP FUNCTION IF EXISTS set_tenant_context(VARCHAR, VARCHAR);")

    # List of tables that have RLS
    tables_with_rls = [
        "platforms",
        "contents",
        "hooks",
        "posts",
        "analytics_records",
        "audit_logs",
    ]

    for table in tables_with_rls:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS tenant_access_policy ON tenants;")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY;")
