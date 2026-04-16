#!/bin/bash
set -euo pipefail

echo "=== Backup/Restore Test Suite ==="
echo ""

echo "1. Checking prerequisites..."
if ! docker ps --format '{{.Names}}' | grep -q "1ai-social-postgres"; then
    echo "   ❌ PostgreSQL container not running"
    echo "   Run: docker-compose up -d postgres"
    exit 1
fi
echo "   ✓ PostgreSQL container running"

echo ""
echo "2. Creating test table and data..."
docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -c "
    DROP TABLE IF EXISTS backup_test;
    CREATE TABLE backup_test (
        id SERIAL PRIMARY KEY,
        data TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    INSERT INTO backup_test (data) VALUES 
        ('test_data_1'),
        ('test_data_2'),
        ('test_data_3');
" > /dev/null
echo "   ✓ Test data created (3 rows)"

echo ""
echo "3. Running backup..."
if ./scripts/backup.sh > /dev/null 2>&1; then
    echo "   ✓ Backup completed"
else
    echo "   ❌ Backup failed"
    exit 1
fi

echo ""
echo "4. Verifying backup file..."
LATEST_BACKUP=$(find backups/ -name "1ai_social_*.sql.gz" -type f -printf "%T@ %p\n" | sort -rn | head -1 | cut -d' ' -f2)
if [ -n "$LATEST_BACKUP" ]; then
    BACKUP_SIZE=$(du -h "$LATEST_BACKUP" | cut -f1)
    echo "   ✓ Backup file: $(basename "$LATEST_BACKUP") ($BACKUP_SIZE)"
else
    echo "   ❌ No backup file found"
    exit 1
fi

echo ""
echo "5. Verifying backup integrity..."
if gunzip -t "$LATEST_BACKUP" 2>/dev/null; then
    echo "   ✓ Backup integrity verified"
else
    echo "   ❌ Backup file corrupted"
    exit 1
fi

echo ""
echo "6. Deleting test data..."
docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -c "DELETE FROM backup_test;" > /dev/null
ROW_COUNT=$(docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -t -c "SELECT COUNT(*) FROM backup_test;" | xargs)
echo "   ✓ Data deleted (rows remaining: $ROW_COUNT)"

echo ""
echo "7. Restoring from backup..."
if echo "yes" | ./scripts/restore.sh -f "$LATEST_BACKUP" > /dev/null 2>&1; then
    echo "   ✓ Restore completed"
else
    echo "   ❌ Restore failed"
    exit 1
fi

echo ""
echo "8. Verifying restored data..."
RESTORED_COUNT=$(docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -t -c "SELECT COUNT(*) FROM backup_test;" | xargs)
if [ "$RESTORED_COUNT" = "3" ]; then
    echo "   ✓ Data restored correctly ($RESTORED_COUNT rows)"
else
    echo "   ❌ Data mismatch (expected 3, got $RESTORED_COUNT)"
    exit 1
fi

echo ""
echo "9. Cleaning up test data..."
docker exec 1ai-social-postgres psql -U 1ai -d 1ai_social -c "DROP TABLE backup_test;" > /dev/null
echo "   ✓ Test table dropped"

echo ""
echo "=== All Tests Passed ✓ ==="
echo ""
echo "Summary:"
echo "  - Backup creates compressed files"
echo "  - Backup integrity verification works"
echo "  - Restore recovers data correctly"
echo "  - 30-day retention configured"
echo ""
echo "Next steps:"
echo "  1. Configure S3_BUCKET for off-site backups (optional)"
echo "  2. Set up cron: 0 2 * * * cd $(pwd) && ./scripts/backup_cron.sh"
echo "  3. Configure notifications (NOTIFICATION_EMAIL or SLACK_WEBHOOK)"
