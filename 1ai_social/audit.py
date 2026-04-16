"""Append-only audit logging system with HMAC signatures for compliance.

This module provides immutable audit logging for critical security and compliance events.
All logs are signed with HMAC-SHA256 to ensure integrity and prevent tampering.

Events logged:
- Authentication: login, logout, failed_login
- Credentials: token_created, token_revoked, token_accessed
- Data: post_created, post_deleted, user_created, user_deleted
- Admin: role_changed, permission_granted

Usage:
    from 1ai_social.audit import AuditLogger

    logger = AuditLogger(db_session, secret_key)
    logger.log_event(
        action="login",
        user_id="user123",
        tenant_id="tenant456",
        resource="auth",
        details={"method": "oauth"},
        ip_address="192.168.1.1"
    )
"""

import hmac
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text


class AuditLogger:
    """Append-only audit logger with HMAC signature verification."""

    def __init__(self, db_session: Session, secret_key: str):
        """Initialize audit logger.

        Args:
            db_session: SQLAlchemy database session
            secret_key: Secret key for HMAC signing (should be from config)
        """
        self.db = db_session
        self.secret_key = secret_key.encode("utf-8")

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for audit log entry.

        Args:
            data: Dictionary containing log data

        Returns:
            Hex-encoded HMAC signature
        """
        # Create canonical representation (sorted keys for consistency)
        canonical = json.dumps(data, sort_keys=True, default=str)
        signature = hmac.new(self.secret_key, canonical.encode("utf-8"), hashlib.sha256)
        return signature.hexdigest()

    def log_event(
        self,
        action: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> int:
        """Log an audit event with HMAC signature.

        Args:
            action: Action performed (e.g., 'login', 'token_created')
            user_id: User who performed the action
            tenant_id: Tenant context
            resource: Resource affected (e.g., 'auth', 'post:123')
            details: Additional context (stored as JSONB)
            ip_address: IP address of the request

        Returns:
            ID of the created audit log entry

        Raises:
            ValueError: If action is empty
        """
        if not action:
            raise ValueError("Action cannot be empty")

        timestamp = datetime.now(timezone.utc).replace(tzinfo=None)

        # Prepare data for signing (exclude signature itself)
        sign_data = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": action,
            "resource": resource,
            "details": details,
            "ip_address": ip_address,
            "timestamp": timestamp.isoformat(),
        }

        signature = self._generate_signature(sign_data)

        # Insert into audit_logs table (append-only)
        query = text("""
            INSERT INTO audit_logs 
            (user_id, tenant_id, action, resource, details, ip_address, timestamp, signature)
            VALUES 
            (:user_id, :tenant_id, :action, :resource, :details, :ip_address, :timestamp, :signature)
            RETURNING id
        """)

        result = self.db.execute(
            query,
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "action": action,
                "resource": resource,
                "details": json.dumps(details) if details else None,
                "ip_address": ip_address,
                "timestamp": timestamp,
                "signature": signature,
            },
        )

        log_id = result.scalar()
        self.db.flush()
        return log_id

    def verify_signature(self, log_id: int) -> bool:
        """Verify HMAC signature of an audit log entry.

        Args:
            log_id: ID of the audit log entry

        Returns:
            True if signature is valid, False otherwise
        """
        query = text("""
            SELECT user_id, tenant_id, action, resource, details, ip_address, timestamp, signature
            FROM audit_logs
            WHERE id = :log_id
        """)

        result = self.db.execute(query, {"log_id": log_id}).fetchone()

        if not result:
            return False

        # Reconstruct data for verification
        timestamp_str = (
            result.timestamp
            if isinstance(result.timestamp, str)
            else result.timestamp.isoformat()
        )
        timestamp_str = timestamp_str.replace(" ", "T")

        sign_data = {
            "user_id": result.user_id,
            "tenant_id": result.tenant_id,
            "action": result.action,
            "resource": result.resource,
            "details": json.loads(result.details) if result.details else None,
            "ip_address": result.ip_address,
            "timestamp": timestamp_str,
        }

        expected_signature = self._generate_signature(sign_data)
        return hmac.compare_digest(expected_signature, result.signature)

    def query_logs(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query audit logs with filters.

        Args:
            user_id: Filter by user ID
            tenant_id: Filter by tenant ID
            action: Filter by action
            resource: Filter by resource
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum number of results (default 100)
            offset: Offset for pagination (default 0)

        Returns:
            List of audit log entries as dictionaries
        """
        conditions = []
        params = {}

        if user_id:
            conditions.append("user_id = :user_id")
            params["user_id"] = user_id

        if tenant_id:
            conditions.append("tenant_id = :tenant_id")
            params["tenant_id"] = tenant_id

        if action:
            conditions.append("action = :action")
            params["action"] = action

        if resource:
            conditions.append("resource = :resource")
            params["resource"] = resource

        if start_time:
            conditions.append("timestamp >= :start_time")
            params["start_time"] = start_time

        if end_time:
            conditions.append("timestamp <= :end_time")
            params["end_time"] = end_time

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = text(f"""
            SELECT id, user_id, tenant_id, action, resource, details, ip_address, timestamp, signature
            FROM audit_logs
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """)

        params["limit"] = limit
        params["offset"] = offset

        results = self.db.execute(query, params).fetchall()

        return [
            {
                "id": row.id,
                "user_id": row.user_id,
                "tenant_id": row.tenant_id,
                "action": row.action,
                "resource": row.resource,
                "details": json.loads(row.details) if row.details else None,
                "ip_address": row.ip_address,
                "timestamp": row.timestamp
                if isinstance(row.timestamp, str)
                else row.timestamp.isoformat(),
                "signature": row.signature,
            }
            for row in results
        ]

    def verify_log_integrity(
        self, log_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Verify integrity of audit logs by checking HMAC signatures.

        Args:
            log_ids: Optional list of specific log IDs to verify. If None, verifies all logs.

        Returns:
            Dictionary with verification results:
            {
                'total': int,
                'valid': int,
                'invalid': int,
                'invalid_ids': List[int]
            }
        """
        if log_ids:
            placeholders = ",".join([":id" + str(i) for i in range(len(log_ids))])
            params = {f"id{i}": log_id for i, log_id in enumerate(log_ids)}
            query = text(f"""
                SELECT id FROM audit_logs
                WHERE id IN ({placeholders})
                ORDER BY id
            """)
            results = self.db.execute(query, params).fetchall()
        else:
            query = text("SELECT id FROM audit_logs ORDER BY id")
            results = self.db.execute(query).fetchall()

        total = len(results)
        invalid_ids = []

        for row in results:
            if not self.verify_signature(row.id):
                invalid_ids.append(row.id)

        return {
            "total": total,
            "valid": total - len(invalid_ids),
            "invalid": len(invalid_ids),
            "invalid_ids": invalid_ids,
        }


# Convenience functions for common audit events


def log_authentication(
    db: Session,
    secret_key: str,
    action: str,
    user_id: str,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> int:
    """Log authentication event (login, logout, failed_login)."""
    logger = AuditLogger(db, secret_key)
    return logger.log_event(
        action=action,
        user_id=user_id,
        resource="auth",
        details=details,
        ip_address=ip_address,
    )


def log_credential_access(
    db: Session,
    secret_key: str,
    action: str,
    user_id: str,
    tenant_id: Optional[str] = None,
    resource: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> int:
    """Log credential access event (token_created, token_revoked, token_accessed)."""
    logger = AuditLogger(db, secret_key)
    return logger.log_event(
        action=action,
        user_id=user_id,
        tenant_id=tenant_id,
        resource=resource,
        details=details,
        ip_address=ip_address,
    )


def log_data_change(
    db: Session,
    secret_key: str,
    action: str,
    user_id: str,
    tenant_id: Optional[str] = None,
    resource: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> int:
    """Log data change event (post_created, post_deleted, user_created, user_deleted)."""
    logger = AuditLogger(db, secret_key)
    return logger.log_event(
        action=action,
        user_id=user_id,
        tenant_id=tenant_id,
        resource=resource,
        details=details,
        ip_address=ip_address,
    )


def log_admin_action(
    db: Session,
    secret_key: str,
    action: str,
    user_id: str,
    tenant_id: Optional[str] = None,
    resource: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> int:
    """Log admin action (role_changed, permission_granted)."""
    logger = AuditLogger(db, secret_key)
    return logger.log_event(
        action=action,
        user_id=user_id,
        tenant_id=tenant_id,
        resource=resource,
        details=details,
        ip_address=ip_address,
    )
