from alembic import op
import sqlalchemy as sa


revision = "011_onboarding"
down_revision = "010_tenant_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_progress",
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("current_phase", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("role_selection", sa.String(50), nullable=True),
        sa.Column(
            "first_platform_connected",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "first_post_published", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("completed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("skipped", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("tenant_id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )

    op.create_index(
        "ix_onboarding_progress_skipped", "onboarding_progress", ["skipped"]
    )

    op.create_index(
        "ix_onboarding_progress_completed_at", "onboarding_progress", ["completed_at"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_onboarding_progress_completed_at", table_name="onboarding_progress"
    )
    op.drop_index("ix_onboarding_progress_skipped", table_name="onboarding_progress")
    op.drop_table("onboarding_progress")
