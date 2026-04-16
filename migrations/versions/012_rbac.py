"""Add RBAC tables for role-based access control

Revision ID: 012_rbac
Revises: 010_gdpr
Create Date: 2026-04-16 10:58:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "012_rbac"
down_revision = "010_gdpr"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("permissions", JSONB, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_role_name"),
    )

    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("invited_by", sa.String(length=255), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user_membership"),
    )

    op.create_table(
        "team_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("invited_by", sa.String(length=255), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("token", name="uq_invite_token"),
    )

    op.create_index("idx_team_members_tenant_id", "team_members", ["tenant_id"])
    op.create_index("idx_team_members_user_id", "team_members", ["user_id"])
    op.create_index("idx_team_invites_tenant_id", "team_invites", ["tenant_id"])
    op.create_index("idx_team_invites_email", "team_invites", ["email"])
    op.create_index("idx_team_invites_token", "team_invites", ["token"])

    op.execute("ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE team_members FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE team_invites ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE team_invites FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY team_members_tenant_isolation ON team_members
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE));
    """)

    op.execute("""
        CREATE POLICY team_invites_tenant_isolation ON team_invites
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE));
    """)

    op.execute("""
        INSERT INTO roles (name, permissions) VALUES
        ('admin', '["manage_team", "manage_billing", "create_post", "edit_post", "delete_post", "view_analytics", "manage_platforms", "manage_api_keys", "view_audit_logs"]'),
        ('manager', '["create_post", "edit_post", "delete_post", "view_analytics", "manage_platforms"]'),
        ('viewer', '["view_analytics"]');
    """)


def downgrade() -> None:
    op.drop_table("team_invites")
    op.drop_table("team_members")
    op.drop_table("roles")
