"""Add tenants table and foreign key constraints for multi-tenancy

Revision ID: 003_add_tenant_id
Revises: 002_audit_logs
Create Date: 2026-04-16 09:52:42.375000

"""

from alembic import op
import sqlalchemy as sa


revision = "003_add_tenant_id"
down_revision = "002_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "plan", sa.String(length=50), nullable=False, server_default="starter"
        ),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="active"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=True, server_default=sa.text("NOW()")
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add foreign key constraints for tenant_id columns
    # Note: tenant_id columns already exist as nullable from 001_initial_schema

    # platforms.tenant_id -> tenants.id
    op.create_foreign_key(
        "fk_platforms_tenant_id",
        "platforms",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # contents.tenant_id -> tenants.id
    op.create_foreign_key(
        "fk_contents_tenant_id",
        "contents",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # hooks.tenant_id -> tenants.id
    op.create_foreign_key(
        "fk_hooks_tenant_id",
        "hooks",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # posts.tenant_id -> tenants.id
    op.create_foreign_key(
        "fk_posts_tenant_id",
        "posts",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # analytics_records.tenant_id -> tenants.id
    op.create_foreign_key(
        "fk_analytics_records_tenant_id",
        "analytics_records",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # audit_logs.tenant_id -> tenants.id
    op.create_foreign_key(
        "fk_audit_logs_tenant_id",
        "audit_logs",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create indexes for tenant_id columns for better query performance
    op.create_index("idx_platforms_tenant_id", "platforms", ["tenant_id"])
    op.create_index("idx_contents_tenant_id", "contents", ["tenant_id"])
    op.create_index("idx_hooks_tenant_id", "hooks", ["tenant_id"])
    op.create_index("idx_posts_tenant_id", "posts", ["tenant_id"])
    op.create_index(
        "idx_analytics_records_tenant_id", "analytics_records", ["tenant_id"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_analytics_records_tenant_id", table_name="analytics_records")
    op.drop_index("idx_posts_tenant_id", table_name="posts")
    op.drop_index("idx_hooks_tenant_id", table_name="hooks")
    op.drop_index("idx_contents_tenant_id", table_name="contents")
    op.drop_index("idx_platforms_tenant_id", table_name="platforms")

    # Drop foreign key constraints
    op.drop_constraint("fk_audit_logs_tenant_id", "audit_logs", type_="foreignkey")
    op.drop_constraint(
        "fk_analytics_records_tenant_id", "analytics_records", type_="foreignkey"
    )
    op.drop_constraint("fk_posts_tenant_id", "posts", type_="foreignkey")
    op.drop_constraint("fk_hooks_tenant_id", "hooks", type_="foreignkey")
    op.drop_constraint("fk_contents_tenant_id", "contents", type_="foreignkey")
    op.drop_constraint("fk_platforms_tenant_id", "platforms", type_="foreignkey")

    # Drop tenants table
    op.drop_table("tenants")
