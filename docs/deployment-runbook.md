# Deployment Runbook - 1ai-social

**Last Updated:** 2026-04-16  
**Owner:** DevOps Team  
**Service:** 1ai-social Social Media Automation Engine

## Overview

This runbook covers deployment procedures for 1ai-social from staging to production, including pre-deployment checks, deployment steps, rollback procedures, and post-deployment verification.

## Pre-Deployment Checklist

### Code Quality
- [ ] All tests passing (`pytest tests/`)
- [ ] Code review approved
- [ ] No critical security vulnerabilities
- [ ] Linting passes (`ruff check .`)
- [ ] Type checking passes (if applicable)

### Database
- [ ] Database migrations tested in staging
- [ ] Migration rollback scripts prepared
- [ ] Database backup completed
- [ ] Migration execution time estimated (< 5 minutes acceptable)

### Configuration
- [ ] Environment variables reviewed and updated in `.env`
- [ ] API keys validated and active
- [ ] Rate limits configured appropriately
- [ ] Feature flags set correctly

### Dependencies
- [ ] `requirements.txt` updated
- [ ] Docker images built and tested
- [ ] External service dependencies verified (PostBridge, NVIDIA NIM, BytePlus, Groq)

### Monitoring
- [ ] Prometheus scraping configured
- [ ] Grafana dashboards updated
- [ ] Alert rules reviewed
- [ ] Log aggregation working

### Communication
- [ ] Deployment window scheduled
- [ ] Stakeholders notified
- [ ] Maintenance page ready (if needed)
- [ ] Rollback plan communicated

## Environment Variables Checklist

Verify these variables are set in production `.env`:

**Required:**
```bash
# API Keys
POSTBRIDGE_API_KEY=<production_key>
NVIDIA_API_KEY=<production_key>
BYTEPLUS_API_KEY=<production_key>
GROQ_API_KEY=<production_key>

# Database
DATABASE_URL=postgresql://<user>:<password>@postgres:5432/1ai_social

# Redis
REDIS_URL=redis://redis:6379/0

# Environment
ENVIRONMENT=production
```

**Optional (verify defaults):**
```bash
DEFAULT_PLATFORMS=tiktok,instagram
MAX_POSTS_PER_DAY=50
RATE_LIMIT_DELAY=60
ANALYTICS_RETENTION_DAYS=90
MCP_HOST=0.0.0.0
MCP_PORT=8000
```

## Deployment Steps

### Staging Deployment

1. **Pull latest code:**
   ```bash
   cd /home/openclaw/projects/1ai-social
   git fetch origin
   git checkout staging
   git pull origin staging
   ```

2. **Build Docker images:**
   ```bash
   docker-compose -f docker-compose.yml build
   ```

3. **Run database migrations:**
   ```bash
   # Backup first
   docker-compose exec postgres pg_dump -U $DB_USER $DB_NAME > backups/staging_$(date +%Y%m%d_%H%M%S).sql
   
   # Run migrations
   docker-compose run --rm app alembic upgrade head
   ```

4. **Start services:**
   ```bash
   docker-compose up -d
   ```

5. **Verify staging:**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Metrics check
   curl http://localhost:8000/metrics
   
   # Test post creation
   # (use staging API test suite)
   ```

6. **Smoke tests:**
   ```bash
   pytest tests/test_health.py
   pytest tests/test_api_keys.py
   ```

### Production Deployment

**Deployment Window:** Off-peak hours (2 AM - 4 AM UTC preferred)

1. **Pre-deployment backup:**
   ```bash
   # Database backup
   docker-compose -f docker-compose.prod.yml exec postgres \
     pg_dump -U $DB_USER $DB_NAME > backups/prod_$(date +%Y%m%d_%H%M%S).sql
   
   # Verify backup
   ls -lh backups/prod_*.sql | tail -1
   ```

2. **Pull production code:**
   ```bash
   cd /home/openclaw/projects/1ai-social
   git fetch origin
   git checkout main
   git pull origin main
   
   # Verify correct version
   git log -1 --oneline
   ```

3. **Build production images:**
   ```bash
   docker-compose -f docker-compose.prod.yml build --no-cache
   ```

4. **Stop current services (graceful):**
   ```bash
   # Allow 30 seconds for graceful shutdown
   docker-compose -f docker-compose.prod.yml stop -t 30
   ```

5. **Run database migrations:**
   ```bash
   # Dry run first (check what will be applied)
   docker-compose -f docker-compose.prod.yml run --rm app alembic current
   docker-compose -f docker-compose.prod.yml run --rm app alembic history
   
   # Apply migrations
   docker-compose -f docker-compose.prod.yml run --rm app alembic upgrade head
   
   # Verify migration success
   docker-compose -f docker-compose.prod.yml run --rm app alembic current
   ```

6. **Start production services:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

7. **Monitor startup:**
   ```bash
   # Watch logs
   docker-compose -f docker-compose.prod.yml logs -f --tail=100
   
   # Check container health
   docker-compose -f docker-compose.prod.yml ps
   ```

## Post-Deployment Verification

### Automated Checks (run immediately)

```bash
# Health endpoint
curl -f http://localhost:8000/health || echo "HEALTH CHECK FAILED"

