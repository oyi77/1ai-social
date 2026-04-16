# Security Incident Response Runbook

**Project:** 1ai-social  
**Version:** 1.0  
**Last Updated:** 2026-04-16  
**Owner:** Security Team

---

## Table of Contents

1. [Overview](#overview)
2. [Incident Classification](#incident-classification)
3. [Response Team](#response-team)
4. [Incident Response Procedures](#incident-response-procedures)
5. [Security Event Playbooks](#security-event-playbooks)
6. [Post-Incident Activities](#post-incident-activities)
7. [Appendix](#appendix)

---

## Overview

This runbook provides step-by-step procedures for responding to security incidents in the 1ai-social platform.

### Objectives
- Minimize impact of security incidents
- Preserve evidence for investigation
- Restore normal operations quickly
- Learn from incidents to prevent recurrence

### Scope
- Authentication breaches
- Data breaches
- API abuse and rate limit violations
- Webhook verification failures
- Encryption key compromises
- Dependency vulnerabilities

---

## Incident Classification

### Severity Levels

#### P0 - Critical (Response Time: Immediate)
- Active data breach or exfiltration
- Encryption key compromise
- Authentication system compromise
- Production system completely down
- Active exploitation of zero-day vulnerability

#### P1 - High (Response Time: 1 hour)
- Suspected data breach
- Multiple failed authentication attempts from single source
- Rate limit bypass detected
- Webhook signature verification failures
- Critical dependency vulnerability (CVSS 9.0+)

#### P2 - Medium (Response Time: 4 hours)
- Unusual API usage patterns
- Audit log integrity failures
- High dependency vulnerability (CVSS 7.0-8.9)
- Security header misconfiguration

#### P3 - Low (Response Time: 24 hours)
- Medium dependency vulnerability (CVSS 4.0-6.9)
- Non-critical security configuration issues
- Security documentation updates

---

## Response Team

### Primary Contacts

**Security Lead**
- Name: [TBD]
- Email: security-lead@berkahkarya.com
- Phone: [TBD]

**Engineering Manager**
- Name: [TBD]
- Email: eng-manager@berkahkarya.com
- Phone: [TBD]

**DevOps Lead**
- Name: [TBD]
- Email: devops-lead@berkahkarya.com
- Phone: [TBD]

### Escalation Path
1. On-call Engineer → Security Lead
2. Security Lead → Engineering Manager
3. Engineering Manager → CTO
4. CTO → CEO (for P0 incidents)

---

## Incident Response Procedures

### Phase 1: Detection & Triage (0-15 minutes)

#### 1.1 Incident Detection
Security incidents may be detected through:
- Prometheus alerts
- Audit log anomalies
- User reports
- Automated security scans

#### 1.2 Initial Assessment
```bash
# Check system health
curl http://localhost:8000/health/ready

# Check recent audit logs
psql -d 1ai_social -c "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 50;"

# Check rate limiter status
redis-cli --scan --pattern "ratelimit:*" | head -20
```

### Phase 2: Containment (15-60 minutes)

#### 2.1 Immediate Actions

**For Rate Limit Bypass:**
```bash
# Block IP address in Redis
redis-cli SET "blocked:ip:<IP_ADDRESS>" "1" EX 3600
```

**For Webhook Attacks:**
```bash
# Rotate webhook secret
export NEW_WEBHOOK_SECRET=$(openssl rand -base64 32)
aws secretsmanager update-secret --secret-id WEBHOOK_SECRET_<PROVIDER> --secret-string "$NEW_WEBHOOK_SECRET"
```

#### 2.2 Evidence Preservation
```bash
# Export audit logs
psql -d 1ai_social -c "COPY (SELECT * FROM audit_logs WHERE timestamp BETWEEN '<START>' AND '<END>') TO '/tmp/incident-audit.csv' CSV HEADER;"

# Archive evidence
tar -czf incident-evidence.tar.gz /tmp/incident-*
```

### Phase 3: Eradication (1-4 hours)

**For Encryption Key Compromise:**
```bash
# Generate new master key
NEW_KEY=$(openssl rand -base64 32)
aws secretsmanager update-secret --secret-id ENCRYPTION_MASTER_KEY --secret-string "$NEW_KEY"
```

**For Dependency Vulnerabilities:**
```bash
pip install --upgrade <package_name>
safety scan
pytest tests/
```

### Phase 4: Recovery (4-24 hours)

```bash
# Verify security measures
./scripts/security-verification.sh

# Restart services
systemctl restart 1ai-social
```

### Phase 5: Post-Incident (24-72 hours)

- Complete incident report
- Update security checklist
- Document lessons learned
- Notify affected users if applicable

---

## Security Event Playbooks

### Playbook 1: Failed Login Attempts

**Trigger:** >10 failed login attempts from single IP in 5 minutes

**Actions:**
```sql
SELECT ip_address, COUNT(*) as attempts
FROM audit_logs
WHERE action = 'failed_login' AND timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY ip_address HAVING COUNT(*) > 10;
```

### Playbook 2: Rate Limit Violations

**Trigger:** User exceeds rate limit by >200%

**Actions:**
```bash
redis-cli HGETALL "ratelimit:api:<USER_ID>:<ENDPOINT>"
```

### Playbook 3: Webhook Verification Failure

**Trigger:** Webhook signature verification fails

**Actions:**
1. Log the failure in audit logs
2. Check for replay attack
3. Verify webhook secret configuration
4. Contact provider if secret mismatch

### Playbook 4: Audit Log Integrity Failure

**Trigger:** HMAC signature verification fails

**Actions:**
```python
from 1ai_social.audit import AuditLogger
logger = AuditLogger(db, secret_key)
result = logger.verify_log_integrity()
```

### Playbook 5: Encryption Key Compromise

**Trigger:** Unauthorized access to AWS Secrets Manager

**Actions:**
1. Rotate master key immediately
2. Re-encrypt all credentials
3. Revoke all OAuth tokens
4. Force user re-authentication

### Playbook 6: Dependency Vulnerability

**Trigger:** Safety scan reports critical vulnerability

**Actions:**
```bash
safety scan --json
pip install --upgrade <package_name>
pytest tests/
```

---

## Post-Incident Activities

### Incident Report Template

```markdown
# Incident Report: <ID>

**Date:** <DATE>
**Severity:** <P0/P1/P2/P3>
**Status:** <Open/Resolved/Closed>

## Summary
[Brief description]

## Timeline
- Detection: <TIME>
- Containment: <TIME>
- Recovery: <TIME>

## Impact
- Users Affected: <COUNT>
- Data Compromised: <YES/NO>

## Root Cause
[Analysis]

## Actions Taken
1. [Action 1]
2. [Action 2]

## Lessons Learned
- [Lesson 1]
- [Lesson 2]
```

### Quarterly Security Review

**Schedule:** Every 3 months (Jan, Apr, Jul, Oct)

**Checklist:**
- [ ] Review all incidents from quarter
- [ ] Update security checklist
- [ ] Run full security audit
- [ ] Update dependency versions
- [ ] Rotate encryption keys
- [ ] Test incident response procedures

---

## Appendix

### A. Useful Commands

**Check Audit Logs:**
```bash
psql -d 1ai_social -c "SELECT * FROM audit_logs WHERE action = 'failed_login' ORDER BY timestamp DESC LIMIT 20;"
```

**Check Rate Limits:**
```bash
redis-cli --scan --pattern "ratelimit:*"
```

### B. Compliance Requirements

**Data Breach Notification:**
- GDPR: 72 hours
- CCPA: Without unreasonable delay

**Audit Log Retention:**
- Minimum: 1 year
- Recommended: 7 years

**Encryption Standards:**
- At Rest: AES-256-GCM
- In Transit: TLS 1.2+
- Key Rotation: Annually

### C. References

- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)

---

**Document Control:**
- Version: 1.0
- Last Review: 2026-04-16
- Next Review: 2026-07-16
- Owner: Security Team
