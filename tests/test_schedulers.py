"""Tests for scheduler classes."""

import sys
import importlib
import tempfile
import json
from pathlib import Path

scheduler_mod = importlib.import_module("1ai_social.schedulers.scheduler")
Scheduler = scheduler_mod.Scheduler

queue_mod = importlib.import_module("1ai_social.schedulers.queue_manager")
QueueManager = queue_mod.QueueManager


class TestScheduler:
    """Test Scheduler."""

    def test_instantiation(self):
        """Test scheduler can be instantiated."""
        scheduler = Scheduler()
        assert scheduler is not None

    def test_validate_cron_valid(self):
        """Test validating valid cron expressions."""
        scheduler = Scheduler()
        assert scheduler.validate_cron("0 7 * * *") is True
        assert scheduler.validate_cron("0 0 1 * *") is True
        assert scheduler.validate_cron("30 2 * * *") is True

    def test_validate_cron_invalid(self):
        """Test validating invalid cron expressions."""
        scheduler = Scheduler()
        assert scheduler.validate_cron("invalid") is False
        assert scheduler.validate_cron("0 0 0") is False
        assert scheduler.validate_cron("0 0 0 0 0 0") is False

    def test_schedule_job(self):
        """Test scheduling a job."""
        scheduler = Scheduler()
        callback = lambda: None
        job_id = scheduler.schedule_job("0 7 * * *", callback, "test_job")
        assert job_id == "test_job"

    def test_schedule_job_invalid_cron(self):
        """Test scheduling with invalid cron raises error."""
        scheduler = Scheduler()
        callback = lambda: None
        try:
            scheduler.schedule_job("invalid", callback)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Invalid cron expression" in str(e)

    def test_schedule_job_auto_id(self):
        """Test job gets auto-generated ID."""
        scheduler = Scheduler()
        callback = lambda: None
        job_id = scheduler.schedule_job("0 7 * * *", callback)
        assert job_id is not None
        assert isinstance(job_id, str)

    def test_remove_job(self):
        """Test removing a job."""
        scheduler = Scheduler()
        callback = lambda: None
        job_id = scheduler.schedule_job("0 7 * * *", callback, "remove_test")
        result = scheduler.remove_job(job_id)
        assert result is True

    def test_remove_job_not_found(self):
        """Test removing nonexistent job returns False."""
        scheduler = Scheduler()
        result = scheduler.remove_job("nonexistent")
        assert result is False

    def test_run_daily(self):
        """Test scheduling daily job."""
        scheduler = Scheduler()
        job_id = scheduler.run_daily()
        assert job_id == "daily_content"

    def test_run_hourly(self):
        """Test scheduling hourly job."""
        scheduler = Scheduler()
        job_id = scheduler.run_hourly()
        assert job_id == "hourly_engagement"

    def test_get_jobs(self):
        """Test getting all jobs."""
        scheduler = Scheduler()
        callback = lambda: None
        scheduler.schedule_job("0 7 * * *", callback, "job1")
        scheduler.schedule_job("0 8 * * *", callback, "job2")
        jobs = scheduler.get_jobs()
        assert len(jobs) >= 2
        assert "job1" in jobs
        assert "job2" in jobs


class TestQueueManager:
    """Test QueueManager."""

    def test_instantiation(self):
        """Test queue manager can be instantiated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm = QueueManager(str(queue_path))
            assert qm is not None

    def test_enqueue(self):
        """Test enqueueing item."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm = QueueManager(str(queue_path))
            item = {"post_id": "post_1", "content": "test"}
            pos = qm.enqueue(item)
            assert pos == 0

    def test_dequeue(self):
        """Test dequeueing item."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm = QueueManager(str(queue_path))
            item = {"post_id": "post_1", "content": "test"}
            qm.enqueue(item)
            dequeued = qm.dequeue()
            assert dequeued is not None
            assert dequeued["post_id"] == "post_1"

    def test_dequeue_empty(self):
        """Test dequeueing from empty queue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm = QueueManager(str(queue_path))
            result = qm.dequeue()
            assert result is None

    def test_peek(self):
        """Test peeking at next item."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm = QueueManager(str(queue_path))
            item = {"post_id": "post_1"}
            qm.enqueue(item)
            peeked = qm.peek()
            assert peeked is not None
            assert peeked["post_id"] == "post_1"
            assert qm.size() == 1

    def test_size(self):
        """Test getting queue size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm = QueueManager(str(queue_path))
            assert qm.size() == 0
            qm.enqueue({"id": "1"})
            assert qm.size() == 1
            qm.enqueue({"id": "2"})
            assert qm.size() == 2

    def test_clear(self):
        """Test clearing queue."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm = QueueManager(str(queue_path))
            qm.enqueue({"id": "1"})
            qm.enqueue({"id": "2"})
            cleared = qm.clear()
            assert cleared == 2
            assert qm.size() == 0

    def test_get_failed(self):
        """Test getting failed items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm = QueueManager(str(queue_path))
            qm.enqueue({"id": "1"})
            qm._queue[0]["status"] = "failed"
            failed = qm.get_failed()
            assert len(failed) == 1
            assert failed[0]["id"] == "1"

    def test_retry_failed(self):
        """Test retrying failed items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm = QueueManager(str(queue_path))
            qm.enqueue({"id": "1"})
            qm._queue[0]["status"] = "failed"
            retried = qm.retry_failed()
            assert retried == 1
            assert qm._queue[0]["status"] == "queued"

    def test_persistence(self):
        """Test queue persists to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            queue_path = Path(tmpdir) / "queue.json"
            qm1 = QueueManager(str(queue_path))
            qm1.enqueue({"id": "1", "data": "test"})

            qm2 = QueueManager(str(queue_path))
            assert qm2.size() == 1
            item = qm2.peek()
            assert item["id"] == "1"
