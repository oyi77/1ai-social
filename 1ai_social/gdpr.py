"""GDPR compliance module with consent management, DSAR, and data deletion.

This module provides GDPR-compliant data handling including:
- Consent recording and management
- Data Subject Access Requests (DSAR) - 30-day legal requirement
- Right to be forgotten (data deletion with anonymization)
- Consent history tracking

Usage:
    from 1ai_social.gdpr import GDPRManager

    manager = GDPRManager(db_session)

    # Record consent
    manager.record_consent(
        user_id="user123",
        tenant_id="tenant456",
        consent_type="marketing",
        consented=True,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0..."
    )

    # Export user data (DSAR)
    data = manager.export_user_data(user_id="user123", tenant_id="tenant456")

    # Delete user data (anonymize PII)
    manager.delete_user_data(user_id="user123", tenant_id="tenant456")
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
import json


class ConsentType:
    """Standard consent types for GDPR compliance."""

    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    DATA_PROCESSING = "data_processing"
    THIRD_PARTY_SHARING = "third_party_sharing"


class GDPRManager:
    """GDPR compliance manager for consent and data subject rights."""

    def __init__(self, db_session: Session):
        """Initialize GDPR manager.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def record_consent(
        self,
        user_id: str,
        tenant_id: str,
        consent_type: str,
        consented: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Record user consent for GDPR compliance.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            consent_type: Type of consent (marketing, analytics, etc.)
            consented: Whether user consented (True) or withdrew (False)
            ip_address: IP address of the request
            user_agent: User agent string
            metadata: Additional metadata (e.g., consent version, form ID)

        Returns:
            Consent record ID
        """
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        metadata_json = json.dumps(metadata) if metadata else None

        query = text("""
            INSERT INTO consent_records 
            (user_id, tenant_id, consent_type, consented, ip_address, user_agent, metadata, timestamp)
            VALUES 
            (:user_id, :tenant_id, :consent_type, :consented, :ip_address, :user_agent, :metadata, :timestamp)
            RETURNING id
        """)

        result = self.db.execute(
            query,
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "consent_type": consent_type,
                "consented": consented,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "metadata": metadata_json,
                "timestamp": timestamp,
            },
        )
        self.db.commit()

        return result.fetchone()[0]

    def get_consent_history(
        self, user_id: str, tenant_id: str, consent_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get consent history for a user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            consent_type: Optional filter by consent type

        Returns:
            List of consent records
        """
        if consent_type:
            query = text("""
                SELECT id, user_id, tenant_id, consent_type, consented, 
                       ip_address, user_agent, metadata, timestamp
                FROM consent_records
                WHERE user_id = :user_id AND tenant_id = :tenant_id AND consent_type = :consent_type
                ORDER BY timestamp DESC
            """)
            result = self.db.execute(
                query,
                {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "consent_type": consent_type,
                },
            )
        else:
            query = text("""
                SELECT id, user_id, tenant_id, consent_type, consented, 
                       ip_address, user_agent, metadata, timestamp
                FROM consent_records
                WHERE user_id = :user_id AND tenant_id = :tenant_id
                ORDER BY timestamp DESC
            """)
            result = self.db.execute(
                query, {"user_id": user_id, "tenant_id": tenant_id}
            )

        records = []
        for row in result:
            records.append(
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "tenant_id": row.tenant_id,
                    "consent_type": row.consent_type,
                    "consented": row.consented,
                    "ip_address": row.ip_address,
                    "user_agent": row.user_agent,
                    "metadata": json.loads(row.metadata) if row.metadata else None,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                }
            )

        return records

    def get_current_consent(
        self, user_id: str, tenant_id: str, consent_type: str
    ) -> Optional[bool]:
        """Get current consent status for a specific type.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            consent_type: Type of consent

        Returns:
            True if consented, False if withdrawn, None if no record
        """
        query = text("""
            SELECT consented
            FROM consent_records
            WHERE user_id = :user_id AND tenant_id = :tenant_id AND consent_type = :consent_type
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        result = self.db.execute(
            query,
            {"user_id": user_id, "tenant_id": tenant_id, "consent_type": consent_type},
        )

        row = result.fetchone()
        return row.consented if row else None

    def export_user_data(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Export all user data for DSAR (Data Subject Access Request).

        This fulfills the GDPR right to data portability.
        Must be completed within 30 days of request.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            Dictionary containing all user data
        """
        export_data = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {},
        }

        # Export consent records
        consent_query = text("""
            SELECT id, consent_type, consented, ip_address, user_agent, metadata, timestamp
            FROM consent_records
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            ORDER BY timestamp DESC
        """)
        consent_result = self.db.execute(
            consent_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        export_data["data"]["consent_records"] = [
            {
                "id": row.id,
                "consent_type": row.consent_type,
                "consented": row.consented,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "metadata": json.loads(row.metadata) if row.metadata else None,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
            for row in consent_result
        ]

        # Export platforms
        platforms_query = text("""
            SELECT id, name, user_id, created_at, updated_at
            FROM platforms
            WHERE user_id = :user_id AND tenant_id = :tenant_id
        """)
        platforms_result = self.db.execute(
            platforms_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        export_data["data"]["platforms"] = [
            {
                "id": row.id,
                "name": row.name,
                "user_id": row.user_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in platforms_result
        ]

        # Export contents
        contents_query = text("""
            SELECT id, text, platform, media_url, video_path, hashtags, mentions, created_at
            FROM contents
            WHERE tenant_id = :tenant_id
        """)
        contents_result = self.db.execute(contents_query, {"tenant_id": tenant_id})
        export_data["data"]["contents"] = [
            {
                "id": row.id,
                "text": row.text,
                "platform": row.platform,
                "media_url": row.media_url,
                "video_path": row.video_path,
                "hashtags": row.hashtags,
                "mentions": row.mentions,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in contents_result
        ]

        # Export posts
        posts_query = text("""
            SELECT id, content_id, platform_id, scheduled_time, published_time, 
                   status, platform_post_id, error_message, created_at, updated_at
            FROM posts
            WHERE tenant_id = :tenant_id
        """)
        posts_result = self.db.execute(posts_query, {"tenant_id": tenant_id})
        export_data["data"]["posts"] = [
            {
                "id": row.id,
                "content_id": row.content_id,
                "platform_id": row.platform_id,
                "scheduled_time": row.scheduled_time.isoformat()
                if row.scheduled_time
                else None,
                "published_time": row.published_time.isoformat()
                if row.published_time
                else None,
                "status": row.status,
                "platform_post_id": row.platform_post_id,
                "error_message": row.error_message,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in posts_result
        ]

        # Export analytics
        analytics_query = text("""
            SELECT id, post_id, platform_id, content_type, views, likes, shares, 
                   comments, engagement_rate, recorded_at
            FROM analytics_records
            WHERE tenant_id = :tenant_id
        """)
        analytics_result = self.db.execute(analytics_query, {"tenant_id": tenant_id})
        export_data["data"]["analytics_records"] = [
            {
                "id": row.id,
                "post_id": row.post_id,
                "platform_id": row.platform_id,
                "content_type": row.content_type,
                "views": row.views,
                "likes": row.likes,
                "shares": row.shares,
                "comments": row.comments,
                "engagement_rate": row.engagement_rate,
                "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
            }
            for row in analytics_result
        ]

        # Export audit logs
        audit_query = text("""
            SELECT user_id, tenant_id, action, resource, details, ip_address, timestamp
            FROM audit_logs
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            ORDER BY timestamp DESC
        """)
        audit_result = self.db.execute(
            audit_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        export_data["data"]["audit_logs"] = [
            {
                "user_id": row.user_id,
                "tenant_id": row.tenant_id,
                "action": row.action,
                "resource": row.resource,
                "details": json.loads(row.details) if row.details else None,
                "ip_address": row.ip_address,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            }
            for row in audit_result
        ]

        # Export API keys (without secrets)
        api_keys_query = text("""
            SELECT id, name, created_at, last_used_at, expires_at
            FROM api_keys
            WHERE tenant_id = :tenant_id
        """)
        api_keys_result = self.db.execute(api_keys_query, {"tenant_id": tenant_id})
        export_data["data"]["api_keys"] = [
            {
                "id": row.id,
                "name": row.name,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "last_used_at": row.last_used_at.isoformat()
                if row.last_used_at
                else None,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            }
            for row in api_keys_result
        ]

        return export_data

    def delete_user_data(
        self, user_id: str, tenant_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete user data (anonymize PII) for GDPR right to be forgotten.

        This anonymizes personally identifiable information while preserving
        aggregate statistics and business intelligence.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            reason: Optional reason for deletion

        Returns:
            Summary of deletion operations
        """
        deletion_summary = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "deletion_timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "operations": {},
        }

        # Anonymize platforms (remove credentials, keep aggregates)
        platforms_query = text("""
            UPDATE platforms
            SET credentials = '[REDACTED]',
                user_id = 'deleted_user',
                updated_at = :timestamp
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            RETURNING id
        """)
        platforms_result = self.db.execute(
            platforms_query,
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "timestamp": datetime.now(timezone.utc).replace(tzinfo=None),
            },
        )
        deletion_summary["operations"]["platforms_anonymized"] = len(
            list(platforms_result)
        )

        # Anonymize consent records (keep consent status for legal compliance)
        consent_query = text("""
            UPDATE consent_records
            SET ip_address = NULL,
                user_agent = NULL,
                metadata = NULL
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            RETURNING id
        """)
        consent_result = self.db.execute(
            consent_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        deletion_summary["operations"]["consent_records_anonymized"] = len(
            list(consent_result)
        )

        # Anonymize audit logs (keep action/resource for security analysis)
        audit_query = text("""
            UPDATE audit_logs
            SET user_id = 'deleted_user',
                ip_address = NULL,
                details = NULL
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            RETURNING id
        """)
        audit_result = self.db.execute(
            audit_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        deletion_summary["operations"]["audit_logs_anonymized"] = len(
            list(audit_result)
        )

        # Delete OAuth accounts (complete removal)
        oauth_query = text("""
            DELETE FROM oauth_accounts
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            RETURNING id
        """)
        oauth_result = self.db.execute(
            oauth_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        deletion_summary["operations"]["oauth_accounts_deleted"] = len(
            list(oauth_result)
        )

        # Anonymize API keys
        api_keys_query = text("""
            UPDATE api_keys
            SET key_hash = '[REDACTED]',
                name = 'deleted_key'
            WHERE tenant_id = :tenant_id
            RETURNING id
        """)
        api_keys_result = self.db.execute(api_keys_query, {"tenant_id": tenant_id})
        deletion_summary["operations"]["api_keys_anonymized"] = len(
            list(api_keys_result)
        )

        # Contents, posts, and analytics are kept for business intelligence
        # but are already scoped by tenant_id, not user_id

        self.db.commit()

        return deletion_summary

    def verify_deletion(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """Verify that user data has been properly deleted/anonymized.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            Verification report showing remaining PII
        """
        verification = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "verification_timestamp": datetime.now(timezone.utc).isoformat(),
            "pii_found": {},
        }

        # Check platforms
        platforms_query = text("""
            SELECT COUNT(*) as count
            FROM platforms
            WHERE user_id = :user_id AND tenant_id = :tenant_id
        """)
        platforms_result = self.db.execute(
            platforms_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        verification["pii_found"]["platforms_with_user_id"] = (
            platforms_result.fetchone()[0]
        )

        # Check audit logs
        audit_query = text("""
            SELECT COUNT(*) as count
            FROM audit_logs
            WHERE user_id = :user_id AND tenant_id = :tenant_id
        """)
        audit_result = self.db.execute(
            audit_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        verification["pii_found"]["audit_logs_with_user_id"] = audit_result.fetchone()[
            0
        ]

        # Check OAuth accounts
        oauth_query = text("""
            SELECT COUNT(*) as count
            FROM oauth_accounts
            WHERE user_id = :user_id AND tenant_id = :tenant_id
        """)
        oauth_result = self.db.execute(
            oauth_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        verification["pii_found"]["oauth_accounts"] = oauth_result.fetchone()[0]

        # Check consent records with PII
        consent_query = text("""
            SELECT COUNT(*) as count
            FROM consent_records
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            AND (ip_address IS NOT NULL OR user_agent IS NOT NULL)
        """)
        consent_result = self.db.execute(
            consent_query, {"user_id": user_id, "tenant_id": tenant_id}
        )
        verification["pii_found"]["consent_records_with_pii"] = (
            consent_result.fetchone()[0]
        )

        verification["deletion_complete"] = all(
            count == 0 for count in verification["pii_found"].values()
        )

        return verification
