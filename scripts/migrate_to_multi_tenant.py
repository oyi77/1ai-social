#!/usr/bin/env python3
"""
Data migration script to assign default tenant to existing records.

This script:
1. Creates a default tenant (id='default', name='Default Tenant')
2. Assigns default tenant to all existing records with NULL tenant_id
3. Verifies data integrity (no data loss)
4. Provides rollback capability

Usage:
    python scripts/migrate_to_multi_tenant.py migrate    # Run migration
    python scripts/migrate_to_multi_tenant.py rollback   # Rollback migration
    python scripts/migrate_to_multi_tenant.py verify     # Verify migration status
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import yaml


def load_database_url():
    """Load database URL from config.yaml or alembic.ini."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    config_path = project_root / "config.yaml"
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        db_url = config.get("database_url", "")

        if db_url.startswith("${") and db_url.endswith("}"):
            var_name = db_url[2:-1]
            if ":-" in var_name:
                var_name, default = var_name.split(":-", 1)
                db_url = os.getenv(var_name, default)
            else:
                db_url = os.getenv(var_name)

        if db_url:
            return db_url

    alembic_ini = project_root / "alembic.ini"
    if alembic_ini.exists():
        with open(alembic_ini, "r") as f:
            for line in f:
                if line.strip().startswith("sqlalchemy.url"):
                    db_url = line.split("=", 1)[1].strip()
                    return db_url

    raise ValueError(
        "database_url not found in environment, config.yaml, or alembic.ini"
    )


def get_db_session():
    """Create database session."""
    db_url = load_database_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    return session, engine


def set_admin_role(session):
    """Set admin role to bypass RLS policies."""
    session.execute(text("SET LOCAL app.user_role = 'admin'"))


def count_records(session, table_name):
    """Count total records in a table."""
    set_admin_role(session)
    result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    return result.scalar()


def count_null_tenant_records(session, table_name):
    """Count records with NULL tenant_id."""
    set_admin_role(session)
    result = session.execute(
        text(f"SELECT COUNT(*) FROM {table_name} WHERE tenant_id IS NULL")
    )
    return result.scalar()


def count_default_tenant_records(session, table_name):
    """Count records with tenant_id='default'."""
    set_admin_role(session)
    result = session.execute(
        text(f"SELECT COUNT(*) FROM {table_name} WHERE tenant_id = :tenant_id"),
        {"tenant_id": "default"},
    )
    return result.scalar()


def count_null_tenant_records(session, table_name):
    """Count records with NULL tenant_id."""
    result = session.execute(
        text(f"SELECT COUNT(*) FROM {table_name} WHERE tenant_id IS NULL")
    )
    return result.scalar()


def count_default_tenant_records(session, table_name):
    """Count records with tenant_id='default'."""
    result = session.execute(
        text(f"SELECT COUNT(*) FROM {table_name} WHERE tenant_id = :tenant_id"),
        {"tenant_id": "default"},
    )
    return result.scalar()


