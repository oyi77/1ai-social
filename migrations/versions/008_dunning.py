"""Add dunning_events table for payment retry workflow

Revision ID: 008_dunning
Revises: 007_usage_tracking
Create Date: 2026-04-16 10:33:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "008_dunning"
down_revision = "007_usage_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dunning_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"
        ),
    )

    op.create_index("idx_dunning_events_tenant_id", "dunning_events", ["tenant_id"])
    op.create_index(
        "idx_dunning_events_subscription_id", "dunning_events", ["subscription_id"]
    )
    op.create_index("idx_dunning_events_event_type", "dunning_events", ["event_type"])
    op.create_index(
        "idx_dunning_events_next_retry_at", "dunning_events", ["next_retry_at"]
    )

    op.execute("ALTER TABLE dunning_events ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE dunning_events FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY tenant_isolation_policy ON dunning_events
        FOR ALL
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::VARCHAR
        );
    """)

    op.execute("""
        CREATE POLICY admin_access_policy ON dunning_events
        FOR ALL
        USING (
            current_setting('app.user_role', true) = 'admin'
        );
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS admin_access_policy ON dunning_events;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON dunning_events;")
    op.execute("ALTER TABLE dunning_events DISABLE ROW LEVEL SECURITY;")

    op.drop_index("idx_dunning_events_next_retry_at", table_name="dunning_events")
    op.drop_index("idx_dunning_events_event_type", table_name="dunning_events")
    op.drop_index("idx_dunning_events_subscription_id", table_name="dunning_events")
    op.drop_index("idx_dunning_events_tenant_id", table_name="dunning_events")

    op.drop_table("dunning_events")
