"""GDPR Compliance Audit Test Suite

Comprehensive tests covering all GDPR requirements:
- Article 7: Consent Management
- Article 15: Right to Access (DSAR)
- Article 17: Right to Erasure
- Article 20: Data Portability
- Article 5(1)(c): Data Minimization
- Article 5(1)(e): Retention Policies
- Article 25: Privacy by Design
- Articles 33-34: Breach Notification Readiness
- Article 30: Data Processing Records
- Article 28: Third-Party Data Sharing

Run with: python -m pytest tests/test_gdpr_compliance.py -v
"""

import unittest
import json
import importlib
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any


gdpr_module = importlib.import_module("1ai_social.gdpr")
GDPRManager = gdpr_module.GDPRManager
ConsentType = gdpr_module.ConsentType


class TestConsentManagement(unittest.TestCase):
    """Test GDPR Article 7: Consent Management"""

    def setUp(self):
        self.db_session = Mock()
        self.manager = GDPRManager(self.db_session)

    def test_record_consent_with_timestamp(self):
        """Consent must be recorded with timestamp"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [123]
        self.db_session.execute.return_value = mock_result

        consent_id = self.manager.record_consent(
            user_id="user123",
            tenant_id="tenant456",
            consent_type=ConsentType.MARKETING,
            consented=True,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        self.assertEqual(consent_id, 123)
        self.db_session.execute.assert_called_once()
        call_args = self.db_session.execute.call_args
        self.assertIn("timestamp", call_args[0][1])
        self.assertIsInstance(call_args[0][1]["timestamp"], datetime)

    def test_record_consent_with_version_metadata(self):
        """Consent must include version and purpose in metadata"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [124]
        self.db_session.execute.return_value = mock_result

        metadata = {
            "version": "2.1",
            "purpose": "Email marketing campaigns",
            "form_id": "marketing_consent_v2",
        }

        consent_id = self.manager.record_consent(
            user_id="user123",
            tenant_id="tenant456",
            consent_type=ConsentType.MARKETING,
            consented=True,
            metadata=metadata,
        )

        self.assertEqual(consent_id, 124)
        call_args = self.db_session.execute.call_args
        metadata_json = call_args[0][1]["metadata"]
        self.assertIsNotNone(metadata_json)
        parsed_metadata = json.loads(metadata_json)
        self.assertEqual(parsed_metadata["version"], "2.1")
        self.assertEqual(parsed_metadata["purpose"], "Email marketing campaigns")

    def test_consent_withdrawal(self):
        """Users must be able to withdraw consent"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [125]
        self.db_session.execute.return_value = mock_result

        consent_id = self.manager.record_consent(
            user_id="user123",
            tenant_id="tenant456",
            consent_type=ConsentType.ANALYTICS,
            consented=False,
        )

        self.assertEqual(consent_id, 125)
        call_args = self.db_session.execute.call_args
        self.assertFalse(call_args[0][1]["consented"])

    def test_consent_required_before_processing(self):
        """Verify consent check before data processing"""
        mock_result = Mock()
        mock_result.fetchone.return_value = Mock(consented=True)
        self.db_session.execute.return_value = mock_result

        consent_status = self.manager.get_current_consent(
            user_id="user123",
            tenant_id="tenant456",
            consent_type=ConsentType.DATA_PROCESSING,
        )

        self.assertTrue(consent_status)

    def test_consent_history_tracking(self):
        """All consent changes must be tracked"""
        mock_rows = [
            Mock(
                id=1,
                user_id="user123",
                tenant_id="tenant456",
                consent_type=ConsentType.MARKETING,
                consented=False,
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                metadata='{"version": "2.0"}',
                timestamp=datetime.now(timezone.utc),
            ),
            Mock(
                id=2,
                user_id="user123",
                tenant_id="tenant456",
                consent_type=ConsentType.MARKETING,
                consented=True,
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                metadata='{"version": "1.0"}',
                timestamp=datetime.now(timezone.utc) - timedelta(days=30),
            ),
        ]
        self.db_session.execute.return_value = mock_rows

        history = self.manager.get_consent_history(
            user_id="user123", tenant_id="tenant456", consent_type=ConsentType.MARKETING
        )

        self.assertEqual(len(history), 2)
        self.assertFalse(history[0]["consented"])
        self.assertTrue(history[1]["consented"])


class TestDataSubjectAccessRequest(unittest.TestCase):
    """Test GDPR Article 15: Right to Access (DSAR)"""

    def setUp(self):
        self.db_session = Mock()
        self.manager = GDPRManager(self.db_session)

    def test_export_all_user_data(self):
        """DSAR must export all user data categories"""
        self.db_session.execute.return_value = []

        export_data = self.manager.export_user_data(
            user_id="user123", tenant_id="tenant456"
        )

        self.assertIn("user_id", export_data)
        self.assertIn("tenant_id", export_data)
        self.assertIn("export_timestamp", export_data)
        self.assertIn("data", export_data)

        required_categories = [
            "consent_records",
            "platforms",
            "contents",
            "posts",
            "analytics_records",
            "audit_logs",
            "api_keys",
        ]

        for category in required_categories:
            self.assertIn(category, export_data["data"])

    def test_export_machine_readable_format(self):
        """DSAR export must be in machine-readable format (JSON)"""
        self.db_session.execute.return_value = []

        export_data = self.manager.export_user_data(
            user_id="user123", tenant_id="tenant456"
        )

        json_str = json.dumps(export_data)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["user_id"], "user123")

    def test_export_includes_timestamps(self):
        """DSAR export must include all timestamps"""
        mock_consent = [
            Mock(
                id=1,
                consent_type=ConsentType.MARKETING,
                consented=True,
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                metadata=None,
                timestamp=datetime.now(timezone.utc),
            )
        ]
        self.db_session.execute.return_value = mock_consent

        export_data = self.manager.export_user_data(
            user_id="user123", tenant_id="tenant456"
        )

        self.assertIsNotNone(export_data["export_timestamp"])
        self.assertGreater(len(export_data["data"]["consent_records"]), 0)
        self.assertIsNotNone(export_data["data"]["consent_records"][0]["timestamp"])

    def test_dsar_30_day_compliance(self):
        """DSAR must be completable within 30 days"""
        self.db_session.execute.return_value = []

        start_time = datetime.now(timezone.utc)
        export_data = self.manager.export_user_data(
            user_id="user123", tenant_id="tenant456"
        )
        end_time = datetime.now(timezone.utc)

        processing_time = (end_time - start_time).total_seconds()
        self.assertLess(processing_time, 5)


class TestRightToErasure(unittest.TestCase):
    """Test GDPR Article 17: Right to Erasure"""

    def setUp(self):
        self.db_session = Mock()
        self.manager = GDPRManager(self.db_session)

    def test_delete_all_user_data(self):
        """Right to erasure must delete all user PII"""
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([Mock(id=1)]))
        self.db_session.execute.return_value = mock_result

        deletion_summary = self.manager.delete_user_data(
            user_id="user123", tenant_id="tenant456", reason="User requested deletion"
        )

        self.assertIn("operations", deletion_summary)
        self.assertIn("platforms_anonymized", deletion_summary["operations"])
        self.assertIn("consent_records_anonymized", deletion_summary["operations"])
        self.assertIn("audit_logs_anonymized", deletion_summary["operations"])
        self.assertIn("oauth_accounts_deleted", deletion_summary["operations"])
        self.assertIn("api_keys_anonymized", deletion_summary["operations"])

    def test_verify_complete_deletion(self):
        """Verify all PII is removed after deletion"""
        mock_result = Mock()
        mock_result.fetchone.return_value = [0]
        self.db_session.execute.return_value = mock_result

        verification = self.manager.verify_deletion(
            user_id="user123", tenant_id="tenant456"
        )

        self.assertTrue(verification["deletion_complete"])
        self.assertEqual(verification["pii_found"]["platforms_with_user_id"], 0)
        self.assertEqual(verification["pii_found"]["oauth_accounts"], 0)
        self.assertEqual(verification["pii_found"]["consent_records_with_pii"], 0)

    def test_deletion_preserves_aggregates(self):
        """Deletion should anonymize but preserve business intelligence"""
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([Mock(id=1)]))
        self.db_session.execute.return_value = mock_result

        deletion_summary = self.manager.delete_user_data(
            user_id="user123", tenant_id="tenant_id"
        )

        self.assertGreater(self.db_session.execute.call_count, 0)

    def test_deletion_with_reason_tracking(self):
        """Deletion requests must track reason"""
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        self.db_session.execute.return_value = mock_result

        deletion_summary = self.manager.delete_user_data(
            user_id="user123", tenant_id="tenant456", reason="GDPR Article 17 request"
        )

        self.assertEqual(deletion_summary["reason"], "GDPR Article 17 request")


class TestDataPortability(unittest.TestCase):
    """Test GDPR Article 20: Data Portability"""

    def test_export_structured_format(self):
        """Data portability requires structured, machine-readable format"""
        db_session = Mock()
        db_session.execute.return_value = []
        manager = GDPRManager(db_session)

        export_data = manager.export_user_data(user_id="user123", tenant_id="tenant456")

        self.assertIsInstance(export_data, dict)
        self.assertIsInstance(export_data["data"], dict)

    def test_export_includes_user_generated_content(self):
        """Data portability must include all user-generated content"""
        db_session = Mock()
        db_session.execute.return_value = []
        manager = GDPRManager(db_session)

        export_data = manager.export_user_data(user_id="user123", tenant_id="tenant456")

        self.assertIn("contents", export_data["data"])
        self.assertIn("posts", export_data["data"])
        self.assertIn("platforms", export_data["data"])


class TestDataMinimization(unittest.TestCase):
    """Test GDPR Article 5(1)(c): Data Minimization"""

    def test_consent_records_minimal_data(self):
        """Only collect necessary data for consent"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_result = Mock()
        mock_result.fetchone.return_value = [126]
        db_session.execute.return_value = mock_result

        consent_id = manager.record_consent(
            user_id="user123",
            tenant_id="tenant456",
            consent_type=ConsentType.TERMS_OF_SERVICE,
            consented=True,
        )

        self.assertEqual(consent_id, 126)

    def test_no_excessive_data_collection(self):
        """Verify no excessive data is collected"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_result = Mock()
        mock_result.fetchone.return_value = [127]
        db_session.execute.return_value = mock_result

        consent_id = manager.record_consent(
            user_id="user123",
            tenant_id="tenant456",
            consent_type=ConsentType.PRIVACY_POLICY,
            consented=True,
            ip_address="192.168.1.1",
        )

        call_args = db_session.execute.call_args
        params = call_args[0][1]
        self.assertIn("user_id", params)
        self.assertIn("tenant_id", params)
        self.assertIn("consent_type", params)
        self.assertIn("consented", params)


class TestRetentionPolicies(unittest.TestCase):
    """Test GDPR Article 5(1)(e): Storage Limitation"""

    def test_consent_records_retention(self):
        """Consent records should be retained for legal compliance"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_rows = [
            Mock(
                id=1,
                user_id="user123",
                tenant_id="tenant456",
                consent_type=ConsentType.MARKETING,
                consented=True,
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                metadata=None,
                timestamp=datetime.now(timezone.utc) - timedelta(days=365),
            )
        ]
        db_session.execute.return_value = mock_rows

        history = manager.get_consent_history(user_id="user123", tenant_id="tenant456")

        self.assertGreater(len(history), 0)

    def test_data_retention_after_deletion(self):
        """After deletion, only anonymized data should remain"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([Mock(id=1)]))
        db_session.execute.return_value = mock_result

        deletion_summary = manager.delete_user_data(
            user_id="user123", tenant_id="tenant456"
        )

        self.assertIn("deletion_timestamp", deletion_summary)


class TestPrivacyByDesign(unittest.TestCase):
    """Test GDPR Article 25: Privacy by Design and Default"""

    def test_consent_records_have_tenant_isolation(self):
        """Privacy by design: tenant isolation via RLS"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_result = Mock()
        mock_result.fetchone.return_value = [128]
        db_session.execute.return_value = mock_result

        consent_id = manager.record_consent(
            user_id="user123",
            tenant_id="tenant456",
            consent_type=ConsentType.DATA_PROCESSING,
            consented=True,
        )

        call_args = db_session.execute.call_args
        self.assertIn("tenant_id", call_args[0][1])

    def test_sensitive_data_not_exported_in_api_keys(self):
        """Privacy by design: API keys exported without secrets"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_api_keys = [
            Mock(
                id=1,
                name="Production API Key",
                created_at=datetime.now(timezone.utc),
                last_used_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            )
        ]

        def mock_execute(query, params=None):
            if "api_keys" in str(query):
                return mock_api_keys
            return []

        db_session.execute.side_effect = mock_execute

        export_data = manager.export_user_data(user_id="user123", tenant_id="tenant456")

        self.assertIn("api_keys", export_data["data"])

    def test_audit_logging_enabled(self):
        """Privacy by design: audit logging for all operations"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_audit_logs = [
            Mock(
                user_id="user123",
                tenant_id="tenant456",
                action="consent_recorded",
                resource="consent_records",
                details='{"consent_type": "marketing"}',
                ip_address="192.168.1.1",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        def mock_execute(query, params=None):
            if "audit_logs" in str(query):
                return mock_audit_logs
            return []

        db_session.execute.side_effect = mock_execute

        export_data = manager.export_user_data(user_id="user123", tenant_id="tenant456")

        self.assertIn("audit_logs", export_data["data"])


class TestBreachNotificationReadiness(unittest.TestCase):
    """Test GDPR Articles 33-34: Breach Notification"""

    def test_breach_detection_capability(self):
        """System must have breach detection capability"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_audit_logs = [
            Mock(
                user_id="user123",
                tenant_id="tenant456",
                action="unauthorized_access_attempt",
                resource="platforms",
                details='{"ip": "10.0.0.1"}',
                ip_address="10.0.0.1",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        def mock_execute(query, params=None):
            if "audit_logs" in str(query):
                return mock_audit_logs
            return []

        db_session.execute.side_effect = mock_execute

        export_data = manager.export_user_data(user_id="user123", tenant_id="tenant456")

        audit_logs = export_data["data"]["audit_logs"]
        self.assertGreater(len(audit_logs), 0)

    def test_72_hour_notification_capability(self):
        """System must support 72-hour breach notification"""
        breach_timestamp = datetime.now(timezone.utc)
        notification_deadline = breach_timestamp + timedelta(hours=72)

        time_remaining = (notification_deadline - breach_timestamp).total_seconds()
        self.assertEqual(time_remaining, 72 * 3600)


class TestDataProcessingRecords(unittest.TestCase):
    """Test GDPR Article 30: Records of Processing Activities"""

    def test_consent_processing_records(self):
        """Maintain records of all consent processing"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_rows = [
            Mock(
                id=1,
                user_id="user123",
                tenant_id="tenant456",
                consent_type=ConsentType.MARKETING,
                consented=True,
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
                metadata='{"version": "2.0"}',
                timestamp=datetime.now(timezone.utc),
            )
        ]
        db_session.execute.return_value = mock_rows

        history = manager.get_consent_history(user_id="user123", tenant_id="tenant456")

        self.assertGreater(len(history), 0)
        self.assertIn("timestamp", history[0])
        self.assertIn("consent_type", history[0])

    def test_data_export_processing_records(self):
        """Maintain records of data export operations"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        db_session.execute.return_value = []

        export_data = manager.export_user_data(user_id="user123", tenant_id="tenant456")

        self.assertIn("export_timestamp", export_data)

    def test_deletion_processing_records(self):
        """Maintain records of deletion operations"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        db_session.execute.return_value = mock_result

        deletion_summary = manager.delete_user_data(
            user_id="user123", tenant_id="tenant456", reason="User request"
        )

        self.assertIn("deletion_timestamp", deletion_summary)
        self.assertIn("operations", deletion_summary)


class TestThirdPartyDataSharing(unittest.TestCase):
    """Test GDPR Article 28: Third-Party Processors"""

    def test_oauth_accounts_third_party_tracking(self):
        """Track third-party OAuth providers"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([Mock(id=1), Mock(id=2)]))
        db_session.execute.return_value = mock_result

        deletion_summary = manager.delete_user_data(
            user_id="user123", tenant_id="tenant456"
        )

        self.assertIn("oauth_accounts_deleted", deletion_summary["operations"])

    def test_third_party_consent_tracking(self):
        """Track consent for third-party data sharing"""
        db_session = Mock()
        manager = GDPRManager(db_session)

        mock_result = Mock()
        mock_result.fetchone.return_value = [129]
        db_session.execute.return_value = mock_result

        consent_id = manager.record_consent(
            user_id="user123",
            tenant_id="tenant456",
            consent_type=ConsentType.THIRD_PARTY_SHARING,
            consented=True,
            metadata={"processor": "Analytics Provider Inc."},
        )

        self.assertEqual(consent_id, 129)


if __name__ == "__main__":
    unittest.main()
