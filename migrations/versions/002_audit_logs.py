"""Add audit_logs table for compliance logging

Revision ID: 002_audit_logs
Revises: 001_initial_schema
Create Date: 2026-04-16 09:33:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "002_audit_logs"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=255), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column(
            "timestamp", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("signature", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("idx_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("idx_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])
    op.create_index("idx_audit_logs_timestamp", "audit_logs", ["timestamp"])

    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Audit logs are immutable and cannot be modified or deleted';
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER audit_logs_immutable_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_modification();
    """)

    op.execute("""
        CREATE TRIGGER audit_logs_immutable_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_log_modification();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_immutable_delete ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_immutable_update ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_modification()")

    op.drop_index("idx_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("idx_audit_logs_action", table_name="audit_logs")
    op.drop_index("idx_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_user_id", table_name="audit_logs")

    op.drop_table("audit_logs")
