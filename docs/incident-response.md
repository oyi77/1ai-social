# Incident Response Playbook - 1ai-social

**Project:** 1ai-social  
**Version:** 1.0  
**Last Updated:** 2026-04-16  
**Owner:** Operations Team

---

## Table of Contents

1. [Overview](#overview)
2. [Severity Levels](#severity-levels)
3. [Escalation Matrix](#escalation-matrix)
4. [Response Procedures](#response-procedures)
5. [Incident Playbooks](#incident-playbooks)
6. [Communication Templates](#communication-templates)
7. [Post-Mortem Template](#post-mortem-template)
8. [Runbook References](#runbook-references)

---

## Overview

This playbook provides structured procedures for responding to operational incidents in the 1ai-social platform. It covers detection, triage, containment, recovery, and post-incident activities.

### Objectives

- Minimize user impact and service downtime
- Establish clear communication during incidents
- Enable rapid decision-making through defined escalation paths
- Preserve evidence for root cause analysis
- Improve systems through post-incident reviews

### Scope

This playbook covers:
- Infrastructure incidents (database, Redis, Docker)
- Application incidents (crashes, memory leaks, hangs)
- External service failures (PostBridge, NVIDIA NIM, BytePlus, Groq)
- Payment processing failures (LemonSqueezy)
- Authentication and authorization failures
- Data integrity issues
- Performance degradation

---

## Severity Levels

### P1 - Critical (Response Time: Immediate)

**Definition:** Complete service outage or severe data loss affecting all users.

**Examples:**
- Production database completely down
- Application unable to start or crashing on startup
- All payment processing failing
- Complete authentication system failure
- Active data corruption or loss
- Security breach in progress

**Response:**
- Page on-call engineer immediately
- Declare SEV-1 incident
- Activate full incident response team
- Begin status page updates every 5 minutes
- Escalate to CTO within 5 minutes if not resolved

---

### P2 - High (Response Time: 1 hour)

**Definition:** Significant service degradation affecting multiple users or critical features.

**Examples:**
- Database intermittently unavailable (>30 seconds downtime)
- Post publishing failing for >10% of requests
- Video generation service down
- Payment processing failing for specific payment methods
- Authentication working but with high latency (>5 seconds)
- Memory leak causing gradual performance degradation

**Response:**
- Page on-call engineer
- Declare SEV-2 incident
- Activate incident commander
- Begin status page updates every 15 minutes
- Escalate to Engineering Manager if not resolved within 30 minutes

---

### P3 - Medium (Response Time: 4 hours)

**Definition:** Minor service issues affecting small subset of users or non-critical features.

**Examples:**
- Single platform integration failing (e.g., TikTok only)
- Analytics data delayed by >1 hour
- Rate limiting too aggressive
- Scheduled posts delayed by <30 minutes
- Non-critical API endpoints returning errors
- Monitoring/alerting system issues

**Response:**
- Create incident ticket
- Notify on-call engineer
- Begin status page updates every 30 minutes if user-facing
- Escalate to Engineering Manager if not resolved within 2 hours

---

### P4 - Low (Response Time: 24 hours)

**Definition:** Cosmetic issues or minor bugs with no user impact.

**Examples:**
- UI display glitches
- Non-critical log errors
- Documentation outdated
- Unused feature broken
- Development environment issues

**Response:**
- Create ticket in backlog
- No immediate escalation required
- Address during next sprint planning

---

## Escalation Matrix

### On-Call Rotation

**Primary On-Call Engineer**
- Responsible for: Initial triage, containment, coordination
- Availability: 24/7 during on-call week
- Escalation: To Tech Lead if unable to resolve within 30 minutes (P1/P2)

**Tech Lead**
- Responsible for: Technical decisions, architecture guidance
- Availability: Business hours + on-call rotation
- Escalation: To Engineering Manager for P1 incidents

**Engineering Manager**
- Responsible for: Resource allocation, stakeholder communication
- Availability: Business hours
- Escalation: To CTO for P1 incidents or if >1 hour unresolved

**CTO**
- Responsible for: Executive decisions, customer communication
- Availability: On-call for P1 incidents
- Escalation: To CEO for P1 incidents affecting paying customers

### Escalation Triggers

| Severity | Time to Escalate | Escalate To |
|----------|------------------|-------------|
| P1 | 5 minutes | Tech Lead |
| P1 | 15 minutes | Engineering Manager |
| P1 | 30 minutes | CTO |
| P2 | 30 minutes | Tech Lead |
| P2 | 60 minutes | Engineering Manager |
| P3 | 120 minutes | Engineering Manager |

### Contact Information Template

```
On-Call Engineer: [Name] - [Phone] - [Slack]
Tech Lead: [Name] - [Phone] - [Slack]
Engineering Manager: [Name] - [Phone] - [Slack]
CTO: [Name] - [Phone] - [Slack]
```

---

## Response Procedures

### Phase 1: Detection & Triage (0-15 minutes)

#### 1.1 Incident Detection

Incidents may be detected through:
- Prometheus alerts (configured in monitoring)
- Grafana dashboard anomalies
- User reports via support channels
- Automated health checks
- Manual observation

#### 1.2 Initial Assessment

**Immediately upon detection:**

```bash
# Check application health
curl -s http://localhost:8000/health/ready | jq .

# Check recent error logs
docker-compose logs --tail=100 app | grep -i error

# Check container status
docker-compose ps

# Check database connectivity
docker-compose exec app python -c "from src.database import engine; engine.connect()"

# Check Redis connectivity
docker-compose exec redis redis-cli ping

# Check system resources
docker stats --no-stream
```

#### 1.3 Severity Classification

Determine incident severity using the matrix above. Document:
- Incident ID (auto-generated or manual)
- Severity level (P1-P4)
- Affected component(s)
- Estimated user impact
- Detection time

#### 1.4 Incident Commander Assignment

For P1/P2 incidents:
- Assign incident commander (usually on-call engineer)
- Create incident channel in Slack
- Invite relevant team members
- Post initial assessment

---

### Phase 2: Containment (15-60 minutes)

#### 2.1 Immediate Actions

**For Database Issues:**
```bash
# Check database status
docker-compose exec postgres pg_isready

# Check active connections
docker-compose exec postgres psql -U 1ai -d 1ai_social -c \
  "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# Check disk space
docker-compose exec postgres df -h

# Check slow queries
docker-compose exec postgres psql -U 1ai -d 1ai_social -c \
  "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

**For Application Crashes:**
```bash
# Restart application
docker-compose restart app

# Monitor startup
docker-compose logs -f app

# Verify health after restart
curl http://localhost:8000/health/ready
```

**For Memory Issues:**
```bash
# Check memory usage
docker stats app --no-stream

# Check for memory leaks in logs
docker-compose logs app | grep -i "memory\|oom"

# Restart if necessary
docker-compose restart app
```

**For External Service Failures:**
```bash
# Check service connectivity
curl -s https://api.postbridge.com/health
curl -s https://api.nvidia.com/health

# Verify API keys
echo $POSTBRIDGE_API_KEY
echo $NVIDIA_API_KEY

# Check rate limits
redis-cli HGETALL "ratelimit:external:postbridge"
```

**For Payment Processing Failures:**
```bash
# Check LemonSqueezy webhook status
docker-compose logs app | grep -i "lemonsqueezy\|webhook"

# Verify webhook secret
echo $LEMONSQUEEZY_WEBHOOK_SECRET

# Check payment queue
docker-compose exec app python -c \
  "from src.models import PaymentQueue; print(PaymentQueue.query.filter_by(status='pending').count())"
```

#### 2.2 Communication

- Post initial status to status page (if user-facing)
- Notify stakeholders in incident channel
- Set update frequency based on severity
- Prepare customer communication template

#### 2.3 Evidence Preservation

```bash
# Export logs
docker-compose logs --timestamps app > /tmp/incident-logs-$(date +%s).txt

# Export metrics
curl http://localhost:9090/api/v1/query?query=up | jq . > /tmp/incident-metrics-$(date +%s).json

# Export database state (if applicable)
docker-compose exec postgres pg_dump -U 1ai -d 1ai_social > /tmp/incident-db-$(date +%s).sql

# Archive evidence
tar -czf /tmp/incident-evidence-$(date +%s).tar.gz /tmp/incident-*
```

---

### Phase 3: Eradication (1-4 hours)

#### 3.1 Root Cause Analysis

- Identify what failed
- Identify why it failed
- Identify contributing factors
- Document timeline

#### 3.2 Remediation

**For Database Issues:**
- Run VACUUM and ANALYZE if needed
- Check for table bloat
- Optimize slow queries
- Increase connection pool if needed

**For Application Issues:**
- Deploy fix or rollback to previous version
- See [Deployment Runbook](./deployment-runbook.md) for rollback procedures

**For External Service Issues:**
- Implement fallback/retry logic
- Queue failed requests for retry
- Notify external service provider if their issue

**For Payment Issues:**
- Manually process failed payments if needed
- Verify webhook configuration
- Test webhook delivery

#### 3.3 Verification

```bash
# Verify fix is working
curl http://localhost:8000/health/ready

# Check error rates
curl http://localhost:9090/api/v1/query?query=rate(http_requests_total%5B5m%5D)

# Run smoke tests
pytest tests/test_health.py -v
pytest tests/test_api_keys.py -v

# Monitor for 10 minutes
watch -n 5 'docker stats --no-stream'
```

---

### Phase 4: Recovery (4-24 hours)

#### 4.1 Service Restoration

- Verify all systems operational
- Confirm no data loss
- Check for cascading failures
- Monitor error rates

#### 4.2 Performance Verification

```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Check database performance
docker-compose exec postgres psql -U 1ai -d 1ai_social -c \
  "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC;"

# Check queue status
docker-compose exec app python -c \
  "from src.models import Queue; print(f'Pending: {Queue.query.filter_by(status=\"pending\").count()}')"
```

#### 4.3 Communication

- Post resolution to status page
- Send customer notification email
- Update incident status to "Resolved"
- Schedule post-mortem meeting

---

### Phase 5: Post-Incident (24-72 hours)

#### 5.1 Post-Mortem Meeting

- Conduct within 48 hours of resolution
- Include incident commander, on-call engineer, tech lead
- Review timeline and actions taken
- Discuss root cause
- Identify action items

#### 5.2 Documentation

- Complete incident report (see template below)
- Update runbooks with lessons learned
- Document any configuration changes
- Update monitoring/alerting rules

#### 5.3 Follow-up Actions

- Implement preventive measures
- Update documentation
- Schedule training if needed
- Track action items to completion

---

## Incident Playbooks

### Playbook 1: Database Down

**Trigger:** Database health check failing, connection errors in logs

**Detection:**
```bash
curl http://localhost:8000/health/ready
# Returns: {"status": "unhealthy", "database": "down"}
```

**Immediate Actions (0-5 min):**
1. Declare P1 incident
2. Check if container is running: `docker-compose ps postgres`
3. Check logs: `docker-compose logs postgres`
4. Check disk space: `docker-compose exec postgres df -h`

**Containment (5-15 min):**
1. If container crashed, restart: `docker-compose restart postgres`
2. If disk full, archive old logs and backups
3. If corrupted, restore from backup (see [Backup Procedures](./BACKUP_PROCEDURES.md))

**Recovery (15-60 min):**
1. Verify database is accepting connections
2. Run integrity check: `docker-compose exec postgres psql -U 1ai -d 1ai_social -c "SELECT 1;"`
3. Check for table bloat: `docker-compose exec postgres psql -U 1ai -d 1ai_social -c "VACUUM ANALYZE;"`
4. Restart application: `docker-compose restart app`

**Verification:**
```bash
curl http://localhost:8000/health/ready
pytest tests/test_health.py -v
```

---

### Playbook 2: Application Crash

**Trigger:** Application container exiting, health check failing

**Detection:**
```bash
docker-compose ps app
# Shows: Exit code non-zero
```

**Immediate Actions (0-5 min):**
1. Declare P1 incident
2. Check logs: `docker-compose logs app | tail -50`
3. Check for OOM: `docker-compose logs app | grep -i "oom\|memory"`

**Containment (5-15 min):**
1. If OOM, increase memory limit in docker-compose.yml
2. If startup error, check environment variables
3. If dependency issue, check external services

**Recovery (15-60 min):**
1. Restart application: `docker-compose restart app`
2. Monitor startup: `docker-compose logs -f app`
3. Verify health: `curl http://localhost:8000/health/ready`

**If restart fails:**
1. Rollback to previous version (see [Deployment Runbook](./deployment-runbook.md))
2. Or deploy fix if root cause identified

---

### Playbook 3: Payment Processing Failures

**Trigger:** Payment webhook errors, failed transactions in logs

**Detection:**
```bash
docker-compose logs app | grep -i "payment\|lemonsqueezy\|webhook"
```

**Immediate Actions (0-5 min):**
1. Declare P2 incident
2. Check webhook logs: `docker-compose logs app | grep webhook`
3. Verify webhook secret: `echo $LEMONSQUEEZY_WEBHOOK_SECRET`

**Containment (5-15 min):**
1. Check LemonSqueezy status page
2. Verify webhook endpoint is accessible
3. Check for rate limiting issues

**Recovery (15-60 min):**
1. Verify webhook configuration in LemonSqueezy dashboard
2. Test webhook delivery manually
3. Retry failed payments: `docker-compose exec app python scripts/retry_payments.py`

**Verification:**
```bash
# Check payment queue
docker-compose exec app python -c \
  "from src.models import PaymentQueue; print(PaymentQueue.query.filter_by(status='failed').count())"
```

---

### Playbook 4: Authentication Failures

**Trigger:** Login errors, OAuth failures, token validation errors

**Detection:**
```bash
docker-compose logs app | grep -i "auth\|oauth\|token"
```

**Immediate Actions (0-5 min):**
1. Declare P2 incident
2. Check OAuth provider status (X, Instagram, TikTok, LinkedIn)
3. Verify API keys: `echo $OAUTH_CLIENT_ID`

**Containment (5-15 min):**
1. Check if OAuth provider is down
2. Verify API keys are still valid
3. Check rate limits on OAuth endpoints

**Recovery (15-60 min):**
1. Rotate OAuth tokens if compromised
2. Update API keys if expired
3. Clear token cache: `redis-cli FLUSHDB` (if safe)

**Verification:**
```bash
# Test OAuth flow
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"provider": "x", "code": "test"}'
```

---

### Playbook 5: Data Breach or Unauthorized Access

**Trigger:** Suspicious access patterns, unauthorized data access, security alerts

**Detection:**
```bash
docker-compose logs app | grep -i "unauthorized\|forbidden\|breach"
```

**Immediate Actions (0-5 min):**
1. Declare P1 incident
2. Isolate affected systems if necessary
3. Preserve evidence: See Phase 2.3 above
4. Notify security team immediately

**Containment (5-15 min):**
1. Revoke compromised credentials
2. Rotate encryption keys (see [Security Runbook](./security-runbook.md))
3. Block suspicious IP addresses
4. Enable enhanced logging

**Recovery (1-4 hours):**
1. Investigate scope of breach
2. Notify affected users
3. Implement additional security measures
4. Follow compliance notification requirements

**Post-Incident:**
- Conduct security audit
- Update security policies
- Implement preventive measures
- Consider third-party security review

---

### Playbook 6: External Service Failures (PostBridge, NVIDIA, BytePlus, Groq)

**Trigger:** API errors, timeouts, service unavailable responses

**Detection:**
```bash
docker-compose logs app | grep -i "postbridge\|nvidia\|byteplus\|groq"
```

**Immediate Actions (0-5 min):**
1. Declare P2 incident
2. Check service status pages
3. Verify API keys and rate limits

**Containment (5-15 min):**
1. If service is down, queue requests for retry
2. Implement fallback behavior if available
3. Notify users of degraded functionality

**Recovery (15-60 min):**
1. Monitor service status for recovery
2. Retry queued requests
3. Verify service is fully operational

**Verification:**
```bash
# Test external service connectivity
curl -H "Authorization: Bearer $POSTBRIDGE_API_KEY" \
  https://api.postbridge.com/health
```

---

### Playbook 7: Performance Degradation

**Trigger:** Slow response times, high latency, timeouts

**Detection:**
```bash
# Check response times
curl -w "Time: %{time_total}s\n" http://localhost:8000/health

# Check Grafana dashboard for latency spikes
```

**Immediate Actions (0-5 min):**
1. Declare P3 incident
2. Check system resources: `docker stats`
3. Check database query performance

**Containment (5-15 min):**
1. Identify slow queries: See Phase 2.1 database section
2. Check for memory leaks
3. Check for connection pool exhaustion

**Recovery (15-60 min):**
1. Optimize slow queries
2. Increase resource limits if needed
3. Clear caches if safe
4. Restart services if necessary

**Verification:**
```bash
# Monitor response times
watch -n 5 'curl -w "Time: %{time_total}s\n" http://localhost:8000/health'
```

---

## Communication Templates

### Status Page Update - Investigating

```
🔴 INVESTIGATING: [Service Name] Performance Issues

We are currently investigating reports of [specific issue].
Our team is actively working to resolve this issue.

Last Updated: [TIME] UTC
```

### Status Page Update - Identified

```
🟡 IDENTIFIED: [Service Name] [Issue Description]

We have identified the root cause: [brief description]
We are implementing a fix and expect resolution within [timeframe].

Affected: [% of users/features]
Last Updated: [TIME] UTC
```

### Status Page Update - Resolved

```
✅ RESOLVED: [Service Name] [Issue Description]

The issue has been resolved. All systems are operating normally.
We apologize for the inconvenience.

Duration: [X minutes]
Last Updated: [TIME] UTC
```

### Customer Notification Email

```
Subject: [Service Name] Incident Report - [Date]

Dear [Customer],

We experienced an incident on [DATE] from [START TIME] to [END TIME] UTC.

**What Happened:**
[Brief description of incident]

**Impact:**
- Duration: [X minutes]
- Affected Users: [X%]
- Services Affected: [list]

**Root Cause:**
[Explanation of root cause]

**Actions Taken:**
- [Action 1]
- [Action 2]
- [Action 3]

**Prevention:**
We have implemented the following measures to prevent recurrence:
- [Preventive measure 1]
- [Preventive measure 2]

We apologize for the disruption and appreciate your patience.

Best regards,
[Company] Operations Team
```

### Internal Incident Notification

```
🚨 INCIDENT DECLARED: [Severity]

**Incident ID:** [ID]
**Severity:** [P1/P2/P3/P4]
**Service:** [Service Name]
**Status:** [Investigating/Identified/Resolved]

**Summary:**
[Brief description]

**Impact:**
[User impact, affected features]

**Timeline:**
- Detection: [TIME]
- Escalation: [TIME]
- Current Status: [TIME]

**Incident Commander:** [Name]
**Slack Channel:** #incident-[ID]

Please join the incident channel for updates.
```

---

## Post-Mortem Template

### Incident Post-Mortem Report

```markdown
# Incident Post-Mortem: [Incident ID]

**Date:** [DATE]
**Severity:** [P1/P2/P3/P4]
**Duration:** [START TIME] - [END TIME] UTC ([X minutes])
**Incident Commander:** [Name]

## Executive Summary

[1-2 sentence summary of what happened and impact]

## Timeline

| Time (UTC) | Event |
|-----------|-------|
| HH:MM | Detection: [What was observed] |
| HH:MM | Triage: [Severity determined] |
| HH:MM | Escalation: [Who was notified] |
| HH:MM | Containment: [Action taken] |
| HH:MM | Root Cause Identified: [What was found] |
| HH:MM | Fix Deployed: [What was changed] |
| HH:MM | Verification: [Confirmed working] |
| HH:MM | Resolution: [Incident closed] |

## Impact Assessment

**Users Affected:** [Number or percentage]
**Services Affected:** [List of services]
**Data Loss:** [Yes/No - if yes, describe]
**Revenue Impact:** [If applicable]

## Root Cause Analysis

### What Happened

[Detailed description of the incident]

### Why It Happened

[Root cause - the underlying reason]

### Contributing Factors

- [Factor 1]
- [Factor 2]
- [Factor 3]

## Actions Taken During Incident

1. [Action 1] - [Time] - [Owner]
2. [Action 2] - [Time] - [Owner]
3. [Action 3] - [Time] - [Owner]

## Lessons Learned

### What Went Well

- [Positive 1]
- [Positive 2]

### What Could Be Improved

- [Improvement 1]
- [Improvement 2]

## Action Items

| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| [Action 1] | [Name] | [Date] | High |
| [Action 2] | [Name] | [Date] | Medium |
| [Action 3] | [Name] | [Date] | Low |

## Prevention Measures

### Short-term (1-2 weeks)
- [Measure 1]
- [Measure 2]

### Long-term (1-3 months)
- [Measure 1]
- [Measure 2]

## Monitoring & Alerting Improvements

- [Alert 1] - [Description]
- [Alert 2] - [Description]

## Documentation Updates

- [ ] Update runbooks
- [ ] Update playbooks
- [ ] Update monitoring rules
- [ ] Update team wiki

## Sign-off

- **Incident Commander:** [Name] - [Date]
- **Tech Lead:** [Name] - [Date]
- **Engineering Manager:** [Name] - [Date]
```

---

## Runbook References

### Related Documentation

- **[Deployment Runbook](./deployment-runbook.md)** - Deployment procedures and rollback steps
- **[Backup Procedures](./BACKUP_PROCEDURES.md)** - Database backup and restore procedures
- **[Security Runbook](./security-runbook.md)** - Security incident response procedures
- **[README.md](../README.md#monitoring)** - Monitoring and alerting setup

### Quick Reference Commands

**Health Checks:**
```bash
curl http://localhost:8000/health/ready
curl http://localhost:8000/metrics
```

**Database:**
```bash
docker-compose exec postgres psql -U 1ai -d 1ai_social -c "SELECT 1;"
docker-compose exec postgres pg_isready
```

**Redis:**
```bash
docker-compose exec redis redis-cli ping
docker-compose exec redis redis-cli INFO
```

**Logs:**
```bash
docker-compose logs --tail=100 app
docker-compose logs --tail=100 postgres
docker-compose logs --tail=100 redis
```

**System Resources:**
```bash
docker stats --no-stream
docker-compose ps
```

---

## Incident Response Checklist

### During Incident

- [ ] Declare incident severity (P1-P4)
- [ ] Assign incident commander
- [ ] Create incident channel
- [ ] Notify on-call team
- [ ] Begin status page updates
- [ ] Preserve evidence
- [ ] Identify root cause
- [ ] Implement fix or rollback
- [ ] Verify resolution
- [ ] Update status page

### After Incident

- [ ] Schedule post-mortem (within 48 hours)
- [ ] Complete incident report
- [ ] Identify action items
- [ ] Update runbooks
- [ ] Update monitoring/alerting
- [ ] Communicate with customers
- [ ] Track action items to completion
- [ ] Archive incident evidence

---

**Document Control:**
- Version: 1.0
- Last Review: 2026-04-16
- Next Review: 2026-07-16
- Owner: Operations Team
