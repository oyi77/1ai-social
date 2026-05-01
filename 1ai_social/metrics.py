"""Prometheus metrics for 1ai-social monitoring."""

import logging

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

logger = logging.getLogger(__name__)

# Standard HTTP Metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_request_errors_total = Counter(
    "http_request_errors_total",
    "Total HTTP request errors",
    ["method", "endpoint", "error_type"],
)

# Business Metrics
posts_published_total = Counter(
    "posts_published_total", "Total posts published", ["platform", "status"]
)

api_calls_total = Counter(
    "api_calls_total", "Total API calls to social platforms", ["platform", "endpoint"]
)

active_users_gauge = Gauge("active_users_gauge", "Number of active users")

platform_errors_total = Counter(
    "platform_errors_total",
    "Total platform-specific errors",
    ["platform", "error_type"],
)

# Content Generation Metrics
content_generated_total = Counter(
    "content_generated_total",
    "Total content items generated",
    ["niche", "content_type"],
)

video_render_duration_seconds = Histogram(
    "video_render_duration_seconds",
    "Video rendering duration in seconds",
    ["template"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

# Queue Metrics
queue_size_gauge = Gauge("queue_size_gauge", "Current queue size")

queue_failed_gauge = Gauge("queue_failed_gauge", "Number of failed items in queue")

# Analytics Metrics
post_views_total = Counter(
    "post_views_total", "Total post views", ["platform", "post_id"]
)

post_engagement_total = Counter(
    "post_engagement_total",
    "Total post engagements (likes, comments, shares)",
    ["platform", "engagement_type"],
)


class MetricsCollector:
    """Centralized metrics collection and reporting."""

    @staticmethod
    def record_http_request(method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics."""
        http_requests_total.labels(
            method=method, endpoint=endpoint, status=str(status)
        ).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )

    @staticmethod
    def record_http_error(method: str, endpoint: str, error_type: str):
        """Record HTTP error."""
        http_request_errors_total.labels(
            method=method, endpoint=endpoint, error_type=error_type
        ).inc()

    @staticmethod
    def record_post_published(platform: str, status: str):
        """Record post publication."""
        posts_published_total.labels(platform=platform, status=status).inc()

    @staticmethod
    def record_api_call(platform: str, endpoint: str):
        """Record API call to social platform."""
        api_calls_total.labels(platform=platform, endpoint=endpoint).inc()

    @staticmethod
    def set_active_users(count: int):
        """Set active users gauge."""
        active_users_gauge.set(count)

    @staticmethod
    def record_platform_error(platform: str, error_type: str):
        """Record platform-specific error."""
        platform_errors_total.labels(platform=platform, error_type=error_type).inc()

    @staticmethod
    def record_content_generated(niche: str, content_type: str):
        """Record content generation."""
        content_generated_total.labels(niche=niche, content_type=content_type).inc()

    @staticmethod
    def record_video_render(template: str, duration: float):
        """Record video rendering duration."""
        video_render_duration_seconds.labels(template=template).observe(duration)

    @staticmethod
    def set_queue_size(size: int):
        """Set queue size gauge."""
        queue_size_gauge.set(size)

    @staticmethod
    def set_queue_failed(count: int):
        """Set failed queue items gauge."""
        queue_failed_gauge.set(count)

    @staticmethod
    def record_post_views(platform: str, post_id: str, views: int):
        """Record post views."""
        post_views_total.labels(platform=platform, post_id=post_id).inc(views)

    @staticmethod
    def record_engagement(platform: str, engagement_type: str, count: int = 1):
        """Record post engagement."""
        post_engagement_total.labels(
            platform=platform, engagement_type=engagement_type
        ).inc(count)

    @staticmethod
    def get_metrics() -> tuple[bytes, str]:
        """Generate Prometheus metrics output."""
        return generate_latest(), CONTENT_TYPE_LATEST


# Global metrics collector instance
metrics = MetricsCollector()
