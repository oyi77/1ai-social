"""Add oauth_accounts table for OAuth 2.0 integration

Revision ID: 009_oauth_accounts
Revises: 008_dunning
Create Date: 2026-04-16 10:45:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "009_oauth_accounts"
down_revision = "008_dunning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_account_id", sa.String(length=255), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
            onupdate=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "provider", "provider_account_id", name="uq_provider_account"
        ),
    )

    op.create_index("idx_oauth_accounts_user_id", "oauth_accounts", ["user_id"])
    op.create_index("idx_oauth_accounts_tenant_id", "oauth_accounts", ["tenant_id"])
    op.create_index("idx_oauth_accounts_provider", "oauth_accounts", ["provider"])

    op.execute("ALTER TABLE oauth_accounts ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE oauth_accounts FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY oauth_accounts_tenant_isolation ON oauth_accounts
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE));
    """)


def downgrade() -> None:
    op.drop_table("oauth_accounts")
