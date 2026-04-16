"""API Key Management System with Tenant Scoping

This module provides secure API key generation, validation, and management
with strict tenant isolation to prevent cross-tenant access.

Key Features:
- Tenant-scoped API keys (keys cannot access other tenants)
- Secure key generation with SHA-256 hashing
- Scope-based permissions (read, write, admin)
- Key expiration support
- Key rotation capabilities

Key Format: sk_live_<base64_encoded_random>_<checksum>
Example: sk_live_dGVzdGtleQ==_a3f2c1
"""

import secrets
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session


class APIKeyError(Exception):
    """Base exception for API key operations"""

    pass


class InvalidAPIKeyError(APIKeyError):
    """Raised when API key is invalid or malformed"""

    pass


class ExpiredAPIKeyError(APIKeyError):
    """Raised when API key has expired"""

    pass


class InsufficientScopeError(APIKeyError):
    """Raised when API key lacks required scope"""

    pass


class CrossTenantAccessError(APIKeyError):
    """Raised when attempting cross-tenant access"""

    pass


def generate_api_key(
    tenant_id: str, scopes: List[str], name: str, expires_in_days: Optional[int] = None
) -> tuple[str, str]:
    """Generate a new API key with tenant scoping.

    Args:
        tenant_id: Tenant ID to scope the key to
        scopes: List of scopes (e.g., ['read', 'write', 'admin'])
        name: Human-readable name for the key
        expires_in_days: Optional expiration in days (None = no expiration)

    Returns:
        Tuple of (api_key, key_hash) where:
        - api_key: The full key to return to user (only shown once)
        - key_hash: SHA-256 hash to store in database

    Example:
        >>> api_key, key_hash = generate_api_key("tenant-123", ["read", "write"], "Production Key")
        >>> print(api_key)
        sk_live_dGVzdGtleQ==_a3f2c1
    """
    # Generate 32 bytes of random data
    random_bytes = secrets.token_bytes(32)
    key_b64 = base64.b64encode(random_bytes).decode("utf-8").rstrip("=")

    # Calculate checksum (first 6 chars of SHA-256)
    checksum = hashlib.sha256(key_b64.encode()).hexdigest()[:6]

    # Format: sk_live_<base64>_<checksum>
    api_key = f"sk_live_{key_b64}_{checksum}"

    # Hash the full key for storage (SHA-256)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    return api_key, key_hash


def validate_api_key_format(api_key: str) -> bool:
    """Validate API key format without database lookup.

    Args:
        api_key: The API key to validate

    Returns:
        True if format is valid, False otherwise

    Example:
        >>> validate_api_key_format("sk_live_dGVzdGtleQ_a3f2c1")
        True
        >>> validate_api_key_format("invalid_key")
        False
    """
    if not api_key.startswith("sk_live_"):
        return False

    parts = api_key.split("_")
    if len(parts) != 4:
        return False

    key_b64 = parts[2]
    checksum = parts[3]

    expected_checksum = hashlib.sha256(key_b64.encode()).hexdigest()[:6]

    return checksum == expected_checksum


def create_api_key(
    session: Session,
    tenant_id: str,
    scopes: List[str],
    name: str,
    expires_in_days: Optional[int] = None,
) -> Dict[str, Any]:
    """Create and store a new API key in the database.

    Args:
        session: SQLAlchemy database session
        tenant_id: Tenant ID to scope the key to
        scopes: List of scopes (e.g., ['read', 'write', 'admin'])
        name: Human-readable name for the key
        expires_in_days: Optional expiration in days

    Returns:
        Dictionary containing:
        - api_key: The full key (only shown once)
        - key_id: Database ID of the key
        - tenant_id: Tenant ID
        - scopes: List of scopes
        - name: Key name
        - expires_at: Expiration timestamp (if set)
        - created_at: Creation timestamp

    Raises:
        APIKeyError: If key creation fails
    """
    # Generate the key
    api_key, key_hash = generate_api_key(tenant_id, scopes, name, expires_in_days)

    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    # Insert into database
    query = text("""
        INSERT INTO api_keys (tenant_id, key_hash, scopes, name, expires_at, created_at)
        VALUES (:tenant_id, :key_hash, CAST(:scopes AS jsonb), :name, :expires_at, NOW())
        RETURNING id, tenant_id, scopes, name, expires_at, created_at
    """)

    session.execute(text("SELECT set_config('app.user_role', 'admin', false)"))

    result = session.execute(
        query,
        {
            "tenant_id": tenant_id,
            "key_hash": key_hash,
            "scopes": str(scopes).replace("'", '"'),
            "name": name,
            "expires_at": expires_at,
        },
    ).fetchone()

    session.execute(text("SELECT set_config('app.user_role', '', false)"))
    session.commit()

    return {
        "api_key": api_key,  # Only shown once!
        "key_id": result.id,
        "tenant_id": result.tenant_id,
        "scopes": result.scopes,
        "name": result.name,
        "expires_at": result.expires_at,
        "created_at": result.created_at,
    }