# Metrics endpoint
curl -f http://localhost:8000/metrics | grep "http_requests_total" || echo "METRICS FAILED"

# Database connectivity
docker-compose -f docker-compose.prod.yml exec app python -c "from src.database import engine; engine.connect()" || echo "DB CONNECTION FAILED"

# Redis connectivity
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping || echo "REDIS FAILED"
```

### Manual Verification (5-10 minutes)

- [ ] Application responds to HTTP requests
- [ ] Database queries executing successfully
- [ ] Redis cache working
- [ ] Prometheus metrics being scraped
- [ ] Grafana dashboards showing data
- [ ] No error spikes in logs
- [ ] API key authentication working
- [ ] Rate limiting functioning
- [ ] Post scheduling working
- [ ] External API calls succeeding (PostBridge, NVIDIA, BytePlus, Groq)

### Monitoring Setup Verification

1. **Prometheus targets:**
   ```bash
   # Check Prometheus is scraping
   curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="1ai-social")'
   ```

2. **Grafana dashboards:**
   - Open Grafana: http://localhost:3000
   - Verify "1ai-social Dashboard" shows live data
   - Check for any red panels or alerts

3. **Alert rules:**
   ```bash
   # Check Prometheus alert rules
   curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.name | contains("1ai"))'
   ```

### Smoke Tests (15 minutes)

```bash
# Run critical path tests
pytest tests/test_health.py -v
pytest tests/test_api_keys.py -v
pytest tests/test_rate_limiter.py -v

# Test post creation (staging API key)
# Manual test via MCP or API client
```

## Rollback Procedures

### When to Rollback

Rollback immediately if:
- Health checks failing for > 2 minutes
- Error rate > 5% of requests
- Database connection failures
- Critical feature broken
- Data corruption detected

### Rollback Steps

**Option 1: Code Rollback (preferred, < 5 minutes)**

1. **Identify previous working version:**
   ```bash
   git log --oneline -10
   # Note the commit hash of last working deployment
   ```

2. **Checkout previous version:**
   ```bash
   git checkout <previous_commit_hash>
   ```

3. **Rebuild and restart:**
   ```bash
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Verify rollback:**
   ```bash
   curl http://localhost:8000/health
   docker-compose -f docker-compose.prod.yml logs -f --tail=50
   ```

**Option 2: Database Rollback (if migrations failed)**

1. **Stop application:**
   ```bash
   docker-compose -f docker-compose.prod.yml stop app
   ```

2. **Rollback migrations:**
   ```bash
   # Downgrade to previous revision
   docker-compose -f docker-compose.prod.yml run --rm app alembic downgrade -1
   
   # Or restore from backup
   docker-compose -f docker-compose.prod.yml exec postgres \
     psql -U $DB_USER -d $DB_NAME < backups/prod_<timestamp>.sql
   ```

3. **Restart with previous code:**
   ```bash
   git checkout <previous_commit_hash>
   docker-compose -f docker-compose.prod.yml up -d
   ```

**Option 3: Full System Restore (last resort, 10-15 minutes)**

1. **Stop all services:**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

2. **Restore database:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d postgres
   docker-compose -f docker-compose.prod.yml exec postgres \
     psql -U $DB_USER -d $DB_NAME < backups/prod_<timestamp>.sql
   ```

3. **Restore code:**
   ```bash
   git checkout <previous_commit_hash>
   docker-compose -f docker-compose.prod.yml build
   ```

4. **Start all services:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. **Verify restoration:**
   ```bash
   curl http://localhost:8000/health
   pytest tests/test_health.py
   ```

## Database Migration Steps

### Creating a Migration

```bash
# Auto-generate migration from model changes
docker-compose run --rm app alembic revision --autogenerate -m "description_of_changes"