def migrate_to_multi_tenant():
    """
    Migrate existing data to multi-tenant structure.

    Steps:
    1. Create default tenant
    2. Count records before migration
    3. Update each table to assign default tenant
    4. Count records after migration
    5. Verify counts match
    6. Log results
    """
    print("=" * 80)
    print("MULTI-TENANT DATA MIGRATION")
    print("=" * 80)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print()

    session, engine = get_db_session()

    try:
        # Tables to migrate
        tables = [
            "platforms",
            "contents",
            "hooks",
            "posts",
            "analytics_records",
            "audit_logs",
        ]

        # Step 1: Create default tenant
        print("Step 1: Creating default tenant...")
        try:
            set_admin_role(session)
            session.execute(
                text("""
                    INSERT INTO tenants (id, name, plan, status, created_at, updated_at)
                    VALUES (:id, :name, :plan, :status, :created_at, :updated_at)
                """),
                {
                    "id": "default",
                    "name": "Default Tenant",
                    "plan": "starter",
                    "status": "active",
                    "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                },
            )
            session.commit()
            print("✓ Default tenant created (id='default', name='Default Tenant')")
        except IntegrityError:
            session.rollback()
            print("⚠ Default tenant already exists, skipping creation")

        print()

        # Step 2: Count records before migration
        print("Step 2: Counting records before migration...")
        before_counts = {}
        null_counts = {}

        for table in tables:
            total = count_records(session, table)
            null_count = count_null_tenant_records(session, table)
            before_counts[table] = total
            null_counts[table] = null_count
            print(f"  {table:25} Total: {total:6}  NULL tenant_id: {null_count:6}")

        print()

        # Step 3: Update each table
        print("Step 3: Assigning default tenant to records with NULL tenant_id...")
        updated_counts = {}

        for table in tables:
            if null_counts[table] > 0:
                set_admin_role(session)
                result = session.execute(
                    text(f"""
                        UPDATE {table}
                        SET tenant_id = :tenant_id
                        WHERE tenant_id IS NULL
                    """),
                    {"tenant_id": "default"},
                )
                updated_counts[table] = result.rowcount
                session.commit()
                print(f"  {table:25} Updated: {updated_counts[table]:6} records")
            else:
                updated_counts[table] = 0
                print(f"  {table:25} Updated: {0:6} records (no NULL values)")

        print()

        # Step 4: Count records after migration
        print("Step 4: Counting records after migration...")
        after_counts = {}
        default_counts = {}
        remaining_null = {}

        for table in tables:
            total = count_records(session, table)
            default_count = count_default_tenant_records(session, table)
            null_count = count_null_tenant_records(session, table)
            after_counts[table] = total
            default_counts[table] = default_count
            remaining_null[table] = null_count
            print(
                f"  {table:25} Total: {total:6}  Default tenant: {default_count:6}  NULL: {null_count:6}"
            )

        print()

        # Step 5: Verify counts match
        print("Step 5: Verifying data integrity...")
        all_verified = True

        for table in tables:
            before = before_counts[table]
            after = after_counts[table]
            expected_default = null_counts[table]
            actual_default = updated_counts[table]
            remaining = remaining_null[table]

            # Check no data loss
            if before != after:
                print(
                    f"  ✗ {table}: DATA LOSS DETECTED! Before: {before}, After: {after}"
                )
                all_verified = False
            # Check all NULL records were updated
            elif remaining > 0:
                print(f"  ✗ {table}: {remaining} records still have NULL tenant_id")
                all_verified = False
            # Check update count matches expected
            elif expected_default != actual_default:
                print(
                    f"  ✗ {table}: Expected {expected_default} updates, got {actual_default}"
                )
                all_verified = False
            else:
                print(
                    f"  ✓ {table}: Verified ({after} records, {actual_default} migrated)"
                )

        print()

        # Step 6: Summary
        print("=" * 80)
        if all_verified:
            print("✓ MIGRATION SUCCESSFUL")
            print()
            print("Summary:")
            total_migrated = sum(updated_counts.values())
            total_records = sum(after_counts.values())
            print(f"  Total records migrated: {total_migrated}")
            print(f"  Total records in database: {total_records}")
            print("  Data loss: None")
            print()
            print("All existing data has been assigned to the default tenant.")
            print("No data was lost during migration.")
        else:
            print("✗ MIGRATION FAILED")
            print()
            print("Data integrity verification failed. Please review the errors above.")
            print("The database may be in an inconsistent state.")
            print(
                "Consider running rollback: python scripts/migrate_to_multi_tenant.py rollback"
            )
            return False

        print("=" * 80)
        print(f"Completed at: {datetime.now(timezone.utc).isoformat()}")
        print()

        return True

    except Exception as e:
        session.rollback()
        print(f"\n✗ ERROR: {e}")
        print("\nMigration failed. Database rolled back.")
        return False
    finally:
        session.close()
        engine.dispose()


def rollback_migration():
    """
    Rollback migration by setting tenant_id to NULL and deleting default tenant.

    Steps:
    1. Count records before rollback
    2. Set tenant_id to NULL for all records with tenant_id='default'
    3. Delete default tenant
    4. Count records after rollback
    5. Verify rollback
    """
    print("=" * 80)
    print("ROLLBACK MULTI-TENANT MIGRATION")
    print("=" * 80)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print()

    session, engine = get_db_session()

    try:
        tables = [
            "platforms",
            "contents",
            "hooks",
            "posts",
            "analytics_records",
            "audit_logs",
        ]

        # Step 1: Count records before rollback
        print("Step 1: Counting records before rollback...")
        before_counts = {}
        default_counts = {}

        for table in tables:
            total = count_records(session, table)
            default_count = count_default_tenant_records(session, table)
            before_counts[table] = total
            default_counts[table] = default_count
            print(f"  {table:25} Total: {total:6}  Default tenant: {default_count:6}")

        print()

        # Step 2: Set tenant_id to NULL
        print("Step 2: Setting tenant_id to NULL for default tenant records...")
        updated_counts = {}

        for table in tables:
            if default_counts[table] > 0:
                set_admin_role(session)
                result = session.execute(
                    text(f"""
                        UPDATE {table}
                        SET tenant_id = NULL
                        WHERE tenant_id = :tenant_id
                    """),
                    {"tenant_id": "default"},
                )
                updated_counts[table] = result.rowcount
                session.commit()
                print(f"  {table:25} Updated: {updated_counts[table]:6} records")
            else:
                updated_counts[table] = 0
                print(f"  {table:25} Updated: {0:6} records (no default tenant)")

        print()

        # Step 3: Delete default tenant
        print("Step 3: Deleting default tenant...")
        set_admin_role(session)
        result = session.execute(
            text("DELETE FROM tenants WHERE id = :tenant_id"), {"tenant_id": "default"}
        )
        deleted = result.rowcount
        session.commit()

        if deleted > 0:
            print(f"✓ Default tenant deleted ({deleted} record)")
        else:
            print("⚠ Default tenant not found")

        print()

        # Step 4: Count records after rollback
        print("Step 4: Counting records after rollback...")
        after_counts = {}
        null_counts = {}

        for table in tables:
            total = count_records(session, table)
            null_count = count_null_tenant_records(session, table)
            after_counts[table] = total
            null_counts[table] = null_count
            print(f"  {table:25} Total: {total:6}  NULL tenant_id: {null_count:6}")

        print()

        # Step 5: Verify rollback
        print("Step 5: Verifying rollback...")
        all_verified = True

        for table in tables:
            before = before_counts[table]
            after = after_counts[table]
            expected_null = default_counts[table]
            actual_updated = updated_counts[table]

            # Check no data loss
            if before != after:
                print(
                    f"  ✗ {table}: DATA LOSS DETECTED! Before: {before}, After: {after}"
                )
                all_verified = False
            # Check update count matches expected
            elif expected_null != actual_updated:
                print(
                    f"  ✗ {table}: Expected {expected_null} updates, got {actual_updated}"
                )
                all_verified = False
            else:
                print(
                    f"  ✓ {table}: Verified ({after} records, {actual_updated} rolled back)"
                )

        print()

        # Summary
        print("=" * 80)
        if all_verified:
            print("✓ ROLLBACK SUCCESSFUL")
            print()
            print("Summary:")
            total_rolled_back = sum(updated_counts.values())
            print(f"  Total records rolled back: {total_rolled_back}")
            print(f"  Default tenant deleted: {'Yes' if deleted > 0 else 'No'}")
            print("  Data loss: None")
            print()
            print("All records have been reverted to NULL tenant_id.")
        else:
            print("✗ ROLLBACK FAILED")
            print()
            print("Rollback verification failed. Please review the errors above.")

        print("=" * 80)
        print(f"Completed at: {datetime.now(timezone.utc).isoformat()}")
        print()

        return all_verified

    except Exception as e:
        session.rollback()
        print(f"\n✗ ERROR: {e}")
        print("\nRollback failed. Database rolled back.")
        return False
    finally:
        session.close()
        engine.dispose()


def verify_migration_status():
    """
    Verify current migration status without making changes.
    """
    print("=" * 80)
    print("MIGRATION STATUS VERIFICATION")
    print("=" * 80)
    print(f"Checked at: {datetime.now(timezone.utc).isoformat()}")
    print()

    session, engine = get_db_session()

    try:
        tables = [
            "platforms",
            "contents",
            "hooks",
            "posts",
            "analytics_records",
            "audit_logs",
        ]

        # Check if default tenant exists
        print("Tenant Status:")
        result = session.execute(
            text("SELECT id, name, plan, status FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": "default"},
        )
        tenant = result.fetchone()

        if tenant:
            print("  ✓ Default tenant exists")
            print(f"    ID: {tenant[0]}")
            print(f"    Name: {tenant[1]}")
            print(f"    Plan: {tenant[2]}")
            print(f"    Status: {tenant[3]}")
        else:
            print("  ✗ Default tenant does not exist")

        print()

        # Check records in each table
        print("Table Status:")
        total_records = 0
        total_null = 0
        total_default = 0

        for table in tables:
            total = count_records(session, table)
            null_count = count_null_tenant_records(session, table)
            default_count = count_default_tenant_records(session, table)

            total_records += total
            total_null += null_count
            total_default += default_count

            status = "✓" if null_count == 0 else "⚠"
            print(
                f"  {status} {table:25} Total: {total:6}  NULL: {null_count:6}  Default: {default_count:6}"
            )

        print()
        print("Summary:")
        print(f"  Total records: {total_records}")
        print(f"  Records with NULL tenant_id: {total_null}")
        print(f"  Records with default tenant: {total_default}")
        print()

        if tenant and total_null == 0 and total_default > 0:
            print("✓ Migration appears complete")
        elif not tenant and total_null > 0:
            print("⚠ Migration not started or rolled back")
        else:
            print("⚠ Migration in inconsistent state")

        print("=" * 80)
        print()

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
    finally:
        session.close()
        engine.dispose()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/migrate_to_multi_tenant.py migrate    # Run migration")
        print(
            "  python scripts/migrate_to_multi_tenant.py rollback   # Rollback migration"
        )
        print("  python scripts/migrate_to_multi_tenant.py verify     # Verify status")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "migrate":
        success = migrate_to_multi_tenant()
        sys.exit(0 if success else 1)
    elif command == "rollback":
        success = rollback_migration()
        sys.exit(0 if success else 1)
    elif command == "verify":
        verify_migration_status()
        sys.exit(0)
    else:
        print(f"Unknown command: {command}")
        print("Valid commands: migrate, rollback, verify")
        sys.exit(1)


if __name__ == "__main__":
    main()
