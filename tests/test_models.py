from datetime import datetime, timezone
"""Tests for Pydantic models."""

import importlib

# Import models using importlib due to package name starting with digit
models = importlib.import_module("1ai_social.models")
Platform = models.Platform
Video = models.Video
Hook = models.Hook
Content = models.Content
Post = models.Post
AnalyticsRecord = models.AnalyticsRecord


class TestPlatformEnum:
    """Test Platform enum."""

    def test_platform_values(self):
        """Test all platform values exist."""
        assert Platform.TIKTOK.value == "tiktok"
        assert Platform.INSTAGRAM.value == "instagram"
        assert Platform.FACEBOOK.value == "facebook"
        assert Platform.X.value == "x"
        assert Platform.LINKEDIN.value == "linkedin"

    def test_platform_from_string(self):
        """Test creating Platform from string."""
        assert Platform("tiktok") == Platform.TIKTOK
        assert Platform("instagram") == Platform.INSTAGRAM


class TestVideoModel:
    """Test Video model."""

    def test_valid_video(self):
        """Test creating valid video."""
        video = Video(
            path="/tmp/video.mp4", duration=60.0, format="mp4", width=1080, height=1920
        )
        assert video.path == "/tmp/video.mp4"
        assert video.duration == 60.0
        assert video.format == "mp4"
        assert video.width == 1080
        assert video.height == 1920

    def test_video_format_lowercase(self):
        """Test format is converted to lowercase."""
        video = Video(path="/tmp/video.mp4", duration=30.0, format="MP4")
        assert video.format == "mp4"

    def test_video_invalid_duration(self):
        """Test negative duration raises error."""
        try:
            Video(path="/tmp/video.mp4", duration=-10.0, format="mp4")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Duration must be positive" in str(e)

    def test_video_invalid_format(self):
        """Test invalid format raises error."""
        try:
            Video(path="/tmp/video.mp4", duration=30.0, format="xyz")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Format must be one of" in str(e)

    def test_video_allowed_formats(self):
        """Test all allowed formats."""
        for fmt in ["mp4", "mov", "avi", "mkv", "webm"]:
            video = Video(path="/tmp/video.mp4", duration=30.0, format=fmt)
            assert video.format == fmt


class TestHookModel:
    """Test Hook model."""

    def test_valid_hook(self):
        """Test creating valid hook."""
        hook = Hook(text="This is an amazing hook", confidence=0.85, type="emotional")
        assert hook.text == "This is an amazing hook"
        assert hook.confidence == 0.85
        assert hook.type == "emotional"

    def test_hook_text_stripped(self):
        """Test hook text is stripped."""
        hook = Hook(text="  hook text  ", confidence=0.5, type="curiosity")
        assert hook.text == "hook text"

    def test_hook_empty_text(self):
        """Test empty hook text raises error."""
        try:
            Hook(text="", confidence=0.5, type="test")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Hook text cannot be empty" in str(e)

    def test_hook_confidence_bounds(self):
        """Test confidence must be 0-1."""
        # Valid bounds
        Hook(text="test", confidence=0.0, type="test")
        Hook(text="test", confidence=1.0, type="test")

        # Invalid bounds
        try:
            Hook(text="test", confidence=-0.1, type="test")
            assert False, "Should raise ValueError"
        except ValueError:
            pass

        try:
            Hook(text="test", confidence=1.1, type="test")
            assert False, "Should raise ValueError"
        except ValueError:
            pass


