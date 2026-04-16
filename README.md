# 1ai-social

Social Media Automation Engine for BerkahKarya.

## Features

1. **Scheduling**: Schedule posts across X, Instagram, TikTok, LinkedIn.
2. **Planning**: Content calendar and planning.
3. **Engagement**: Automated likes, comments, follows, DMs.
4. **Analytics**: Track reach, engagement, follower growth.
5. **Multi-platform**: Single workflow, distribute everywhere.

## Supported Platforms

- X (Twitter)
- Instagram
- TikTok
- LinkedIn
- Facebook
- YouTube

## Directory Structure

- `scripts/`: Automation scripts
- `data/`: Content database
- `logs/`: Execution logs

## Usage

```bash
# Schedule a post
python3 scripts/scheduler.py --platform x --content "Hello world"

# Run engagement routine
python3 scripts/engagement.py --action like --count 20

# Generate content plan
python3 scripts/planner.py --niche "AI" --days 7
```

## Integration

Connects with:
- `1ai-ads` - Paid amplification
- `1ai-engage` - Cold outreach
- `berkahkarya-hub` - Orchestration

## Monitoring

### Prometheus Metrics

The application exposes Prometheus metrics at the `/metrics` endpoint via the MCP server.

**Standard HTTP Metrics:**
- `http_requests_total` - Total HTTP requests (labels: method, endpoint, status)
- `http_request_duration_seconds` - HTTP request latency histogram (labels: method, endpoint)
- `http_request_errors_total` - Total HTTP errors (labels: method, endpoint, error_type)

**Business Metrics:**
- `posts_published_total` - Total posts published (labels: platform, status)
- `api_calls_total` - API calls to social platforms (labels: platform, endpoint)
- `active_users_gauge` - Number of active users
- `platform_errors_total` - Platform-specific errors (labels: platform, error_type)
- `content_generated_total` - Content items generated (labels: niche, content_type)
- `video_render_duration_seconds` - Video rendering duration histogram (labels: template)
- `queue_size_gauge` - Current queue size
- `queue_failed_gauge` - Failed queue items
- `post_views_total` - Total post views (labels: platform, post_id)
- `post_engagement_total` - Post engagements (labels: platform, engagement_type)

**Access Metrics:**
```bash
# Via MCP tool
get_metrics()

# Returns Prometheus text format output
```

**Prometheus Setup:**
```bash
# Start Prometheus with provided config
prometheus --config.file=prometheus.yml

# Prometheus will scrape metrics from localhost:8000/metrics every 10s
```

**Grafana Dashboard:**
Import `grafana/dashboard.json` to visualize:
- HTTP request rates and latency
- Posts published by platform
- Platform API calls
- Active users and queue status
- Error rates and platform errors
- Content generation and video rendering metrics
- Post engagement metrics
