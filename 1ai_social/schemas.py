"""Pydantic schemas for API input validation and sanitization."""

import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator
import html


class PostCreateSchema(BaseModel):
    """Schema for creating a new post with validation."""

    niche: str = Field(
        ..., min_length=1, max_length=200, description="Content niche/topic"
    )
    platforms: List[str] = Field(default=["tiktok"], description="Target platforms")
    content_type: str = Field(default="video", description="Content type")
    count: int = Field(
        default=1, ge=1, le=10, description="Number of posts to generate"
    )

    @field_validator("niche")
    @classmethod
    def sanitize_niche(cls, v: str) -> str:
        """Sanitize niche text to prevent XSS."""
        if not v or not v.strip():
            raise ValueError("Niche cannot be empty")
        # HTML escape to prevent XSS
        sanitized = html.escape(v.strip())
        # Remove any remaining script tags
        sanitized = re.sub(
            r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
        )
        return sanitized

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: List[str]) -> List[str]:
        """Validate platform names."""
        allowed = ["tiktok", "instagram", "facebook", "x", "linkedin"]
        if not v:
            raise ValueError("At least one platform must be specified")
        for platform in v:
            if platform.lower() not in allowed:
                raise ValueError(
                    f"Invalid platform: {platform}. Must be one of {allowed}"
                )
        return [p.lower() for p in v]

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type."""
        allowed = ["video", "image", "text", "slideshow"]
        if v.lower() not in allowed:
            raise ValueError(f"Content type must be one of {allowed}")
        return v.lower()


class ContentCreateSchema(BaseModel):
    """Schema for creating content with validation."""

    text: str = Field(..., min_length=1, max_length=5000, description="Content text")
    platform: str = Field(..., description="Target platform")
    media_url: Optional[str] = Field(None, max_length=2000, description="Media URL")
    hashtags: List[str] = Field(
        default_factory=list, max_items=30, description="Hashtags"
    )
    mentions: List[str] = Field(
        default_factory=list, max_items=20, description="Mentions"
    )

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """Sanitize text content to prevent XSS."""
        if not v or not v.strip():
            raise ValueError("Content text cannot be empty")
        # HTML escape
        sanitized = html.escape(v.strip())
        # Remove script tags
        sanitized = re.sub(
            r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
        )
        # Remove event handlers
        sanitized = re.sub(r"on\w+\s*=", "", sanitized, flags=re.IGNORECASE)
        return sanitized

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """Validate platform name."""
        allowed = ["tiktok", "instagram", "facebook", "x", "linkedin"]
        if v.lower() not in allowed:
            raise ValueError(f"Platform must be one of {allowed}")
        return v.lower()

    @field_validator("media_url")
    @classmethod
    def validate_media_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate media URL format and scheme."""
        if v is None:
            return v
        v = v.strip()
        # Whitelist URL schemes
        if not re.match(r"^https?://", v, re.IGNORECASE):
            raise ValueError("Media URL must use http or https scheme")
        # Basic URL validation
        if not re.match(r'^https?://[^\s<>"{}|\\^`\[\]]+$', v, re.IGNORECASE):
            raise ValueError("Invalid media URL format")
        return v

    @field_validator("hashtags")
    @classmethod
    def sanitize_hashtags(cls, v: List[str]) -> List[str]:
        """Sanitize hashtags."""
        sanitized = []
        for tag in v:
            # Remove # if present
            tag = tag.lstrip("#").strip()
            # HTML escape
            tag = html.escape(tag)
            # Only allow alphanumeric and underscores
            if re.match(r"^[\w]+$", tag):
                sanitized.append(tag)
        return sanitized[:30]  # Limit to 30 tags

    @field_validator("mentions")
    @classmethod
    def sanitize_mentions(cls, v: List[str]) -> List[str]:
        """Sanitize user mentions."""
        sanitized = []
        for mention in v:
            # Remove @ if present
            mention = mention.lstrip("@").strip()
            # HTML escape
            mention = html.escape(mention)
            # Only allow alphanumeric, underscores, dots
            if re.match(r"^[\w.]+$", mention):
                sanitized.append(mention)
        return sanitized[:20]  # Limit to 20 mentions


