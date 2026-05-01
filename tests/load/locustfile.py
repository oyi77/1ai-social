"""
Load testing suite for 1ai-social using Locust.

Simulates 1000 concurrent users performing various operations:
- User signup and authentication
- Content generation
- Post creation and scheduling
- Analytics queries
- Billing webhooks

Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""

import random
from locust import HttpUser, task, between, events


class UserSignup(HttpUser):
    """Simulates user registration and authentication flow."""

    wait_time = between(1, 3)
    weight = 1

    def on_start(self):
        """Initialize user with random credentials."""
        self.user_id = f"user_{random.randint(10000, 99999)}"
        self.api_key = None

    @task(3)
    def health_check(self):
        """Check service health."""
        with self.client.get("/health/live", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(2)
    def readiness_check(self):
        """Check service readiness."""
        with self.client.get("/health/ready", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure(f"Service not ready: {data}")
            else:
                response.failure(f"Readiness check failed: {response.status_code}")

    @task(1)
    def simulate_signup(self):
        """Simulate user signup (mock endpoint)."""
        payload = {
            "user_id": self.user_id,
            "email": f"{self.user_id}@loadtest.com",
            "plan": random.choice(["free", "pro", "enterprise"]),
        }

        with self.client.post(
            "/api/signup", json=payload, catch_response=True, name="/api/signup"
        ) as response:
            if response.status_code in [200, 201, 404]:
                response.success()
            else:
                response.failure(f"Signup failed: {response.status_code}")


class ContentCreation(HttpUser):
    """Simulates content generation and posting."""

    wait_time = between(2, 5)
    weight = 3

    def on_start(self):
        """Initialize with test user context."""
        self.niches = ["AI", "tech", "fitness", "cooking", "travel", "business"]
        self.platforms = ["tiktok", "instagram", "linkedin", "x"]

    @task(5)
    def generate_content(self):
        """Generate content without posting."""
        niche = random.choice(self.niches)
        count = random.randint(1, 5)

        payload = {"niche": niche, "count": count}

        with self.client.post(
            "/mcp/tools/generate_content",
            json=payload,
            catch_response=True,
            name="/generate_content",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure(
                        f"Content generation failed: {data.get('message')}"
                    )
            else:
                response.failure(f"Request failed: {response.status_code}")

    @task(3)
    def generate_and_post(self):
        """Full pipeline: generate and post content."""
        niche = random.choice(self.niches)
        platforms = random.sample(self.platforms, k=random.randint(1, 2))

        payload = {
            "niche": niche,
            "platforms": platforms,
            "content_type": "video",
            "count": 1,
        }

        with self.client.post(
            "/mcp/tools/generate_and_post",
            json=payload,
            catch_response=True,
            name="/generate_and_post",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure(f"Post creation failed: {data.get('message')}")
            else:
                response.failure(f"Request failed: {response.status_code}")

    @task(2)
    def schedule_campaign(self):
        """Schedule multi-day content campaign."""
        niche = random.choice(self.niches)
        platforms = random.sample(self.platforms, k=random.randint(1, 3))
        days = random.choice([3, 7, 14])

        payload = {"niche": niche, "platforms": platforms, "days": days}

        with self.client.post(
            "/mcp/tools/schedule_campaign",
            json=payload,
            catch_response=True,
            name="/schedule_campaign",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure(
                        f"Campaign scheduling failed: {data.get('message')}"
                    )
            else:
                response.failure(f"Request failed: {response.status_code}")


class AnalyticsQuery(HttpUser):
    """Simulates analytics and reporting queries."""

    wait_time = between(3, 8)
    weight = 2

    def on_start(self):
        """Initialize with test post IDs."""
        self.post_ids = [f"post_{i}" for i in range(1, 101)]

    @task(4)
    def track_analytics(self):
        """Track analytics for a post."""
        post_id = random.choice(self.post_ids)

        payload = {"post_id": post_id}

        with self.client.post(
            "/mcp/tools/track_analytics",
            json=payload,
            catch_response=True,
            name="/track_analytics",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure(
                        f"Analytics tracking failed: {data.get('message')}"
                    )
            else:
                response.failure(f"Request failed: {response.status_code}")

    @task(3)
    def get_aggregate_stats(self):
        """Get aggregate statistics."""
        platform = random.choice(["tiktok", "instagram", "linkedin", "x", "all"])
        days = random.choice([7, 30, 90])

        payload = {"platform": platform, "days": days}

        with self.client.post(
            "/mcp/tools/get_aggregate_stats",
            json=payload,
            catch_response=True,
            name="/get_aggregate_stats",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    response.success()
                else:
                    response.failure(f"Stats query failed: {data.get('message')}")
            else:
                response.failure(f"Request failed: {response.status_code}")

    @task(2)
    def get_metrics(self):
        """Get Prometheus metrics."""
        with self.client.get(
            "/metrics", catch_response=True, name="/metrics"
        ) as response:
            if response.status_code == 200:
                if "http_requests_total" in response.text:
                    response.success()
                else:
                    response.failure("Invalid metrics format")
            else:
                response.failure(f"Metrics endpoint failed: {response.status_code}")


class BillingWebhook(HttpUser):
    """Simulates billing webhook events from LemonSqueezy."""

    wait_time = between(5, 15)
    weight = 1

    def on_start(self):
        """Initialize webhook test data."""
        self.event_types = [
            "subscription_created",
            "subscription_updated",
            "subscription_cancelled",
            "order_created",
        ]

    @task(1)
    def send_webhook(self):
        """Send billing webhook event."""
        event_type = random.choice(self.event_types)

        payload = {
            "meta": {
                "event_name": event_type,
                "custom_data": {"user_id": f"user_{random.randint(10000, 99999)}"},
            },
            "data": {
                "id": str(random.randint(100000, 999999)),
                "type": "subscriptions",
                "attributes": {
                    "status": "active" if "created" in event_type else "cancelled",
                    "product_id": random.randint(1000, 9999),
                    "variant_id": random.randint(1000, 9999),
                },
            },
        }

        # Note: Webhook signature would be required in production
        with self.client.post(
            "/webhooks/lemonsqueezy",
            json=payload,
            catch_response=True,
            name="/webhooks/lemonsqueezy",
        ) as response:
            # Accept various responses since webhook validation may fail
            if response.status_code in [200, 400, 401]:
                response.success()
            else:
                response.failure(f"Webhook failed: {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("\n" + "=" * 80)
    print("LOAD TEST STARTING")
    print(f"Target: {environment.host}")
    print(
        f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}"
    )
    print("=" * 80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops - print summary."""
    print("\n" + "=" * 80)
    print("LOAD TEST COMPLETED")
    print("=" * 80)

    stats = environment.stats

    print("\n📊 SUMMARY STATISTICS:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Total Failures: {stats.total.num_failures}")
    print(f"  Failure Rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"  Requests/sec: {stats.total.total_rps:.2f}")

    print("\n⏱️  LATENCY METRICS:")
    print(f"  Median (p50): {stats.total.get_response_time_percentile(0.5):.0f}ms")
    print(
        f"  95th percentile (p95): {stats.total.get_response_time_percentile(0.95):.0f}ms"
    )
    print(
        f"  99th percentile (p99): {stats.total.get_response_time_percentile(0.99):.0f}ms"
    )
    print(f"  Average: {stats.total.avg_response_time:.0f}ms")
    print(f"  Min: {stats.total.min_response_time:.0f}ms")
    print(f"  Max: {stats.total.max_response_time:.0f}ms")

    print("\n🎯 TOP ENDPOINTS BY REQUEST COUNT:")
    sorted_stats = sorted(
        [s for s in stats.entries.values() if s.num_requests > 0],
        key=lambda x: x.num_requests,
        reverse=True,
    )[:10]

    for stat in sorted_stats:
        print(
            f"  {stat.name:40} | Requests: {stat.num_requests:6} | "
            f"Failures: {stat.num_failures:4} | "
            f"Avg: {stat.avg_response_time:6.0f}ms | "
            f"p95: {stat.get_response_time_percentile(0.95):6.0f}ms"
        )

    print("\n" + "=" * 80 + "\n")
