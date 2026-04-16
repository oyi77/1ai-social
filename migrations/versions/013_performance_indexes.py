"""Add performance indexes for frequently queried columns

Revision ID: 013_performance_indexes
Revises: 012_rbac
Create Date: 2026-04-16 11:18:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "013_performance_indexes"
down_revision = "012_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_platforms_user_id", "platforms", ["user_id"])
    op.create_index("idx_platforms_tenant_id", "platforms", ["tenant_id"])

    op.create_index("idx_contents_platform", "contents", ["platform"])
    op.create_index("idx_contents_tenant_id", "contents", ["tenant_id"])
    op.create_index("idx_contents_created_at", "contents", ["created_at"])

    op.create_index("idx_hooks_content_id", "hooks", ["content_id"])
    op.create_index("idx_hooks_tenant_id", "hooks", ["tenant_id"])

    op.create_index("idx_posts_status", "posts", ["status"])
    op.create_index("idx_posts_scheduled_time", "posts", ["scheduled_time"])
    op.create_index("idx_posts_tenant_id", "posts", ["tenant_id"])
    op.create_index("idx_posts_platform_id", "posts", ["platform_id"])
    op.create_index("idx_posts_status_scheduled", "posts", ["status", "scheduled_time"])

    op.create_index("idx_analytics_post_id", "analytics_records", ["post_id"])
    op.create_index("idx_analytics_platform_id", "analytics_records", ["platform_id"])
    op.create_index("idx_analytics_tenant_id", "analytics_records", ["tenant_id"])
    op.create_index("idx_analytics_recorded_at", "analytics_records", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("idx_analytics_recorded_at", "analytics_records")
    op.drop_index("idx_analytics_tenant_id", "analytics_records")
    op.drop_index("idx_analytics_platform_id", "analytics_records")
    op.drop_index("idx_analytics_post_id", "analytics_records")

    op.drop_index("idx_posts_status_scheduled", "posts")
    op.drop_index("idx_posts_platform_id", "posts")
    op.drop_index("idx_posts_tenant_id", "posts")
    op.drop_index("idx_posts_scheduled_time", "posts")
    op.drop_index("idx_posts_status", "posts")

    op.drop_index("idx_hooks_tenant_id", "hooks")
    op.drop_index("idx_hooks_content_id", "hooks")

    op.drop_index("idx_contents_created_at", "contents")
    op.drop_index("idx_contents_tenant_id", "contents")
    op.drop_index("idx_contents_platform", "contents")

    op.drop_index("idx_platforms_tenant_id", "platforms")
    op.drop_index("idx_platforms_user_id", "platforms")
