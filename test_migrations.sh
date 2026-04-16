#!/bin/bash
set -e

cd "$(dirname "$0")/.."

source venv/bin/activate

echo "=== Testing Alembic Migrations ==="
echo ""

echo "1. Checking migration file exists..."
if [ -f "migrations/versions/001_initial_schema.py" ]; then
    echo "✓ Migration file found"
else
    echo "✗ Migration file not found"
    exit 1
fi

echo ""
echo "2. Listing available migrations..."
alembic history || echo "No migration history yet (expected for first run)"

echo ""
echo "3. Current migration status..."
alembic current || echo "No current migration (expected for fresh database)"

echo ""
echo "=== Migration Setup Complete ==="
echo ""
echo "To apply migrations to a database:"
echo "  1. Set DATABASE_URL environment variable"
echo "  2. Run: alembic upgrade head"
echo "  3. To rollback: alembic downgrade -1"
