"""Add consent_records table for GDPR compliance

Revision ID: 010_gdpr
Revises: 009_oauth_accounts
Create Date: 2026-04-16 10:57:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "010_gdpr"
down_revision = "009_oauth_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consent_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("consent_type", sa.String(length=100), nullable=False),
        sa.Column("consented", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )

    op.create_index("idx_consent_records_user_id", "consent_records", ["user_id"])
    op.create_index("idx_consent_records_tenant_id", "consent_records", ["tenant_id"])
    op.create_index(
        "idx_consent_records_consent_type", "consent_records", ["consent_type"]
    )
    op.create_index("idx_consent_records_timestamp", "consent_records", ["timestamp"])

    op.execute("ALTER TABLE consent_records ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE consent_records FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY consent_records_tenant_isolation ON consent_records
        USING (tenant_id = current_setting('app.current_tenant_id', TRUE));
    """)


def downgrade() -> None:
    op.drop_table("consent_records")
