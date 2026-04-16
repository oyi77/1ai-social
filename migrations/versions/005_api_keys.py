"""Add API keys table with tenant scoping

Revision ID: 005_api_keys
Revises: 004_rls_policies
Create Date: 2026-04-16 09:58:00.884000

This migration creates the api_keys table for secure API key management
with tenant isolation. API keys are scoped to tenants and cannot access
other tenants' data due to RLS policies.

Table: api_keys
- id (PK)
- tenant_id (FK to tenants.id, NOT NULL)
- key_hash (SHA-256 hash of the API key)
- scopes (JSONB array: ['read', 'write', 'admin'])
- name (VARCHAR, human-readable key name)
- expires_at (TIMESTAMP, optional expiration)
- created_at (TIMESTAMP)

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005_api_keys"
down_revision = "004_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )

    op.create_index("idx_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("idx_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("idx_api_keys_expires_at", "api_keys", ["expires_at"])

    op.execute("ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE api_keys FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY tenant_isolation_policy ON api_keys
        FOR ALL
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::VARCHAR
        );
    """)

    op.execute("""
        CREATE POLICY admin_access_policy ON api_keys
        FOR ALL
        USING (
            current_setting('app.user_role', true) = 'admin'
        );
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS admin_access_policy ON api_keys;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON api_keys;")
    op.execute("ALTER TABLE api_keys DISABLE ROW LEVEL SECURITY;")

    op.drop_index("idx_api_keys_expires_at", table_name="api_keys")
    op.drop_index("idx_api_keys_tenant_id", table_name="api_keys")
    op.drop_index("idx_api_keys_key_hash", table_name="api_keys")

    op.drop_table("api_keys")