# Manual migration (for complex changes)
docker-compose run --rm app alembic revision -m "description_of_changes"
# Edit the generated file in migrations/versions/
```

### Testing Migrations

```bash
# Test upgrade
docker-compose run --rm app alembic upgrade head

# Test downgrade
docker-compose run --rm app alembic downgrade -1

# Test full cycle
docker-compose run --rm app alembic downgrade base
docker-compose run --rm app alembic upgrade head
```

### Migration Best Practices

- Always test migrations in staging first
- Keep migrations small and focused
- Write both upgrade and downgrade functions
- Add data migrations separately from schema changes
- Avoid long-running migrations (> 5 minutes)
- Use `op.batch_alter_table()` for SQLite compatibility
- Add indexes in separate migrations

## Common Deployment Issues and Fixes

### Issue: Container fails to start

**Symptoms:** Container exits immediately, `docker ps` shows no running container

**Diagnosis:**
```bash
docker-compose -f docker-compose.prod.yml logs app
docker-compose -f docker-compose.prod.yml ps
```

**Fixes:**
- Check environment variables are set correctly
- Verify database connection string
- Check for port conflicts
- Review application logs for startup errors

### Issue: Database migration fails

**Symptoms:** `alembic upgrade head` returns error

**Diagnosis:**
```bash
docker-compose -f docker-compose.prod.yml run --rm app alembic current
docker-compose -f docker-compose.prod.yml logs postgres
```

**Fixes:**
- Check database connectivity
- Verify migration script syntax
- Rollback to previous version: `alembic downgrade -1`
- Restore from backup if data corrupted

### Issue: High memory usage

**Symptoms:** Container OOM killed, slow response times

**Diagnosis:**
```bash
docker stats
docker-compose -f docker-compose.prod.yml logs app | grep -i "memory"
```

**Fixes:**
- Increase memory limits in `docker-compose.prod.yml`
- Check for memory leaks in application code
- Restart services to clear memory
- Scale horizontally if needed

### Issue: External API calls failing

**Symptoms:** Posts not publishing, video generation failing

**Diagnosis:**
```bash
# Check API key validity
curl -H "Authorization: Bearer $POSTBRIDGE_API_KEY" https://api.postbridge.com/health

# Check logs for API errors
docker-compose -f docker-compose.prod.yml logs app | grep -i "api error"
```

**Fixes:**
- Verify API keys are correct and active
- Check rate limits on external services
- Verify network connectivity
- Review API endpoint URLs

### Issue: Redis connection lost

**Symptoms:** Cache misses, rate limiting not working

**Diagnosis:**
```bash
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
docker-compose -f docker-compose.prod.yml logs redis
```

**Fixes:**
- Restart Redis: `docker-compose -f docker-compose.prod.yml restart redis`
- Check Redis memory usage
- Verify Redis URL in environment variables
- Check for network issues

### Issue: Prometheus not scraping metrics

**Symptoms:** Grafana dashboards empty, no metrics data

**Diagnosis:**
```bash
curl http://localhost:9090/api/v1/targets
curl http://localhost:8000/metrics
```

**Fixes:**
- Verify `/metrics` endpoint is accessible
- Check Prometheus configuration in `prometheus.yml`
- Restart Prometheus
- Verify network connectivity between containers

## Post-Deployment Tasks

### Immediate (within 1 hour)
- [ ] Monitor error rates in Grafana
- [ ] Check application logs for warnings
- [ ] Verify scheduled posts are running
- [ ] Test critical user flows
- [ ] Update deployment log

### Short-term (within 24 hours)
- [ ] Review performance metrics
- [ ] Check for any user-reported issues
- [ ] Verify analytics data collection
- [ ] Update documentation if needed
- [ ] Schedule post-deployment review

### Documentation
- [ ] Update CHANGELOG.md
- [ ] Document any configuration changes
- [ ] Update runbook with lessons learned
- [ ] Share deployment summary with team

## Emergency Contacts

- **On-Call Engineer:** Check PagerDuty rotation
- **Database Admin:** [Contact info]
- **DevOps Lead:** [Contact info]
- **Product Owner:** [Contact info]

## Related Documentation

- [Incident Response Playbook](./incident-response.md)
- [Security Runbook](./security-runbook.md)
- [API Documentation](./api/)
- [Monitoring Setup](../README.md#monitoring)
