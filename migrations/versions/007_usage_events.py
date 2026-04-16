"""Add usage_events table for metering and billing

Revision ID: 007_usage_tracking
Revises: 006_subscriptions
Create Date: 2026-04-16 10:33:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007_usage_tracking"
down_revision = "006_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )

    # Indexes for efficient querying
    op.create_index("idx_usage_events_tenant_id", "usage_events", ["tenant_id"])
    op.create_index("idx_usage_events_event_type", "usage_events", ["event_type"])
    op.create_index("idx_usage_events_created_at", "usage_events", ["created_at"])

    # Composite index for aggregation queries
    op.create_index(
        "idx_usage_events_tenant_type_created",
        "usage_events",
        ["tenant_id", "event_type", "created_at"],
    )

    # Enable RLS
    op.execute("ALTER TABLE usage_events ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE usage_events FORCE ROW LEVEL SECURITY;")

    # Tenant isolation policy
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON usage_events
        FOR ALL
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::VARCHAR
        );
    """)

    # Admin access policy
    op.execute("""
        CREATE POLICY admin_access_policy ON usage_events
        FOR ALL
        USING (
            current_setting('app.user_role', true) = 'admin'
        );
    """)

    # Add constraint to validate event_type
    op.execute("""
        ALTER TABLE usage_events
        ADD CONSTRAINT valid_event_type
        CHECK (event_type IN ('posts_published', 'api_calls', 'connected_accounts'));
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS admin_access_policy ON usage_events;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON usage_events;")
    op.execute("ALTER TABLE usage_events DISABLE ROW LEVEL SECURITY;")

    op.drop_index("idx_usage_events_tenant_type_created", table_name="usage_events")
    op.drop_index("idx_usage_events_created_at", table_name="usage_events")
    op.drop_index("idx_usage_events_event_type", table_name="usage_events")
    op.drop_index("idx_usage_events_tenant_id", table_name="usage_events")

    op.drop_table("usage_events")
