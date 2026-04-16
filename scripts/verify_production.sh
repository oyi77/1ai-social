#!/bin/bash
#
# Production Deployment Verification Script
# Verifies production deployment health and readiness
#

set -euo pipefail

# Configuration
DB_CONTAINER="${DB_CONTAINER:-1ai-social-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-1ai-social-redis}"
APP_CONTAINER="${APP_CONTAINER:-1ai-social-app}"
DB_NAME="${DB_NAME:-1ai_social}"
DB_USER="${DB_USER:-1ai}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-http://localhost:8000/health}"
LOG_FILE="${LOG_FILE:-./logs/verify_production.log}"

# Ensure directories exist
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Success counter
CHECKS_PASSED=0
CHECKS_FAILED=0

# Check function
check() {
    local name="$1"
    local command="$2"
    
    if eval "$command" > /dev/null 2>&1; then
        log "✓ PASS: $name"
        ((CHECKS_PASSED++))
        return 0
    else
        log "✗ FAIL: $name"
        ((CHECKS_FAILED++))
        return 1
    fi
}

log "=========================================="
log "Production Deployment Verification"
log "=========================================="

# 1. Database Connectivity
log ""
log "Checking Database..."
check "Database container running" \
    "docker ps --format '{{.Names}}' | grep -q '^${DB_CONTAINER}$'"

check "Database connectivity" \
    "docker exec '$DB_CONTAINER' psql -U '$DB_USER' -d '$DB_NAME' -c 'SELECT 1' > /dev/null 2>&1"

# 2. Redis Connectivity
log ""
log "Checking Redis..."
check "Redis container running" \
    "docker ps --format '{{.Names}}' | grep -q '^${REDIS_CONTAINER}$'"

check "Redis connectivity" \
    "docker exec '$REDIS_CONTAINER' redis-cli ping | grep -q PONG"

# 3. Health Endpoint
log ""
log "Checking Health Endpoint..."
if command -v curl &> /dev/null; then
    check "Health endpoint responds 200" \
        "curl -sf '$HEALTH_ENDPOINT' > /dev/null 2>&1"
else
    log "⊘ SKIP: Health endpoint (curl not available)"
fi

# 4. Database Migrations
log ""
log "Checking Database Migrations..."
MIGRATION_COUNT=$(docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'" 2>/dev/null || echo "0")

if [ "$MIGRATION_COUNT" -gt 0 ]; then
    log "✓ PASS: Database migrations applied ($MIGRATION_COUNT tables)"
    ((CHECKS_PASSED++))
else
    log "✗ FAIL: No database tables found"
    ((CHECKS_FAILED++))
fi

# 5. SSL Certificate Validity
log ""
log "Checking SSL Certificate..."
if [ -f "/etc/ssl/certs/1ai-social.crt" ]; then
    EXPIRY=$(openssl x509 -enddate -noout -in /etc/ssl/certs/1ai-social.crt 2>/dev/null | cut -d= -f2 || echo "")
    if [ -n "$EXPIRY" ]; then
        EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$EXPIRY" +%s 2>/dev/null || echo "0")
        CURRENT_EPOCH=$(date +%s)
        DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))
        
        if [ "$DAYS_UNTIL_EXPIRY" -gt 0 ]; then
            log "✓ PASS: SSL certificate valid ($DAYS_UNTIL_EXPIRY days remaining)"
            ((CHECKS_PASSED++))
        else
            log "✗ FAIL: SSL certificate expired"
            ((CHECKS_FAILED++))
        fi
    else
        log "⊘ SKIP: SSL certificate (unable to parse expiry)"
    fi
else
    log "⊘ SKIP: SSL certificate (file not found)"
fi

# 6. Environment Variables
log ""
log "Checking Environment Variables..."
REQUIRED_VARS=("DATABASE_URL" "REDIS_URL" "SENTRY_DSN" "SECRET_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    log "✓ PASS: All required environment variables set"
    ((CHECKS_PASSED++))
else
    log "✗ FAIL: Missing environment variables: ${MISSING_VARS[*]}"
    ((CHECKS_FAILED++))
fi

# 7. Docker Containers Running
log ""
log "Checking Docker Containers..."
REQUIRED_CONTAINERS=("$DB_CONTAINER" "$REDIS_CONTAINER" "$APP_CONTAINER")
STOPPED_CONTAINERS=()

for container in "${REQUIRED_CONTAINERS[@]}"; do
    if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        STOPPED_CONTAINERS+=("$container")
    fi
done

if [ ${#STOPPED_CONTAINERS[@]} -eq 0 ]; then
    log "✓ PASS: All required containers running"
    ((CHECKS_PASSED++))
else
    log "✗ FAIL: Stopped containers: ${STOPPED_CONTAINERS[*]}"
    ((CHECKS_FAILED++))
fi

# Summary
log ""
log "=========================================="
log "Verification Summary"
log "=========================================="
log "Passed: $CHECKS_PASSED"
log "Failed: $CHECKS_FAILED"
log "=========================================="

if [ "$CHECKS_FAILED" -eq 0 ]; then
    log "✓ Production deployment is healthy"
    exit 0
else
    log "✗ Production deployment has issues"
    exit 1
fi
