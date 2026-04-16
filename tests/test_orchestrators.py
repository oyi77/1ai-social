"""Tests for orchestrator classes."""

import sys
import importlib
from unittest.mock import Mock, patch, MagicMock

models = importlib.import_module("1ai_social.models")
Platform = models.Platform
Content = models.Content

orchestrator_mod = importlib.import_module("1ai_social.orchestrators.orchestrator")
Orchestrator = orchestrator_mod.Orchestrator


class TestOrchestrator:
    """Test Orchestrator."""

    def test_instantiation(self):
        """Test orchestrator can be instantiated."""
        orch = Orchestrator()
        assert orch is not None

    def test_generate_and_post_returns_dict(self):
        """Test generate_and_post returns dict with status."""
        orch = Orchestrator()
        request = {
            "niche": "AI",
            "platforms": ["tiktok"],
            "content_type": "video",
            "count": 1,
        }
        result = orch.generate_and_post(request)
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] in ["success", "partial", "failed"]

    def test_generate_and_post_has_required_keys(self):
        """Test generate_and_post result has required keys."""
        orch = Orchestrator()
        request = {
            "niche": "tech",
            "platforms": ["instagram"],
            "content_type": "video",
        }
        result = orch.generate_and_post(request)
        assert "status" in result
        assert "posts" in result
        assert "hooks_used" in result
        assert "errors" in result

    def test_generate_and_post_with_multiple_platforms(self):
        """Test generate_and_post with multiple platforms."""
        orch = Orchestrator()
        request = {
            "niche": "business",
            "platforms": ["tiktok", "instagram"],
            "content_type": "video",
        }
        result = orch.generate_and_post(request)
        assert isinstance(result, dict)
        assert "status" in result

    def test_generate_content_only(self):
        """Test generate_content_only returns preview."""
        orch = Orchestrator()
        request = {
            "niche": "AI",
            "content_type": "video",
        }
        result = orch.generate_content_only(request)
        assert isinstance(result, dict)
        assert "hooks" in result
        assert "winner" in result
        assert "caption" in result
        assert "niche" in result

    def test_generate_content_only_has_hooks(self):
        """Test generate_content_only includes hooks."""
        orch = Orchestrator()
        request = {"niche": "tech"}
        result = orch.generate_content_only(request)
        assert isinstance(result["hooks"], list)

    def test_schedule_campaign(self):
        """Test schedule_campaign returns campaign dict."""
        orch = Orchestrator()
        request = {
            "niche": "AI",
            "platforms": ["tiktok"],
        }
        result = orch.schedule_campaign(request, days=7)
        assert isinstance(result, dict)
        assert "niche" in result
        assert "days" in result
        assert "calendar" in result
        assert "scheduled_count" in result

    def test_schedule_campaign_days_parameter(self):
        """Test schedule_campaign respects days parameter."""
        orch = Orchestrator()
        request = {"niche": "business", "platforms": ["instagram"]}
        result = orch.schedule_campaign(request, days=14)
        assert result["days"] == 14
