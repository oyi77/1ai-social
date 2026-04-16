# Backup Scripts

Automated PostgreSQL backup and restore system for 1ai-social.

## Quick Start

```bash
# Run backup
./scripts/backup.sh

# List backups
./scripts/restore.sh -l

# Restore latest backup
./scripts/restore.sh

# Test backup/restore cycle
./scripts/test_backup_restore.sh
```

## Files

- `backup.sh` - Core backup script with S3 support
- `restore.sh` - Restore script with verification
- `backup_cron.sh` - Cron-friendly wrapper with notifications
- `test_backup_restore.sh` - Automated test suite
- `.env.example` - Configuration template

## Documentation

See [docs/BACKUP_PROCEDURES.md](../docs/BACKUP_PROCEDURES.md) for complete documentation.

## Setup Cron

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/1ai-social && ./scripts/backup_cron.sh
```

## Configuration

Copy `.env.example` and customize:

```bash
cp scripts/.env.example scripts/.env
source scripts/.env
```
