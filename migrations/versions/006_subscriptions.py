"""Add subscriptions table for LemonSqueezy billing

Revision ID: 006_subscriptions
Revises: 005_api_keys
Create Date: 2026-04-16 10:18:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "006_subscriptions"
down_revision = "005_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column(
            "lemonsqueezy_subscription_id", sa.String(length=255), nullable=False
        ),
        sa.Column("lemonsqueezy_customer_id", sa.String(length=255), nullable=True),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_period_start", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column(
            "cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )

    op.create_index(
        "idx_subscriptions_lemonsqueezy_subscription_id",
        "subscriptions",
        ["lemonsqueezy_subscription_id"],
        unique=True,
    )
    op.create_index("idx_subscriptions_tenant_id", "subscriptions", ["tenant_id"])
    op.create_index("idx_subscriptions_status", "subscriptions", ["status"])

    op.execute("ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY tenant_isolation_policy ON subscriptions
        FOR ALL
        USING (
            tenant_id = current_setting('app.current_tenant_id', true)::VARCHAR
        );
    """)

    op.execute("""
        CREATE POLICY admin_access_policy ON subscriptions
        FOR ALL
        USING (
            current_setting('app.user_role', true) = 'admin'
        );
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS admin_access_policy ON subscriptions;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON subscriptions;")
    op.execute("ALTER TABLE subscriptions DISABLE ROW LEVEL SECURITY;")

    op.drop_index("idx_subscriptions_status", table_name="subscriptions")
    op.drop_index("idx_subscriptions_tenant_id", table_name="subscriptions")
    op.drop_index(
        "idx_subscriptions_lemonsqueezy_subscription_id", table_name="subscriptions"
    )

    op.drop_table("subscriptions")