def validate_api_key(
    session: Session, api_key: str, required_scopes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Validate an API key and return its metadata.

    Args:
        session: SQLAlchemy database session
        api_key: The API key to validate
        required_scopes: Optional list of required scopes

    Returns:
        Dictionary containing:
        - key_id: Database ID
        - tenant_id: Tenant ID (for setting context)
        - scopes: List of scopes
        - name: Key name

    Raises:
        InvalidAPIKeyError: If key is invalid or not found
        ExpiredAPIKeyError: If key has expired
        InsufficientScopeError: If key lacks required scopes
    """
    # Validate format first
    if not validate_api_key_format(api_key):
        raise InvalidAPIKeyError("Invalid API key format")

    # Hash the key for lookup
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Look up key in database
    query = text("""
        SELECT id, tenant_id, scopes, name, expires_at
        FROM api_keys
        WHERE key_hash = :key_hash
    """)

    result = session.execute(query, {"key_hash": key_hash}).fetchone()

    if not result:
        raise InvalidAPIKeyError("API key not found")

    # Check expiration
    if result.expires_at and result.expires_at < datetime.now(timezone.utc):
        raise ExpiredAPIKeyError("API key has expired")

    # Check scopes
    key_scopes = result.scopes if isinstance(result.scopes, list) else []

    if required_scopes:
        missing_scopes = set(required_scopes) - set(key_scopes)
        if missing_scopes:
            raise InsufficientScopeError(
                f"API key missing required scopes: {', '.join(missing_scopes)}"
            )

    return {
        "key_id": result.id,
        "tenant_id": result.tenant_id,
        "scopes": key_scopes,
        "name": result.name,
    }


def set_tenant_context_from_key(session: Session, api_key: str) -> str:
    """Validate API key and set tenant context for RLS.

    This function:
    1. Validates the API key
    2. Extracts the tenant_id
    3. Sets the PostgreSQL session variable for RLS

    Args:
        session: SQLAlchemy database session
        api_key: The API key to validate

    Returns:
        tenant_id: The tenant ID extracted from the key

    Raises:
        InvalidAPIKeyError: If key is invalid
        ExpiredAPIKeyError: If key has expired
    """
    # Validate key and get metadata
    key_data = validate_api_key(session, api_key)
    tenant_id = key_data["tenant_id"]

    # Set tenant context for RLS
    session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"),
        {"tenant_id": tenant_id},
    )

    return tenant_id


def rotate_api_key(
    session: Session, old_api_key: str, expires_in_days: Optional[int] = None
) -> Dict[str, Any]:
    """Rotate an API key (create new key with same scopes, revoke old key).

    Args:
        session: SQLAlchemy database session
        old_api_key: The existing API key to rotate
        expires_in_days: Optional expiration for new key

    Returns:
        Dictionary containing new key data (same format as create_api_key)

    Raises:
        InvalidAPIKeyError: If old key is invalid
    """
    # Validate old key
    old_key_data = validate_api_key(session, old_api_key)

    # Create new key with same scopes
    new_key_data = create_api_key(
        session,
        tenant_id=old_key_data["tenant_id"],
        scopes=old_key_data["scopes"],
        name=f"{old_key_data['name']} (rotated)",
        expires_in_days=expires_in_days,
    )

    # Revoke old key
    revoke_api_key(session, old_api_key)

    return new_key_data


def revoke_api_key(session: Session, api_key: str) -> None:
    """Revoke an API key (delete from database).

    Args:
        session: SQLAlchemy database session
        api_key: The API key to revoke

    Raises:
        InvalidAPIKeyError: If key is invalid
    """
    # Hash the key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Delete from database
    query = text("DELETE FROM api_keys WHERE key_hash = :key_hash")
    result = session.execute(query, {"key_hash": key_hash})
    session.commit()

    if result.rowcount == 0:
        raise InvalidAPIKeyError("API key not found")


def list_api_keys(session: Session, tenant_id: str) -> List[Dict[str, Any]]:
    """List all API keys for a tenant (without revealing the actual keys).

    Args:
        session: SQLAlchemy database session
        tenant_id: Tenant ID to list keys for

    Returns:
        List of dictionaries containing key metadata (no actual keys)
    """
    query = text("""
        SELECT id, tenant_id, scopes, name, expires_at, created_at
        FROM api_keys
        WHERE tenant_id = :tenant_id
        ORDER BY created_at DESC
    """)

    results = session.execute(query, {"tenant_id": tenant_id}).fetchall()

    return [
        {
            "key_id": row.id,
            "tenant_id": row.tenant_id,
            "scopes": row.scopes,
            "name": row.name,
            "expires_at": row.expires_at,
            "created_at": row.created_at,
            "is_expired": row.expires_at
            and row.expires_at < datetime.now(timezone.utc),
        }
        for row in results
    ]
