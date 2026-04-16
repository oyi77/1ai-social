from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class Platform(str, Enum):
    """Supported social media platforms"""

    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    X = "x"
    LINKEDIN = "linkedin"


class Video(BaseModel):
    """Video model for media content"""

    path: str = Field(..., description="File path to video")
    duration: float = Field(..., description="Duration in seconds")
    format: str = Field(..., description="Video format (mp4, mov, etc.)")
    width: Optional[int] = Field(None, description="Video width in pixels")
    height: Optional[int] = Field(None, description="Video height in pixels")

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v):
        if v <= 0:
            raise ValueError("Duration must be positive")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        allowed = ["mp4", "mov", "avi", "mkv", "webm"]
        if v.lower() not in allowed:
            raise ValueError(f"Format must be one of {allowed}")
        return v.lower()


class Hook(BaseModel):
    """Hook model for content hooks/angles"""

    text: str = Field(..., description="Hook text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    type: str = Field(..., description="Hook type (emotional, curiosity, value, etc.)")

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Hook text cannot be empty")
        return v.strip()


class Content(BaseModel):
    """Content model for social media content"""

    text: str = Field(..., description="Main content text")
    platform: Platform = Field(..., description="Target platform")
    media_url: Optional[str] = Field(None, description="URL to media (image/video)")
    video: Optional[Video] = Field(None, description="Video object if applicable")
    hooks: List[Hook] = Field(default_factory=list, description="Content hooks")
    hashtags: List[str] = Field(default_factory=list, description="Hashtags")
    mentions: List[str] = Field(default_factory=list, description="User mentions")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Content text cannot be empty")
        return v.strip()


class Post(BaseModel):
    """Post model for scheduled/published posts"""

    id: str = Field(..., description="Unique post identifier")
    content: Content = Field(..., description="Content object")
    scheduled_time: Optional[datetime] = Field(
        None, description="Scheduled publish time"
    )
    published_time: Optional[datetime] = Field(None, description="Actual publish time")
    status: str = Field(
        default="draft", description="Post status (draft, scheduled, published, failed)"
    )
    platform_post_id: Optional[str] = Field(
        None, description="Platform-specific post ID"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = ["draft", "scheduled", "published", "failed"]
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class AnalyticsRecord(BaseModel):
    """Analytics record for post performance"""

    post_id: str = Field(..., description="Associated post ID")
    platform: Platform = Field(..., description="Platform")
    views: int = Field(default=0, ge=0, description="View count")
    likes: int = Field(default=0, ge=0, description="Like count")
    shares: int = Field(default=0, ge=0, description="Share count")
    comments: int = Field(default=0, ge=0, description="Comment count")
    engagement_rate: float = Field(
        default=0.0, ge=0.0, description="Engagement rate percentage"
    )
    recorded_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record timestamp"
    )

    @field_validator("engagement_rate")
    @classmethod
    def validate_engagement_rate(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Engagement rate must be between 0 and 100")
        return v
