"""Tests for analytics classes."""

import sys
import importlib
import tempfile
import json
from pathlib import Path
from datetime import datetime

models = importlib.import_module("1ai_social.models")
Platform = models.Platform
AnalyticsRecord = models.AnalyticsRecord

tracker_mod = importlib.import_module("1ai_social.analytics.tracker")
AnalyticsTracker = tracker_mod.AnalyticsTracker

confidence_mod = importlib.import_module("1ai_social.analytics.confidence")
ConfidenceUpdater = confidence_mod.ConfidenceUpdater

memory_mod = importlib.import_module("1ai_social.analytics.memory")
MemorySystem = memory_mod.MemorySystem


class TestAnalyticsTracker:
    """Test AnalyticsTracker."""

    def test_instantiation(self):
        """Test tracker can be instantiated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / "analytics.json"
            tracker = AnalyticsTracker(str(tracker_path))
            assert tracker is not None

    def test_track_post(self):
        """Test tracking post metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / "analytics.json"
            tracker = AnalyticsTracker(str(tracker_path))
            metrics = {"views": 1000, "likes": 100, "shares": 50}
            tracker.track_post("post_1", metrics)
            stats = tracker.get_stats("post_1")
            assert stats == metrics

    def test_get_stats(self):
        """Test getting post statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / "analytics.json"
            tracker = AnalyticsTracker(str(tracker_path))
            metrics = {"views": 500, "likes": 50}
            tracker.track_post("post_2", metrics)
            stats = tracker.get_stats("post_2")
            assert stats["views"] == 500
            assert stats["likes"] == 50

    def test_get_stats_not_found(self):
        """Test getting stats for nonexistent post."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / "analytics.json"
            tracker = AnalyticsTracker(str(tracker_path))
            stats = tracker.get_stats("nonexistent")
            assert stats is None

    def test_aggregate_stats(self):
        """Test aggregating statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / "analytics.json"
            tracker = AnalyticsTracker(str(tracker_path))
            tracker.track_post("post_1", {"views": 1000, "likes": 100})
            tracker.track_post("post_2", {"views": 2000, "likes": 200})
            agg = tracker.aggregate_stats()
            assert agg["total_posts"] == 2
            assert agg["total_views"] == 3000
            assert agg["total_likes"] == 300

    def test_get_all_records(self):
        """Test getting all records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / "analytics.json"
            tracker = AnalyticsTracker(str(tracker_path))
            tracker.track_post("post_1", {"views": 100})
            tracker.track_post("post_2", {"views": 200})
            records = tracker.get_all_records()
            assert len(records) == 2
            assert "post_1" in records
            assert "post_2" in records

    def test_persistence(self):
        """Test tracker persists to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / "analytics.json"
            tracker1 = AnalyticsTracker(str(tracker_path))
            tracker1.track_post("post_1", {"views": 500})

            tracker2 = AnalyticsTracker(str(tracker_path))
            stats = tracker2.get_stats("post_1")
            assert stats["views"] == 500


class TestConfidenceUpdater:
    """Test ConfidenceUpdater."""

    def test_instantiation(self):
        """Test updater can be instantiated."""
        updater = ConfidenceUpdater()
        assert updater is not None

    def test_update_hook_confidence(self):
        """Test updating hook confidence."""
        updater = ConfidenceUpdater()
        new_score = updater.update_hook_confidence("landlord_ai", 50000)
        assert new_score > 0.9

    def test_get_confidence(self):
        """Test getting hook confidence."""
        updater = ConfidenceUpdater()
        score = updater.get_confidence("landlord_ai")
        assert score == 0.9

    def test_get_confidence_unknown_hook(self):
        """Test getting confidence for unknown hook."""
        updater = ConfidenceUpdater()
        score = updater.get_confidence("unknown_hook")
        assert score == 0.5

    def test_get_top_hooks(self):
        """Test getting top hooks."""
        updater = ConfidenceUpdater()
        top = updater.get_top_hooks(limit=3)
        assert len(top) <= 3
        assert all(isinstance(h, tuple) for h in top)
        assert all(len(h) == 2 for h in top)

    def test_get_top_hooks_sorted(self):
        """Test top hooks are sorted by confidence."""
        updater = ConfidenceUpdater()
        top = updater.get_top_hooks(limit=5)
        scores = [h[1] for h in top]
        assert scores == sorted(scores, reverse=True)

    def test_decay_old_hooks(self):
        """Test decaying old hooks."""
        updater = ConfidenceUpdater()
        updater.update_hook_confidence("landlord_ai", 100000)
        before = updater.get_confidence("landlord_ai")
        decayed = updater.decay_old_hooks(decay_factor=0.9)
        after = updater.get_confidence("landlord_ai")
        assert after < before
        assert decayed > 0

    def test_get_all_scores(self):
        """Test getting all scores."""
        updater = ConfidenceUpdater()
        scores = updater.get_all_scores()
        assert isinstance(scores, dict)
        assert "landlord_ai" in scores
        assert "parent_ai" in scores


class TestMemorySystem:
    """Test MemorySystem."""

    def test_instantiation(self):
        """Test memory system can be instantiated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memory.json"
            memory = MemorySystem(str(memory_path))
            assert memory is not None

    def test_save_lesson(self):
        """Test saving a lesson."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memory.json"
            memory = MemorySystem(str(memory_path))
            result = {"views": 5000, "success": True}
            memory.save_lesson("landlord_ai", result)
            lessons = memory.get_lessons("landlord_ai")
            assert len(lessons) == 1
            assert lessons[0]["hook_type"] == "landlord_ai"

    def test_get_lessons(self):
        """Test getting lessons."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memory.json"
            memory = MemorySystem(str(memory_path))
            memory.save_lesson("emotional", {"views": 1000, "success": True})
            memory.save_lesson("emotional", {"views": 2000, "success": False})
            lessons = memory.get_lessons("emotional")
            assert len(lessons) == 2

    def test_get_lessons_all(self):
        """Test getting all lessons."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memory.json"
            memory = MemorySystem(str(memory_path))
            memory.save_lesson("hook1", {"views": 100})
            memory.save_lesson("hook2", {"views": 200})
            all_lessons = memory.get_lessons()
            assert len(all_lessons) == 2

    def test_get_successful_patterns(self):
        """Test getting successful patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memory.json"
            memory = MemorySystem(str(memory_path))
            memory.save_lesson("hook1", {"views": 1000, "success": True})
            memory.save_lesson("hook2", {"views": 500, "success": False})
            successful = memory.get_successful_patterns()
            assert len(successful) == 1
            assert successful[0]["result"]["success"] is True

    def test_evolve_rules(self):
        """Test evolving rules from lessons."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memory.json"
            memory = MemorySystem(str(memory_path))
            memory.save_lesson("hook1", {"success": True})
            memory.save_lesson("hook1", {"success": True})
            memory.save_lesson("hook1", {"success": False})
            rules = memory.evolve_rules()
            assert "hook1" in rules
            assert "success_rate" in rules["hook1"]
            assert rules["hook1"]["success_rate"] > 0

    def test_clear_old_lessons(self):
        """Test clearing old lessons."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memory.json"
            memory = MemorySystem(str(memory_path))
            memory.save_lesson("hook1", {"views": 100})
            cleared = memory.clear_old_lessons(days=0)
            assert cleared >= 0

    def test_persistence(self):
        """Test memory persists to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memory.json"
            memory1 = MemorySystem(str(memory_path))
            memory1.save_lesson("hook1", {"views": 1000, "success": True})

            memory2 = MemorySystem(str(memory_path))
            lessons = memory2.get_lessons("hook1")
            assert len(lessons) == 1
            assert lessons[0]["result"]["views"] == 1000
