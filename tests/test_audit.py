import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from importlib import import_module

audit_module = import_module("1ai_social.audit")
AuditLogger = audit_module.AuditLogger
log_authentication = audit_module.log_authentication
log_credential_access = audit_module.log_credential_access
log_data_change = audit_module.log_data_change
log_admin_action = audit_module.log_admin_action


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(255),
                tenant_id VARCHAR(255),
                action VARCHAR(100) NOT NULL,
                resource VARCHAR(255),
                details TEXT,
                ip_address VARCHAR(45),
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                signature VARCHAR(64) NOT NULL
            )
        """)
        )
        conn.commit()

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def audit_logger(db_session):
    return AuditLogger(db_session, "test-secret-key-for-hmac-signing")


def test_log_event_creates_entry(audit_logger, db_session):
    log_id = audit_logger.log_event(
        action="login",
        user_id="user123",
        tenant_id="tenant456",
        resource="auth",
        details={"method": "oauth", "provider": "google"},
        ip_address="192.168.1.1",
    )

    assert log_id is not None

    result = db_session.execute(
        text("SELECT * FROM audit_logs WHERE id = :id"), {"id": log_id}
    ).fetchone()

    assert result is not None
    assert result.user_id == "user123"
    assert result.tenant_id == "tenant456"
    assert result.action == "login"
    assert result.resource == "auth"
    assert result.ip_address == "192.168.1.1"
    assert result.signature is not None
    assert len(result.signature) == 64


def test_log_event_requires_action(audit_logger):
    with pytest.raises(ValueError, match="Action cannot be empty"):
        audit_logger.log_event(action="")


def test_signature_verification_valid(audit_logger, db_session):
    log_id = audit_logger.log_event(
        action="token_created", user_id="user123", resource="token:abc123"
    )

    assert audit_logger.verify_signature(log_id) is True


def test_signature_verification_invalid_after_tampering(audit_logger, db_session):
    log_id = audit_logger.log_event(
        action="post_created", user_id="user123", resource="post:456"
    )

    db_session.execute(
        text("UPDATE audit_logs SET action = 'post_deleted' WHERE id = :id"),
        {"id": log_id},
    )
    db_session.commit()

    assert audit_logger.verify_signature(log_id) is False


def test_signature_verification_nonexistent_log(audit_logger):
    assert audit_logger.verify_signature(99999) is False


def test_query_logs_by_user(audit_logger):
    audit_logger.log_event(action="login", user_id="user1")
    audit_logger.log_event(action="logout", user_id="user1")
    audit_logger.log_event(action="login", user_id="user2")

    logs = audit_logger.query_logs(user_id="user1")

    assert len(logs) == 2
    assert all(log["user_id"] == "user1" for log in logs)


def test_query_logs_by_tenant(audit_logger):
    audit_logger.log_event(action="post_created", tenant_id="tenant1", user_id="user1")
    audit_logger.log_event(action="post_deleted", tenant_id="tenant1", user_id="user2")
    audit_logger.log_event(action="post_created", tenant_id="tenant2", user_id="user3")

    logs = audit_logger.query_logs(tenant_id="tenant1")

    assert len(logs) == 2
    assert all(log["tenant_id"] == "tenant1" for log in logs)


def test_query_logs_by_action(audit_logger):
    audit_logger.log_event(action="login", user_id="user1")
    audit_logger.log_event(action="login", user_id="user2")
    audit_logger.log_event(action="logout", user_id="user1")

    logs = audit_logger.query_logs(action="login")

    assert len(logs) == 2
    assert all(log["action"] == "login" for log in logs)


def test_query_logs_by_time_range(audit_logger, db_session):
    now = datetime.now(timezone.utc)

    log_id1 = audit_logger.log_event(action="event1", user_id="user1")

    db_session.execute(
        text("UPDATE audit_logs SET timestamp = :ts WHERE id = :id"),
        {"ts": now - timedelta(hours=2), "id": log_id1},
    )
    db_session.commit()

    log_id2 = audit_logger.log_event(action="event2", user_id="user1")

    logs = audit_logger.query_logs(
        start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1)
    )

    assert len(logs) == 1
    assert logs[0]["action"] == "event2"


def test_query_logs_pagination(audit_logger):
    for i in range(15):
        audit_logger.log_event(action=f"event{i}", user_id="user1")

    page1 = audit_logger.query_logs(limit=10, offset=0)
    page2 = audit_logger.query_logs(limit=10, offset=10)

    assert len(page1) == 10
    assert len(page2) == 5


def test_verify_log_integrity_all_valid(audit_logger):
    audit_logger.log_event(action="event1", user_id="user1")
    audit_logger.log_event(action="event2", user_id="user2")
    audit_logger.log_event(action="event3", user_id="user3")

    result = audit_logger.verify_log_integrity()

    assert result["total"] == 3
    assert result["valid"] == 3
    assert result["invalid"] == 0
    assert result["invalid_ids"] == []


def test_verify_log_integrity_with_tampering(audit_logger, db_session):
    log_id1 = audit_logger.log_event(action="event1", user_id="user1")
    log_id2 = audit_logger.log_event(action="event2", user_id="user2")
    log_id3 = audit_logger.log_event(action="event3", user_id="user3")

    db_session.execute(
        text("UPDATE audit_logs SET action = 'tampered' WHERE id = :id"),
        {"id": log_id2},
    )
    db_session.commit()

    result = audit_logger.verify_log_integrity()

    assert result["total"] == 3
    assert result["valid"] == 2
    assert result["invalid"] == 1
    assert log_id2 in result["invalid_ids"]


def test_verify_log_integrity_specific_logs(audit_logger, db_session):
    log_id1 = audit_logger.log_event(action="event1", user_id="user1")
    log_id2 = audit_logger.log_event(action="event2", user_id="user2")
    log_id3 = audit_logger.log_event(action="event3", user_id="user3")

    result = audit_logger.verify_log_integrity(log_ids=[log_id1, log_id3])

    assert result["total"] == 2
    assert result["valid"] == 2


def test_log_authentication_convenience(db_session):
    log_id = log_authentication(
        db=db_session,
        secret_key="test-key",
        action="login",
        user_id="user123",
        ip_address="10.0.0.1",
        details={"method": "password"},
    )

    assert log_id is not None

    result = db_session.execute(
        text("SELECT * FROM audit_logs WHERE id = :id"), {"id": log_id}
    ).fetchone()

    assert result.action == "login"
    assert result.resource == "auth"


def test_log_credential_access_convenience(db_session):
    log_id = log_credential_access(
        db=db_session,
        secret_key="test-key",
        action="token_accessed",
        user_id="user123",
        tenant_id="tenant456",
        resource="token:xyz789",
    )

    assert log_id is not None


def test_log_data_change_convenience(db_session):
    log_id = log_data_change(
        db=db_session,
        secret_key="test-key",
        action="post_created",
        user_id="user123",
        tenant_id="tenant456",
        resource="post:123",
    )

    assert log_id is not None


def test_log_admin_action_convenience(db_session):
    log_id = log_admin_action(
        db=db_session,
        secret_key="test-key",
        action="role_changed",
        user_id="admin123",
        tenant_id="tenant456",
        resource="user:789",
        details={"old_role": "user", "new_role": "admin"},
    )

    assert log_id is not None


def test_details_stored_as_json(audit_logger, db_session):
    details = {
        "key1": "value1",
        "key2": 123,
        "key3": ["a", "b", "c"],
        "key4": {"nested": "object"},
    }

    log_id = audit_logger.log_event(
        action="test_action", user_id="user123", details=details
    )

    logs = audit_logger.query_logs(user_id="user123")

    assert len(logs) == 1
    assert logs[0]["details"] == details


def test_signature_consistency(audit_logger):
    log_id1 = audit_logger.log_event(
        action="test", user_id="user1", details={"key": "value"}
    )

    log_id2 = audit_logger.log_event(
        action="test", user_id="user1", details={"key": "value"}
    )

    logs = audit_logger.query_logs(user_id="user1")

    assert logs[0]["signature"] != logs[1]["signature"]
