# Load Testing Results

## Test Configuration
- **Target**: 1000 concurrent users
- **Ramp-up**: 60 seconds (16.67 users/sec spawn rate)
- **Duration**: 5 minutes
- **Tool**: Locust 2.15.0+

## User Scenarios

### 1. UserSignup (Weight: 1)
Simulates user registration and authentication flow.
- Health checks
- Readiness checks
- User signup requests

### 2. ContentCreation (Weight: 3)
Simulates content generation and posting operations.
- Generate content without posting
- Generate and post content
- Schedule multi-day campaigns

### 3. AnalyticsQuery (Weight: 2)
Simulates analytics and reporting queries.
- Track post analytics
- Get aggregate statistics
- Fetch Prometheus metrics

### 4. BillingWebhook (Weight: 1)
Simulates billing webhook events from LemonSqueezy.
- Subscription created/updated/cancelled
- Order created events

## How to Run

### Prerequisites
```bash
pip install -r requirements.txt
```

### Start the Service
```bash
python -m 1ai_social
```

### Run Load Test
```bash
# Default: 1000 users, 60s ramp-up, 5min duration
./tests/load/run_load_test.sh

# Custom configuration
HOST=http://localhost:8000 USERS=500 RUN_TIME=3m ./tests/load/run_load_test.sh
```

### Environment Variables
- `HOST`: Target host (default: http://localhost:8000)
- `USERS`: Number of concurrent users (default: 1000)
- `SPAWN_RATE`: Users spawned per second (default: 16.67 for 60s ramp-up)
- `RUN_TIME`: Test duration (default: 5m)

## Expected Metrics

### Performance Targets
- **Requests/sec**: > 100 rps
- **Latency p50**: < 200ms
- **Latency p95**: < 500ms
- **Latency p99**: < 1000ms
- **Error Rate**: < 1%

### Key Endpoints
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe
- `/mcp/tools/generate_content` - Content generation
- `/mcp/tools/generate_and_post` - Full pipeline
- `/mcp/tools/schedule_campaign` - Campaign scheduling
- `/mcp/tools/track_analytics` - Analytics tracking
- `/mcp/tools/get_aggregate_stats` - Aggregate statistics
- `/metrics` - Prometheus metrics
- `/webhooks/lemonsqueezy` - Billing webhooks

## Results Location
All test results are saved to `tests/load/results/`:
- `report_TIMESTAMP.html` - Interactive HTML report
- `stats_TIMESTAMP_stats.csv` - Request statistics
- `stats_TIMESTAMP_failures.csv` - Failure details
- `stats_TIMESTAMP_exceptions.csv` - Exception details

## Interpreting Results

### Success Criteria
✅ System handles 1000 concurrent users
✅ Error rate < 1%
✅ p95 latency < 500ms
✅ No service crashes or timeouts

### Warning Signs
⚠️ Error rate > 5%
⚠️ p95 latency > 1000ms
⚠️ Increasing response times over test duration
⚠️ Database connection pool exhaustion

### Failure Indicators
❌ Service crashes or becomes unresponsive
❌ Error rate > 10%
❌ p99 latency > 5000ms
❌ Memory leaks or resource exhaustion

## Troubleshooting

### High Latency
- Check database query performance
- Review connection pool settings
- Monitor CPU and memory usage
- Check for N+1 queries

### High Error Rate
- Review application logs
- Check database connectivity
- Verify rate limiting configuration
- Monitor external API dependencies

### Resource Exhaustion
- Increase database connection pool size
- Scale Redis cache
- Add more application instances
- Optimize memory usage

## Next Steps

1. **Baseline Test**: Run initial test to establish baseline metrics
2. **Optimization**: Identify and fix bottlenecks
3. **Regression Testing**: Run after each major change
4. **Stress Testing**: Gradually increase load beyond 1000 users
5. **Soak Testing**: Run for extended periods (1+ hours)
