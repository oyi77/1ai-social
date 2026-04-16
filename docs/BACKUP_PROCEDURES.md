# PostgreSQL Backup and Restore Procedures

## Overview

Automated backup system for the 1ai-social PostgreSQL database with 30-day retention, optional S3 storage, and verified restore capabilities.

## Scripts

### backup.sh
Creates compressed database backups with optional S3 upload.

**Usage:**
```bash
./scripts/backup.sh
```

**Environment Variables:**
- `BACKUP_DIR` - Local backup directory (default: ./backups)
- `DB_CONTAINER` - PostgreSQL container name (default: 1ai-social-postgres)
- `DB_NAME` - Database name (default: 1ai_social)
- `DB_USER` - Database user (default: 1ai)
- `RETENTION_DAYS` - Days to keep backups (default: 30)
- `S3_BUCKET` - S3 bucket for off-site storage (optional)
- `LOG_FILE` - Log file path (default: ./logs/backup.log)

**Features:**
- Compressed backups using gzip
- Integrity verification
- 30-day local retention
- Optional S3 upload with STANDARD_IA storage class
- Automatic cleanup of old backups

### restore.sh
Restores database from backup with data verification.

**Usage:**
```bash
# List available backups
./scripts/restore.sh -l

# Restore latest local backup
./scripts/restore.sh

# Restore specific backup
./scripts/restore.sh -f backups/1ai_social_20260416_120000.sql.gz

# Restore latest from S3
./scripts/restore.sh -s
```

**Options:**
- `-f FILE` - Restore from specific backup file
- `-l` - List available backups
- `-s` - Download and restore latest from S3
- `-h` - Show help

**Features:**
- Backup integrity verification
- Pre/post restore row count comparison
- Interactive confirmation (when run manually)
- S3 download support

### backup_cron.sh
Cron-friendly wrapper with error handling and notifications.

**Usage:**
```bash
./scripts/backup_cron.sh
```

**Environment Variables:**
- `NOTIFICATION_EMAIL` - Email for backup notifications (optional)
- `SLACK_WEBHOOK` - Slack webhook URL for notifications (optional)
- `MAX_LOG_SIZE_MB` - Maximum log size before rotation (default: 10)

**Features:**
- Error handling and notifications
- Backup verification
- Log rotation
- Email and Slack notifications

## Setup

### 1. Manual Backup
```bash
cd /path/to/1ai-social
./scripts/backup.sh
```

### 2. Automated Daily Backups
Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/1ai-social && ./scripts/backup_cron.sh
```

Edit crontab:
```bash
crontab -e
```

### 3. S3 Configuration (Optional)
```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure

# Set S3 bucket
export S3_BUCKET="my-backup-bucket"
```

### 4. Email Notifications (Optional)
```bash
# Install mail utility
sudo apt-get install mailutils

# Set notification email
export NOTIFICATION_EMAIL="admin@example.com"
```

### 5. Slack Notifications (Optional)
```bash
# Create Slack webhook: https://api.slack.com/messaging/webhooks
export SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

## Testing

### Test Backup
```bash
# Start database
docker-compose up -d postgres

# Run backup
./scripts/backup.sh

# Verify backup created
ls -lh backups/
```

### Test Restore
```bash
# Create test data
docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -c \
  "CREATE TABLE test_backup (id SERIAL, data TEXT); 
   INSERT INTO test_backup (data) VALUES ('test1'), ('test2');"

# Run backup
./scripts/backup.sh

# Delete test data
docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -c \
  "DROP TABLE test_backup;"

# Restore
./scripts/restore.sh

# Verify data restored
docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -c \
  "SELECT * FROM test_backup;"
```

## Monitoring

### Check Backup Logs
```bash
tail -f logs/backup.log
tail -f logs/backup_cron.log
```

### List Backups
```bash
# Local backups
./scripts/restore.sh -l

# S3 backups
aws s3 ls s3://your-bucket/
```

### Verify Backup Size
```bash
du -sh backups/
```

## Recovery Procedures

### Full Database Recovery
```bash
# Stop application
docker-compose stop app

# Restore database
./scripts/restore.sh

# Verify data integrity
docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -c \
  "SELECT schemaname, tablename, n_live_tup FROM pg_stat_user_tables;"

# Start application
docker-compose start app
```

### Point-in-Time Recovery
```bash
# List available backups
./scripts/restore.sh -l

# Restore specific backup
./scripts/restore.sh -f backups/1ai_social_20260416_120000.sql.gz
```

### Disaster Recovery from S3
```bash
# Download and restore latest
./scripts/restore.sh -s

# Or download specific backup
aws s3 cp s3://your-bucket/1ai_social_20260416_120000.sql.gz backups/
./scripts/restore.sh -f backups/1ai_social_20260416_120000.sql.gz
```

## Best Practices

1. **Test restores regularly** - Verify backups are valid
2. **Monitor backup logs** - Check for failures
3. **Use S3 for off-site storage** - Protect against hardware failure
4. **Keep multiple backup copies** - 30-day retention provides safety
5. **Verify data integrity** - Check row counts after restore
6. **Document recovery procedures** - Ensure team knows how to restore

## Troubleshooting

### Backup fails with "container not running"
```bash
docker-compose up -d postgres
```

### Backup file is corrupted
```bash
# Verify integrity
gunzip -t backups/1ai_social_*.sql.gz

# If corrupted, use previous backup
./scripts/restore.sh -l
```

### S3 upload fails
```bash
# Check AWS credentials
aws s3 ls

# Verify bucket exists
aws s3 mb s3://your-bucket
```

### Restore fails with permission error
```bash
# Check database user permissions
docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -c \
  "SELECT current_user, session_user;"
```

## Security Notes

- Backups contain sensitive data - secure storage location
- Use IAM roles for S3 access in production
- Encrypt backups for off-site storage
- Restrict access to backup scripts and files
- Rotate database credentials regularly
