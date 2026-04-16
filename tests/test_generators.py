"""Tests for generator classes."""

import sys
import importlib
from unittest.mock import Mock, patch

models = importlib.import_module("1ai_social.models")
Platform = models.Platform
Hook = models.Hook
Video = models.Video

hook_gen = importlib.import_module("1ai_social.generators.hook_generator")
HookGenerator = hook_gen.HookGenerator

video_pipe = importlib.import_module("1ai_social.generators.video_pipeline")
VideoPipeline = video_pipe.VideoPipeline

caption_pol = importlib.import_module("1ai_social.generators.caption_polisher")
CaptionPolisher = caption_pol.CaptionPolisher


class TestHookGenerator:
    """Test HookGenerator."""

    def test_instantiation(self):
        """Test generator can be instantiated."""
        gen = HookGenerator()
        assert gen is not None

    def test_generate_viral_hooks(self):
        """Test generating viral hooks."""
        gen = HookGenerator()
        hooks = gen.generate_viral_hooks("AI", count=3)
        assert len(hooks) == 3
        assert all(isinstance(h, Hook) for h in hooks)

    def test_generate_hooks_returns_hook_objects(self):
        """Test hooks have required attributes."""
        gen = HookGenerator()
        hooks = gen.generate_viral_hooks("tech", count=2)
        for hook in hooks:
            assert hasattr(hook, "text")
            assert hasattr(hook, "confidence")
            assert hasattr(hook, "type")
            assert isinstance(hook.text, str)
            assert isinstance(hook.confidence, float)
            assert 0 <= hook.confidence <= 1

    def test_rank_hooks_by_confidence(self):
        """Test hooks are ranked by confidence."""
        gen = HookGenerator()
        hooks = [
            Hook(text="low", confidence=0.3, type="test"),
            Hook(text="high", confidence=0.9, type="test"),
            Hook(text="mid", confidence=0.6, type="test"),
        ]
        ranked = gen.rank_hooks_by_confidence(hooks)
        assert ranked[0].confidence == 0.9
        assert ranked[1].confidence == 0.6
        assert ranked[2].confidence == 0.3

    def test_select_winner(self):
        """Test selecting best hook."""
        gen = HookGenerator()
        hooks = gen.generate_viral_hooks("business", count=5)
        winner = gen.select_winner(hooks)
        assert isinstance(winner, Hook)
        assert winner.confidence == max(h.confidence for h in hooks)

    def test_select_winner_empty_list(self):
        """Test select_winner raises error on empty list."""
        gen = HookGenerator()
        try:
            gen.select_winner([])
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "No hooks provided" in str(e)

    def test_generate_hooks_different_niches(self):
        """Test generating hooks for different niches."""
        gen = HookGenerator()
        for niche in ["AI", "tech", "design", "cooking", "fitness"]:
            hooks = gen.generate_viral_hooks(niche, count=2)
            assert len(hooks) == 2
            assert all(isinstance(h, Hook) for h in hooks)


class TestVideoPipeline:
    """Test VideoPipeline."""

    def test_instantiation(self):
        """Test pipeline can be instantiated."""
        pipeline = VideoPipeline()
        assert pipeline is not None

    def test_generate_video_returns_dict_or_video(self):
        """Test generate_video returns dict or Video object."""
        pipeline = VideoPipeline()
        content = {
            "text": "Amazing content",
            "template_id": "tiktok-viral-short",
            "duration": 60,
        }
        result = pipeline.generate_video(content, style="9:16")
        assert result is not None
        assert isinstance(result, (dict, Video))

    def test_generate_video_with_template(self):
        """Test video generation with template."""
        pipeline = VideoPipeline()
        content = {
            "text": "Test content",
            "template_id": "template_1",
            "duration": 30,
        }
        result = pipeline.generate_video(content)
        assert result is not None

    def test_generate_video_without_template(self):
        """Test video generation without template."""
        pipeline = VideoPipeline()
        content = {
            "text": "Test content",
            "duration": 45,
        }
        result = pipeline.generate_video(content)
        assert result is not None

    def test_fallback_generation(self):
        """Test fallback video generation."""
        pipeline = VideoPipeline()
        content = {"text": "test", "duration": 60}
        result = pipeline.fallback_generation(content)
        assert isinstance(result, dict)
        assert "path" in result
        assert "duration" in result
        assert "format" in result
        assert result["duration"] == 60

    def test_select_provider_with_template(self):
        """Test provider selection with template."""
        pipeline = VideoPipeline()
        content = {"template_id": "template_1", "text": "test"}
        provider = pipeline._select_provider(content)
        assert provider == "remotion"

    def test_select_provider_without_template(self):
        """Test provider selection without template."""
        pipeline = VideoPipeline()
        content = {"text": "test"}
        provider = pipeline._select_provider(content)
        assert provider == "content_generator"


class TestCaptionPolisher:
    """Test CaptionPolisher."""

    def test_instantiation(self):
        """Test polisher can be instantiated."""
        polisher = CaptionPolisher()
        assert polisher is not None

    def test_polish_caption_with_mock(self):
        """Test polishing caption with mocked humanizer."""
        polisher = CaptionPolisher()
        caption = "This is a test caption"
        with patch.object(polisher, "_get_humanizer") as mock_humanizer:
            mock_humanizer.return_value.humanize.return_value = caption
            result = polisher.polish(caption, Platform.TIKTOK)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_polish_adds_cta_with_mock(self):
        """Test polished caption includes CTA."""
        polisher = CaptionPolisher()
        caption = "Test caption"
        with patch.object(polisher, "_get_humanizer") as mock_humanizer:
            mock_humanizer.return_value.humanize.return_value = caption
            result = polisher.polish(caption, Platform.INSTAGRAM)
            assert isinstance(result, str)
            assert len(result) > len(caption)

    def test_polish_different_platforms_with_mock(self):
        """Test polishing for different platforms."""
        polisher = CaptionPolisher()
        caption = "Test caption"
        with patch.object(polisher, "_get_humanizer") as mock_humanizer:
            mock_humanizer.return_value.humanize.return_value = caption
            for platform in [Platform.TIKTOK, Platform.INSTAGRAM, Platform.X]:
                result = polisher.polish(caption, platform)
                assert isinstance(result, str)
                assert len(result) > 0

    def test_add_hooks(self):
        """Test adding CTAs."""
        polisher = CaptionPolisher()
        for cta_type in ["engagement", "share", "follow", "link"]:
            result = polisher.add_hooks(cta_type)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_optimize_for_algorithm(self):
        """Test getting hashtags for platform."""
        polisher = CaptionPolisher()
        hashtags = polisher.optimize_for_algorithm(Platform.TIKTOK)
        assert isinstance(hashtags, list)
        assert len(hashtags) > 0
        assert all(isinstance(h, str) for h in hashtags)

    def test_format_hashtags(self):
        """Test formatting hashtags."""
        polisher = CaptionPolisher()
        result = polisher._format_hashtags(Platform.INSTAGRAM)
        assert isinstance(result, str)
        assert "#" in result
