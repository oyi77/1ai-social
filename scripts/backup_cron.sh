#!/bin/bash
#
# Cron-friendly Backup Wrapper
# Handles errors, notifications, and verification for automated backups
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="${SCRIPT_DIR}/backup.sh"
LOG_FILE="${LOG_FILE:-${SCRIPT_DIR}/../logs/backup_cron.log}"
NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
MAX_LOG_SIZE_MB="${MAX_LOG_SIZE_MB:-10}"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Send notification
notify() {
    local STATUS="$1"
    local MESSAGE="$2"
    
    # Email notification
    if [ -n "$NOTIFICATION_EMAIL" ] && command -v mail &> /dev/null; then
        echo "$MESSAGE" | mail -s "Backup $STATUS: 1ai-social" "$NOTIFICATION_EMAIL" 2>/dev/null || true
    fi
    
    # Slack notification
    if [ -n "$SLACK_WEBHOOK" ] && command -v curl &> /dev/null; then
        local COLOR="good"
        [ "$STATUS" = "FAILED" ] && COLOR="danger"
        
        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$COLOR\",
                    \"title\": \"Backup $STATUS\",
                    \"text\": \"$MESSAGE\",
                    \"footer\": \"1ai-social\",
                    \"ts\": $(date +%s)
                }]
            }" 2>/dev/null || true
    fi
}

# Rotate log file if too large
rotate_log() {
    if [ -f "$LOG_FILE" ]; then
        LOG_SIZE_MB=$(du -m "$LOG_FILE" | cut -f1)
        if [ "$LOG_SIZE_MB" -gt "$MAX_LOG_SIZE_MB" ]; then
            mv "$LOG_FILE" "${LOG_FILE}.old"
            log "Log file rotated (was ${LOG_SIZE_MB}MB)"
        fi
    fi
}

# Main execution
main() {
    local START_TIME=$(date +%s)
    
    log "=========================================="
    log "Starting automated backup"
    
    # Check if backup script exists
    if [ ! -f "$BACKUP_SCRIPT" ]; then
        local ERROR_MSG="Backup script not found: $BACKUP_SCRIPT"
        log "ERROR: $ERROR_MSG"
        notify "FAILED" "$ERROR_MSG"
        exit 1
    fi
    
    # Run backup script
    if bash "$BACKUP_SCRIPT" >> "$LOG_FILE" 2>&1; then
        local END_TIME=$(date +%s)
        local DURATION=$((END_TIME - START_TIME))
        local SUCCESS_MSG="Backup completed successfully in ${DURATION}s"
        
        log "$SUCCESS_MSG"
        
        # Verify backup was created
        BACKUP_DIR="${BACKUP_DIR:-${SCRIPT_DIR}/../backups}"
        LATEST_BACKUP=$(find "$BACKUP_DIR" -name "1ai_social_*.sql.gz" -type f -mmin -5 | head -1)
        
        if [ -n "$LATEST_BACKUP" ]; then
            BACKUP_SIZE=$(du -h "$LATEST_BACKUP" | cut -f1)
            log "Latest backup: $(basename "$LATEST_BACKUP") ($BACKUP_SIZE)"
            notify "SUCCESS" "$SUCCESS_MSG\nFile: $(basename "$LATEST_BACKUP") ($BACKUP_SIZE)"
        else
            local WARN_MSG="Backup script succeeded but no recent backup file found"
            log "WARNING: $WARN_MSG"
            notify "WARNING" "$WARN_MSG"
        fi
    else
        local ERROR_MSG="Backup script failed (exit code: $?)"
        log "ERROR: $ERROR_MSG"
        notify "FAILED" "$ERROR_MSG\nCheck logs: $LOG_FILE"
        exit 1
    fi
    
    # Rotate log if needed
    rotate_log
    
    log "Automated backup completed"
    log "=========================================="
}

# Trap errors
trap 'log "ERROR: Script failed at line $LINENO"; notify "FAILED" "Backup script crashed at line $LINENO"' ERR

# Run main function
main

exit 0
