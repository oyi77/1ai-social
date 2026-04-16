"""SQLAlchemy ORM models for database persistence."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Enum,
    Boolean,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class PlatformEnum(str, enum.Enum):
    """Platform enumeration for database storage."""

    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    X = "x"
    LINKEDIN = "linkedin"


class PlatformModel(Base):
    """Platform configuration table."""

    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    credentials = Column(Text, nullable=False)
    user_id = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=True)  # Wave 3: multi-tenancy
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    # Relationships
    posts = relationship("PostModel", back_populates="platform")
    hooks = relationship("HookModel", back_populates="platform")
    analytics_records = relationship("AnalyticsRecordModel", back_populates="platform")


class ContentModel(Base):
    """Content table for social media content."""

    __tablename__ = "contents"

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False)
    media_url = Column(String(500), nullable=True)
    video_path = Column(String(500), nullable=True)
    video_duration = Column(Float, nullable=True)
    video_format = Column(String(20), nullable=True)
    video_width = Column(Integer, nullable=True)
    video_height = Column(Integer, nullable=True)
    hashtags = Column(Text, nullable=True)  # JSON array as string
    mentions = Column(Text, nullable=True)  # JSON array as string
    tenant_id = Column(String(255), nullable=True)  # Wave 3: multi-tenancy
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    posts = relationship("PostModel", back_populates="content")
    hooks = relationship("HookModel", back_populates="content")


class HookModel(Base):
    """Hook/angle table for content hooks."""

    __tablename__ = "hooks"

    id = Column(Integer, primary_key=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=True)
    text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    type = Column(String(50), nullable=False)
    tenant_id = Column(String(255), nullable=True)  # Wave 3: multi-tenancy
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    content = relationship("ContentModel", back_populates="hooks")
    platform = relationship("PlatformModel", back_populates="hooks")


class PostModel(Base):
    """Post table for scheduled/published posts."""

    __tablename__ = "posts"

    id = Column(String(255), primary_key=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    scheduled_time = Column(DateTime, nullable=True)
    published_time = Column(DateTime, nullable=True)
    status = Column(String(50), default="draft", nullable=False)
    platform_post_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    tenant_id = Column(String(255), nullable=True)  # Wave 3: multi-tenancy
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    # Relationships
    content = relationship("ContentModel", back_populates="posts")
    platform = relationship("PlatformModel", back_populates="posts")
    analytics_records = relationship("AnalyticsRecordModel", back_populates="post")


class AnalyticsRecordModel(Base):
    """Analytics record table for post performance metrics."""

    __tablename__ = "analytics_records"

    id = Column(Integer, primary_key=True)
    post_id = Column(String(255), ForeignKey("posts.id"), nullable=False)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    content_type = Column(String(50), default="video", nullable=False)
    views = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    shares = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    engagement_rate = Column(Float, default=0.0, nullable=False)
    tenant_id = Column(String(255), nullable=True)  # Wave 3: multi-tenancy
    recorded_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Relationships
    post = relationship("PostModel", back_populates="analytics_records")
    platform = relationship("PlatformModel", back_populates="analytics_records")
