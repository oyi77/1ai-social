"""Initial schema with all tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-04-16 09:22:26.376000

"""

from alembic import op
import sqlalchemy as sa


revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platforms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("credentials", sa.Text(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("media_url", sa.String(length=500), nullable=True),
        sa.Column("video_path", sa.String(length=500), nullable=True),
        sa.Column("video_duration", sa.Float(), nullable=True),
        sa.Column("video_format", sa.String(length=20), nullable=True),
        sa.Column("video_width", sa.Integer(), nullable=True),
        sa.Column("video_height", sa.Integer(), nullable=True),
        sa.Column("hashtags", sa.Text(), nullable=True),
        sa.Column("mentions", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "hooks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=True),
        sa.Column("platform_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["contents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["platform_id"],
            ["platforms.id"],
        ),
    )

    op.create_table(
        "posts",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_time", sa.DateTime(), nullable=True),
        sa.Column("published_time", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("platform_post_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["content_id"],
            ["contents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["platform_id"],
            ["platforms.id"],
        ),
    )

    op.create_table(
        "analytics_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.String(length=255), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("engagement_rate", sa.Float(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["posts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["platform_id"],
            ["platforms.id"],
        ),
    )


def downgrade() -> None:
    op.drop_table("analytics_records")
    op.drop_table("posts")
    op.drop_table("hooks")
    op.drop_table("contents")
    op.drop_table("platforms")
