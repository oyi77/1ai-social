#!/bin/bash
#
# PostgreSQL Backup Script
# Creates compressed backups with optional S3 upload and 30-day retention
#

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_CONTAINER="${DB_CONTAINER:-1ai-social-postgres}"
DB_NAME="${DB_NAME:-1ai_social}"
DB_USER="${DB_USER:-1ai}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"
LOG_FILE="${LOG_FILE:-./logs/backup.log}"

# Ensure directories exist
mkdir -p "$BACKUP_DIR"
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

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

log "Starting backup of database: $DB_NAME"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    error_exit "Database container '$DB_CONTAINER' is not running"
fi

# Create backup using pg_dump with compression
log "Creating compressed backup: $BACKUP_FILE"
if docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists | gzip > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"
else
    error_exit "Failed to create backup"
fi

# Verify backup file is not empty
if [ ! -s "$BACKUP_FILE" ]; then
    error_exit "Backup file is empty"
fi

# Verify backup integrity
log "Verifying backup integrity..."
if gunzip -t "$BACKUP_FILE" 2>/dev/null; then
    log "Backup integrity verified"
else
    error_exit "Backup file is corrupted"
fi

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    log "Uploading backup to S3: s3://$S3_BUCKET/"
    if command -v aws &> /dev/null; then
        if aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/$(basename "$BACKUP_FILE")" --storage-class STANDARD_IA; then
            log "Backup uploaded to S3 successfully"
        else
            log "WARNING: Failed to upload backup to S3 (local backup still available)"
        fi
    else
        log "WARNING: AWS CLI not found, skipping S3 upload"
    fi
fi

# Clean up old backups (local retention)
log "Cleaning up backups older than $RETENTION_DAYS days..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$DELETED_COUNT" -gt 0 ]; then
    log "Deleted $DELETED_COUNT old backup(s)"
else
    log "No old backups to delete"
fi

# Clean up old S3 backups if configured
if [ -n "$S3_BUCKET" ] && command -v aws &> /dev/null; then
    log "Cleaning up S3 backups older than $RETENTION_DAYS days..."
    CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d)
    aws s3 ls "s3://$S3_BUCKET/" | grep "${DB_NAME}_" | while read -r line; do
        FILE_DATE=$(echo "$line" | awk '{print $1}')
        FILE_NAME=$(echo "$line" | awk '{print $4}')
        if [[ "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
            aws s3 rm "s3://$S3_BUCKET/$FILE_NAME" && log "Deleted old S3 backup: $FILE_NAME"
        fi
    done 2>/dev/null || log "S3 cleanup completed"
fi

# Summary
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
log "Backup completed successfully"
log "Total local backups: $TOTAL_BACKUPS (using $TOTAL_SIZE)"

exit 0
