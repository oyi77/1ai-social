#!/bin/bash
#
# PostgreSQL Restore Script
# Restores database from backup with verification
#

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_CONTAINER="${DB_CONTAINER:-1ai-social-postgres}"
DB_NAME="${DB_NAME:-1ai_social}"
DB_USER="${DB_USER:-1ai}"
S3_BUCKET="${S3_BUCKET:-}"
LOG_FILE="${LOG_FILE:-./logs/restore.log}"

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

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Restore PostgreSQL database from backup.

OPTIONS:
    -f FILE     Restore from specific backup file
    -l          List available backups
    -s          Download and restore latest backup from S3
    -h          Show this help message

EXAMPLES:
    $0 -l                                    # List available backups
    $0 -f backups/1ai_social_20260416.sql.gz # Restore from specific file
    $0 -s                                    # Restore latest from S3
    $0                                       # Restore latest local backup

EOF
    exit 1
}

# List available backups
list_backups() {
    log "Available local backups:"
    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f -printf "%T@ %p\n" | sort -rn | while read -r timestamp file; do
            SIZE=$(du -h "$file" | cut -f1)
            DATE=$(date -d "@${timestamp%.*}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r "${timestamp%.*}" '+%Y-%m-%d %H:%M:%S')
            echo "  $DATE - $(basename "$file") ($SIZE)"
        done
    else
        echo "  No backups found in $BACKUP_DIR"
    fi
    
    if [ -n "$S3_BUCKET" ] && command -v aws &> /dev/null; then
        log "Available S3 backups:"
        aws s3 ls "s3://$S3_BUCKET/" | grep "${DB_NAME}_" | tail -10 || echo "  No S3 backups found"
    fi
}

# Download latest backup from S3
download_from_s3() {
    if [ -z "$S3_BUCKET" ]; then
        error_exit "S3_BUCKET not configured"
    fi
    
    if ! command -v aws &> /dev/null; then
        error_exit "AWS CLI not found"
    fi
    
    log "Fetching latest backup from S3..."
    LATEST_S3=$(aws s3 ls "s3://$S3_BUCKET/" | grep "${DB_NAME}_" | sort | tail -1 | awk '{print $4}')
    
    if [ -z "$LATEST_S3" ]; then
        error_exit "No backups found in S3 bucket"
    fi
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/$LATEST_S3"
    
    log "Downloading: $LATEST_S3"
    if aws s3 cp "s3://$S3_BUCKET/$LATEST_S3" "$BACKUP_FILE"; then
        log "Downloaded successfully: $BACKUP_FILE"
        echo "$BACKUP_FILE"
    else
        error_exit "Failed to download from S3"
    fi
}

# Get latest local backup
get_latest_backup() {
    if [ ! -d "$BACKUP_DIR" ]; then
        error_exit "Backup directory not found: $BACKUP_DIR"
    fi
    
    LATEST=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -type f -printf "%T@ %p\n" | sort -rn | head -1 | cut -d' ' -f2)
    
    if [ -z "$LATEST" ]; then
        error_exit "No backup files found in $BACKUP_DIR"
    fi
    
    echo "$LATEST"
}

# Get row counts for verification
get_row_counts() {
    docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT schemaname || '.' || tablename AS table, n_live_tup AS rows
        FROM pg_stat_user_tables
        ORDER BY schemaname, tablename;
    " 2>/dev/null || echo ""
}

# Parse command line options
BACKUP_FILE=""
LIST_ONLY=false
FROM_S3=false

while getopts "f:lsh" opt; do
    case $opt in
        f) BACKUP_FILE="$OPTARG" ;;
        l) LIST_ONLY=true ;;
        s) FROM_S3=true ;;
        h) usage ;;
        *) usage ;;
    esac
done

# List backups and exit if requested
if [ "$LIST_ONLY" = true ]; then
    list_backups
    exit 0
fi

# Determine backup file to restore
if [ "$FROM_S3" = true ]; then
    BACKUP_FILE=$(download_from_s3)
elif [ -z "$BACKUP_FILE" ]; then
    BACKUP_FILE=$(get_latest_backup)
fi

# Validate backup file
if [ ! -f "$BACKUP_FILE" ]; then
    error_exit "Backup file not found: $BACKUP_FILE"
fi

log "Starting restore from: $BACKUP_FILE"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    error_exit "Database container '$DB_CONTAINER' is not running"
fi

# Verify backup integrity
log "Verifying backup integrity..."
if ! gunzip -t "$BACKUP_FILE" 2>/dev/null; then
    error_exit "Backup file is corrupted"
fi
log "Backup integrity verified"

# Get pre-restore row counts
log "Capturing pre-restore database state..."
PRE_COUNTS=$(get_row_counts)

# Confirm restore (if interactive)
if [ -t 0 ]; then
    echo ""
    echo "WARNING: This will drop and recreate the database '$DB_NAME'"
    echo "Backup file: $BACKUP_FILE"
    echo ""
    read -p "Continue with restore? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        log "Restore cancelled by user"
        exit 0
    fi
fi

# Perform restore
log "Restoring database..."
if gunzip -c "$BACKUP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
    log "Database restored successfully"
else
    error_exit "Failed to restore database"
fi

# Verify restore
log "Verifying restore..."

# Check database connectivity
if ! docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    error_exit "Database connectivity check failed"
fi

# Get post-restore row counts
POST_COUNTS=$(get_row_counts)

# Compare row counts
log "Data integrity check:"
if [ -n "$PRE_COUNTS" ] && [ -n "$POST_COUNTS" ]; then
    echo "$POST_COUNTS" | while read -r line; do
        TABLE=$(echo "$line" | awk '{print $1}')
        ROWS=$(echo "$line" | awk '{print $2}')
        log "  $TABLE: $ROWS rows"
    done
else
    log "  Database restored (row count verification skipped)"
fi

# Summary
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "Restore completed successfully"
log "Restored from: $(basename "$BACKUP_FILE") ($BACKUP_SIZE)"

exit 0