class HookCreateSchema(BaseModel):
    """Schema for creating a hook with validation."""

    text: str = Field(..., min_length=1, max_length=500, description="Hook text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    type: str = Field(..., min_length=1, max_length=50, description="Hook type")

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        """Sanitize hook text."""
        if not v or not v.strip():
            raise ValueError("Hook text cannot be empty")
        sanitized = html.escape(v.strip())
        sanitized = re.sub(
            r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
        )
        return sanitized

    @field_validator("type")
    @classmethod
    def sanitize_type(cls, v: str) -> str:
        """Sanitize hook type."""
        sanitized = html.escape(v.strip())
        # Only allow alphanumeric and underscores
        if not re.match(r"^[\w\s-]+$", sanitized):
            raise ValueError("Hook type contains invalid characters")
        return sanitized


class CampaignCreateSchema(BaseModel):
    """Schema for creating a campaign with validation."""

    niche: str = Field(..., min_length=1, max_length=200, description="Campaign niche")
    platforms: List[str] = Field(default=["tiktok"], description="Target platforms")
    days: int = Field(default=7, ge=1, le=90, description="Campaign duration in days")

    @field_validator("niche")
    @classmethod
    def sanitize_niche(cls, v: str) -> str:
        """Sanitize niche text."""
        if not v or not v.strip():
            raise ValueError("Niche cannot be empty")
        sanitized = html.escape(v.strip())
        sanitized = re.sub(
            r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
        )
        return sanitized

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: List[str]) -> List[str]:
        """Validate platform names."""
        allowed = ["tiktok", "instagram", "facebook", "x", "linkedin"]
        if not v:
            raise ValueError("At least one platform must be specified")
        for platform in v:
            if platform.lower() not in allowed:
                raise ValueError(f"Invalid platform: {platform}")
        return [p.lower() for p in v]


class AnalyticsQuerySchema(BaseModel):
    """Schema for analytics queries with validation."""

    post_id: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Post ID"
    )
    platform: Optional[str] = Field(None, description="Platform filter")
    days: int = Field(default=30, ge=1, le=365, description="Days to look back")

    @field_validator("post_id")
    @classmethod
    def sanitize_post_id(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize post ID to prevent SQL injection."""
        if v is None:
            return v
        v = v.strip()
        # Only allow alphanumeric, hyphens, underscores
        if not re.match(r"^[\w-]+$", v):
            raise ValueError("Post ID contains invalid characters")
        return v

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: Optional[str]) -> Optional[str]:
        """Validate platform name."""
        if v is None:
            return v
        allowed = ["tiktok", "instagram", "facebook", "x", "linkedin"]
        if v.lower() not in allowed:
            raise ValueError(f"Platform must be one of {allowed}")
        return v.lower()


class UserCreateSchema(BaseModel):
    """Schema for creating a user with validation."""

    user_id: str = Field(
        ..., min_length=1, max_length=255, description="User identifier"
    )
    tenant_id: Optional[str] = Field(
        None, max_length=255, description="Tenant identifier"
    )

    @field_validator("user_id")
    @classmethod
    def sanitize_user_id(cls, v: str) -> str:
        """Sanitize user ID."""
        v = v.strip()
        # Only allow alphanumeric, hyphens, underscores, dots
        if not re.match(r"^[\w.-]+$", v):
            raise ValueError("User ID contains invalid characters")
        return v

    @field_validator("tenant_id")
    @classmethod
    def sanitize_tenant_id(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize tenant ID."""
        if v is None:
            return v
        v = v.strip()
        # Only allow alphanumeric, hyphens, underscores
        if not re.match(r"^[\w-]+$", v):
            raise ValueError("Tenant ID contains invalid characters")
        return v


class PlatformCredentialsSchema(BaseModel):
    """Schema for platform credentials with validation."""

    name: str = Field(..., min_length=1, max_length=50, description="Platform name")
    credentials: str = Field(..., min_length=1, description="Encrypted credentials")
    user_id: str = Field(..., min_length=1, max_length=255, description="User ID")
    tenant_id: Optional[str] = Field(None, max_length=255, description="Tenant ID")

    @field_validator("name")
    @classmethod
    def validate_platform_name(cls, v: str) -> str:
        """Validate platform name."""
        allowed = ["tiktok", "instagram", "facebook", "x", "linkedin"]
        if v.lower() not in allowed:
            raise ValueError(f"Platform must be one of {allowed}")
        return v.lower()

    @field_validator("user_id")
    @classmethod
    def sanitize_user_id(cls, v: str) -> str:
        """Sanitize user ID."""
        v = v.strip()
        if not re.match(r"^[\w.-]+$", v):
            raise ValueError("User ID contains invalid characters")
        return v

    @field_validator("tenant_id")
    @classmethod
    def sanitize_tenant_id(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize tenant ID."""
        if v is None:
            return v
        v = v.strip()
        if not re.match(r"^[\w-]+$", v):
            raise ValueError("Tenant ID contains invalid characters")
        return v


# Request size limit validator
class RequestSizeLimiter:
    """Middleware to limit request body size."""

    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB

    @staticmethod
    def validate_size(content_length: Optional[int]) -> None:
        """Validate request content length."""
        if content_length and content_length > RequestSizeLimiter.MAX_REQUEST_SIZE:
            raise ValueError(
                f"Request size exceeds maximum allowed size of {RequestSizeLimiter.MAX_REQUEST_SIZE} bytes"
            )