class TestContentModel:
    """Test Content model."""

    def test_valid_content(self):
        """Test creating valid content."""
        content = Content(
            text="Amazing AI content",
            platform=Platform.TIKTOK,
            media_url="https://example.com/video.mp4",
            hashtags=["#ai", "#tech"],
            mentions=["@user1", "@user2"],
        )
        assert content.text == "Amazing AI content"
        assert content.platform == Platform.TIKTOK
        assert len(content.hashtags) == 2
        assert len(content.mentions) == 2

    def test_content_created_at_default(self):
        """Test created_at defaults to now."""
        content = Content(text="test", platform=Platform.INSTAGRAM)
        assert isinstance(content.created_at, datetime)

    def test_content_empty_text(self):
        """Test empty content text raises error."""
        try:
            Content(text="", platform=Platform.TIKTOK)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Content text cannot be empty" in str(e)

    def test_content_with_video(self):
        """Test content with video object."""
        video = Video(path="/tmp/video.mp4", duration=60.0, format="mp4")
        content = Content(text="Video content", platform=Platform.TIKTOK, video=video)
        assert content.video == video
        assert content.video.path == "/tmp/video.mp4"

    def test_content_with_hooks(self):
        """Test content with hooks."""
        hook = Hook(text="Amazing hook", confidence=0.9, type="emotional")
        content = Content(
            text="Content with hook", platform=Platform.INSTAGRAM, hooks=[hook]
        )
        assert len(content.hooks) == 1
        assert content.hooks[0].text == "Amazing hook"


class TestPostModel:
    """Test Post model."""

    def test_valid_post(self):
        """Test creating valid post."""
        content = Content(text="test", platform=Platform.TIKTOK)
        post = Post(id="post_123", content=content, status="draft")
        assert post.id == "post_123"
        assert post.status == "draft"
        assert post.content == content

    def test_post_default_status(self):
        """Test post status defaults to draft."""
        content = Content(text="test", platform=Platform.TIKTOK)
        post = Post(id="post_123", content=content)
        assert post.status == "draft"

    def test_post_invalid_status(self):
        """Test invalid status raises error."""
        content = Content(text="test", platform=Platform.TIKTOK)
        try:
            Post(id="post_123", content=content, status="invalid")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Status must be one of" in str(e)

    def test_post_valid_statuses(self):
        """Test all valid statuses."""
        content = Content(text="test", platform=Platform.TIKTOK)
        for status in ["draft", "scheduled", "published", "failed"]:
            post = Post(id="post_123", content=content, status=status)
            assert post.status == status

    def test_post_with_timestamps(self):
        """Test post with scheduled and published times."""
        content = Content(text="test", platform=Platform.TIKTOK)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        post = Post(
            id="post_123",
            content=content,
            scheduled_time=now,
            published_time=now,
            status="published",
        )
        assert post.scheduled_time == now
        assert post.published_time == now


class TestAnalyticsRecordModel:
    """Test AnalyticsRecord model."""

    def test_valid_analytics_record(self):
        """Test creating valid analytics record."""
        record = AnalyticsRecord(
            post_id="post_123",
            platform=Platform.TIKTOK,
            views=1000,
            likes=100,
            shares=50,
            comments=25,
            engagement_rate=17.5,
        )
        assert record.post_id == "post_123"
        assert record.views == 1000
        assert record.likes == 100
        assert record.engagement_rate == 17.5

    def test_analytics_record_defaults(self):
        """Test analytics record defaults."""
        record = AnalyticsRecord(post_id="post_123", platform=Platform.INSTAGRAM)
        assert record.views == 0
        assert record.likes == 0
        assert record.shares == 0
        assert record.comments == 0
        assert record.engagement_rate == 0.0

    def test_analytics_record_negative_values(self):
        """Test negative metric values raise error."""
        try:
            AnalyticsRecord(post_id="post_123", platform=Platform.TIKTOK, views=-100)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_analytics_record_invalid_engagement_rate(self):
        """Test engagement rate must be 0-100."""
        try:
            AnalyticsRecord(
                post_id="post_123", platform=Platform.TIKTOK, engagement_rate=150.0
            )
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Engagement rate must be between 0 and 100" in str(e)

    def test_analytics_record_recorded_at_default(self):
        """Test recorded_at defaults to now."""
        record = AnalyticsRecord(post_id="post_123", platform=Platform.TIKTOK)
        assert isinstance(record.recorded_at, datetime)
