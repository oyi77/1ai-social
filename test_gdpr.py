"""Test GDPR compliance functionality with existing tenant."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import importlib

gdpr_module = importlib.import_module("1ai_social.gdpr")
GDPRManager = gdpr_module.GDPRManager
ConsentType = gdpr_module.ConsentType


def get_test_session():
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/1ai_social")
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    result = session.execute(text("SELECT id FROM tenants LIMIT 1"))
    row = result.fetchone()
    if row:
        tenant_id = row[0]
        session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
        return session, tenant_id
    else:
        raise Exception("No tenants found in database. Please create a tenant first.")


def test_record_consent():
    session, tenant_id = get_test_session()
    manager = GDPRManager(session)

    consent_id = manager.record_consent(
        user_id="test_user_123",
        tenant_id=tenant_id,
        consent_type=ConsentType.MARKETING,
        consented=True,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        metadata={"version": "1.0", "form_id": "signup_form"},
    )

    assert consent_id is not None
    print(f"✓ Consent recorded with ID: {consent_id}")

    history = manager.get_consent_history(
        user_id="test_user_123", tenant_id=tenant_id, consent_type=ConsentType.MARKETING
    )

    assert len(history) > 0
    assert history[0]["consented"] == True
    assert history[0]["consent_type"] == ConsentType.MARKETING
    print(f"✓ Consent history retrieved: {len(history)} records")

    session.close()


def test_consent_withdrawal():
    session, tenant_id = get_test_session()
    manager = GDPRManager(session)

    manager.record_consent(
        user_id="test_user_456",
        tenant_id=tenant_id,
        consent_type=ConsentType.ANALYTICS,
        consented=True,
        ip_address="192.168.1.2",
    )

    manager.record_consent(
        user_id="test_user_456",
        tenant_id=tenant_id,
        consent_type=ConsentType.ANALYTICS,
        consented=False,
        ip_address="192.168.1.2",
    )

    current_consent = manager.get_current_consent(
        user_id="test_user_456", tenant_id=tenant_id, consent_type=ConsentType.ANALYTICS
    )

    assert current_consent == False
    print("✓ Consent withdrawal recorded correctly")

    session.close()


def test_export_user_data():
    session, tenant_id = get_test_session()
    manager = GDPRManager(session)

    manager.record_consent(
        user_id="test_user_789",
        tenant_id=tenant_id,
        consent_type=ConsentType.PRIVACY_POLICY,
        consented=True,
        ip_address="192.168.1.3",
    )

    export_data = manager.export_user_data(user_id="test_user_789", tenant_id=tenant_id)

    assert export_data["user_id"] == "test_user_789"
    assert export_data["tenant_id"] == tenant_id
    assert "export_timestamp" in export_data
    assert "data" in export_data
    assert "consent_records" in export_data["data"]
    assert len(export_data["data"]["consent_records"]) > 0

    print("✓ User data exported successfully")
    print(f"  - Consent records: {len(export_data['data']['consent_records'])}")
    print(f"  - Platforms: {len(export_data['data']['platforms'])}")
    print(f"  - Contents: {len(export_data['data']['contents'])}")
    print(f"  - Posts: {len(export_data['data']['posts'])}")

    session.close()


def test_delete_user_data():
    session, tenant_id = get_test_session()
    manager = GDPRManager(session)

    manager.record_consent(
        user_id="test_user_delete",
        tenant_id=tenant_id,
        consent_type=ConsentType.MARKETING,
        consented=True,
        ip_address="192.168.1.4",
        user_agent="Mozilla/5.0",
    )

    deletion_summary = manager.delete_user_data(
        user_id="test_user_delete",
        tenant_id=tenant_id,
        reason="User requested account deletion",
    )

    assert deletion_summary["user_id"] == "test_user_delete"
    assert deletion_summary["tenant_id"] == tenant_id
    assert "deletion_timestamp" in deletion_summary
    assert "operations" in deletion_summary

    print("✓ User data deleted/anonymized")
    print(
        f"  - Consent records anonymized: {deletion_summary['operations']['consent_records_anonymized']}"
    )

    verification = manager.verify_deletion(
        user_id="test_user_delete", tenant_id=tenant_id
    )

    print("✓ Deletion verification:")
    print(f"  - Deletion complete: {verification['deletion_complete']}")
    print(f"  - PII found: {verification['pii_found']}")

    session.close()


def test_consent_types():
    session, tenant_id = get_test_session()
    manager = GDPRManager(session)

    consent_types = [
        ConsentType.TERMS_OF_SERVICE,
        ConsentType.PRIVACY_POLICY,
        ConsentType.MARKETING,
        ConsentType.ANALYTICS,
        ConsentType.DATA_PROCESSING,
        ConsentType.THIRD_PARTY_SHARING,
    ]

    for consent_type in consent_types:
        manager.record_consent(
            user_id="test_user_types",
            tenant_id=tenant_id,
            consent_type=consent_type,
            consented=True,
            ip_address="192.168.1.5",
        )

    history = manager.get_consent_history(
        user_id="test_user_types", tenant_id=tenant_id
    )

    assert len(history) >= len(consent_types)
    print(f"✓ All {len(consent_types)} consent types recorded successfully")

    session.close()


if __name__ == "__main__":
    print("Testing GDPR Compliance Module\n")

    try:
        print("1. Testing consent recording...")
        test_record_consent()
        print()

        print("2. Testing consent withdrawal...")
        test_consent_withdrawal()
        print()

        print("3. Testing data export (DSAR)...")
        test_export_user_data()
        print()

        print("4. Testing data deletion...")
        test_delete_user_data()
        print()

        print("5. Testing consent types...")
        test_consent_types()
        print()

        print("=" * 50)
        print("✓ All GDPR tests passed!")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
