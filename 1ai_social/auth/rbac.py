"""Role-Based Access Control (RBAC) module for team management.

Provides role enforcement, permission checking, and team invite functionality.
"""

import logging
import secrets
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Any, List, Dict
from functools import wraps
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class RBACError(Exception):
    """Base exception for RBAC errors."""

    pass


class PermissionDeniedError(RBACError):
    """Raised when user lacks required permission."""

    pass


class RoleNotFoundError(RBACError):
    """Raised when role does not exist."""

    pass


class InviteError(RBACError):
    """Raised when invite operation fails."""

    pass


# Role definitions with permissions
ROLES = {
    "admin": {
        "permissions": [
            "manage_team",
            "manage_billing",
            "create_post",
            "edit_post",
            "delete_post",
            "view_analytics",
            "manage_platforms",
            "manage_api_keys",
            "view_audit_logs",
        ]
    },
    "manager": {
        "permissions": [
            "create_post",
            "edit_post",
            "delete_post",
            "view_analytics",
            "manage_platforms",
        ]
    },
    "viewer": {
        "permissions": [
            "view_analytics",
        ]
    },
}


def get_role_permissions(role_name: str) -> List[str]:
    """Get permissions for a role.

    Args:
        role_name: Name of the role

    Returns:
        List of permission strings

    Raises:
        RoleNotFoundError: If role does not exist
    """
    if role_name not in ROLES:
        raise RoleNotFoundError(f"Role '{role_name}' not found")
    return ROLES[role_name]["permissions"]


def check_permission(
    user_id: str, tenant_id: str, permission: str, db: Session
) -> bool:
    """Check if user has a specific permission in tenant.

    Args:
        user_id: User ID to check
        tenant_id: Tenant ID context
        permission: Permission string to check
        db: Database session

    Returns:
        True if user has permission, False otherwise
    """
    try:
        # Get user's role in tenant
        result = db.execute(
            text("""
                SELECT r.name, r.permissions
                FROM team_members tm
                JOIN roles r ON tm.role_id = r.id
                WHERE tm.user_id = :user_id 
                AND tm.tenant_id = :tenant_id
                AND tm.accepted_at IS NOT NULL
            """),
            {"user_id": user_id, "tenant_id": tenant_id},
        ).fetchone()

        if not result:
            logger.warning(f"User {user_id} not found in tenant {tenant_id}")
            return False

        role_name, permissions_json = result

        # Check if permission exists in role
        role_permissions = get_role_permissions(role_name)
        has_permission = permission in role_permissions

        logger.info(
            f"Permission check: user={user_id}, tenant={tenant_id}, "
            f"permission={permission}, result={has_permission}"
        )

        return has_permission

    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        return False


def get_user_role(user_id: str, tenant_id: str, db: Session) -> Optional[str]:
    """Get user's role in tenant.

    Args:
        user_id: User ID
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Role name or None if not found
    """
    try:
        result = db.execute(
            text("""
                SELECT r.name
                FROM team_members tm
                JOIN roles r ON tm.role_id = r.id
                WHERE tm.user_id = :user_id 
                AND tm.tenant_id = :tenant_id
                AND tm.accepted_at IS NOT NULL
            """),
            {"user_id": user_id, "tenant_id": tenant_id},
        ).fetchone()

        return result[0] if result else None

    except Exception as e:
        logger.error(f"Error getting user role: {e}")
        return None


def require_role(role_name: str) -> Callable:
    """Decorator to require specific role for endpoint access.

    Usage:
        @require_role("admin")
        async def admin_only_function(user_id: str, tenant_id: str, db: Session):
            pass

    Args:
        role_name: Required role name

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            user_id = kwargs.get("_user_id")
            tenant_id = kwargs.get("_tenant_id")
            db = kwargs.get("_db_session")

            if not all([user_id, tenant_id, db]):
                raise PermissionDeniedError("Missing authentication context")

            user_role = get_user_role(user_id, tenant_id, db)

            if not user_role:
                raise PermissionDeniedError("User not member of tenant")

            # Check if user has required role or higher
            role_hierarchy = ["viewer", "manager", "admin"]
            required_level = role_hierarchy.index(role_name)
            user_level = role_hierarchy.index(user_role)

            if user_level < required_level:
                raise PermissionDeniedError(
                    f"Requires {role_name} role, user has {user_role}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_permission(permission: str) -> Callable:
    """Decorator to require specific permission for endpoint access.

    Usage:
        @require_permission("create_post")
        async def create_post_function(user_id: str, tenant_id: str, db: Session):
            pass

    Args:
        permission: Required permission string

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            user_id = kwargs.get("_user_id")
            tenant_id = kwargs.get("_tenant_id")
            db = kwargs.get("_db_session")

            if not all([user_id, tenant_id, db]):
                raise PermissionDeniedError("Missing authentication context")

            if not check_permission(user_id, tenant_id, permission, db):
                raise PermissionDeniedError(
                    f"User lacks required permission: {permission}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def invite_team_member(
    tenant_id: str,
    email: str,
    role_name: str,
    invited_by: str,
    db: Session,
    expires_hours: int = 72,
) -> Dict[str, Any]:
    """Invite a team member to tenant.

    Args:
        tenant_id: Tenant ID
        email: Email address to invite
        role_name: Role to assign (admin, manager, viewer)
        invited_by: User ID of inviter
        db: Database session
        expires_hours: Hours until invite expires (default 72)

    Returns:
        Dict with invite details (token, expires_at)

    Raises:
        InviteError: If invite creation fails
        RoleNotFoundError: If role does not exist
    """
    try:
        # Validate role exists
        if role_name not in ROLES:
            raise RoleNotFoundError(f"Role '{role_name}' not found")

        # Get role ID
        result = db.execute(
            text("SELECT id FROM roles WHERE name = :role_name"),
            {"role_name": role_name},
        ).fetchone()

        if not result:
            raise RoleNotFoundError(f"Role '{role_name}' not in database")

        role_id = result[0]

        # Generate secure token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

        # Check for existing pending invite
        existing = db.execute(
            text("""
                SELECT id FROM team_invites
                WHERE tenant_id = :tenant_id
                AND email = :email
                AND accepted = FALSE
                AND expires_at > NOW()
            """),
            {"tenant_id": tenant_id, "email": email},
        ).fetchone()

        if existing:
            # Revoke existing invite
            db.execute(
                text("""
                    UPDATE team_invites
                    SET accepted = TRUE
                    WHERE id = :invite_id
                """),
                {"invite_id": existing[0]},
            )

        # Create invite
        db.execute(
            text("""
                INSERT INTO team_invites 
                (tenant_id, email, role_id, token, expires_at, invited_by, accepted)
                VALUES (:tenant_id, :email, :role_id, :token, :expires_at, :invited_by, FALSE)
            """),
            {
                "tenant_id": tenant_id,
                "email": email,
                "role_id": role_id,
                "token": token,
                "expires_at": expires_at,
                "invited_by": invited_by,
            },
        )

        db.commit()

        logger.info(
            f"Created team invite: tenant={tenant_id}, email={email}, "
            f"role={role_name}, invited_by={invited_by}"
        )

        # In production, send email here
        invite_url = f"{os.getenv('APP_URL', 'http://localhost:8000')}/accept-invite?token={token}"

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "invite_url": invite_url,
            "email": email,
            "role": role_name,
        }

    except (RoleNotFoundError, InviteError):
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating team invite: {e}")
        raise InviteError(f"Failed to create invite: {e}")


def accept_invitation(token: str, user_id: str, db: Session) -> Dict[str, Any]:
    """Accept a team invitation.

    Args:
        token: Invitation token
        user_id: User ID accepting invite
        db: Database session

    Returns:
        Dict with tenant_id and role

    Raises:
        InviteError: If invite is invalid or expired
    """
    try:
        # Find invite
        result = db.execute(
            text("""
                SELECT id, tenant_id, email, role_id, expires_at, accepted
                FROM team_invites
                WHERE token = :token
            """),
            {"token": token},
        ).fetchone()

        if not result:
            raise InviteError("Invalid invitation token")

        invite_id, tenant_id, email, role_id, expires_at, accepted = result

        if accepted:
            raise InviteError("Invitation already accepted")

        expires_at_aware = (
            expires_at.replace(tzinfo=timezone.utc)
            if expires_at.tzinfo is None
            else expires_at
        )
        if expires_at_aware < datetime.now(timezone.utc):
            raise InviteError("Invitation expired")

        # Get role name
        role_result = db.execute(
            text("SELECT name FROM roles WHERE id = :role_id"),
            {"role_id": role_id},
        ).fetchone()

        role_name = role_result[0] if role_result else "viewer"

        # Check if user already member
        existing = db.execute(
            text("""
                SELECT id FROM team_members
                WHERE tenant_id = :tenant_id
                AND user_id = :user_id
            """),
            {"tenant_id": tenant_id, "user_id": user_id},
        ).fetchone()

        if existing:
            # Update existing membership
            db.execute(
                text("""
                    UPDATE team_members
                    SET role_id = :role_id, accepted_at = NOW()
                    WHERE id = :member_id
                """),
                {"role_id": role_id, "member_id": existing[0]},
            )
        else:
            # Create team membership
            db.execute(
                text("""
                    INSERT INTO team_members
                    (tenant_id, user_id, role_id, invited_by, accepted_at)
                    SELECT :tenant_id, :user_id, :role_id, invited_by, NOW()
                    FROM team_invites
                    WHERE id = :invite_id
                """),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "role_id": role_id,
                    "invite_id": invite_id,
                },
            )

        # Mark invite as accepted
        db.execute(
            text("""
                UPDATE team_invites
                SET accepted = TRUE
                WHERE id = :invite_id
            """),
            {"invite_id": invite_id},
        )

        db.commit()

        logger.info(
            f"Accepted team invite: user={user_id}, tenant={tenant_id}, role={role_name}"
        )

        return {
            "tenant_id": tenant_id,
            "role": role_name,
            "email": email,
        }

    except InviteError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error accepting invitation: {e}")
        raise InviteError(f"Failed to accept invitation: {e}")


def remove_team_member(
    tenant_id: str, user_id: str, removed_by: str, db: Session
) -> None:
    """Remove a team member from tenant.

    Args:
        tenant_id: Tenant ID
        user_id: User ID to remove
        removed_by: User ID performing removal
        db: Database session

    Raises:
        PermissionDeniedError: If trying to remove last admin
    """
    try:
        # Check if user is last admin
        admin_count = db.execute(
            text("""
                SELECT COUNT(*)
                FROM team_members tm
                JOIN roles r ON tm.role_id = r.id
                WHERE tm.tenant_id = :tenant_id
                AND r.name = 'admin'
                AND tm.accepted_at IS NOT NULL
            """),
            {"tenant_id": tenant_id},
        ).scalar()

        user_role = get_user_role(user_id, tenant_id, db)

        if user_role == "admin" and admin_count <= 1:
            raise PermissionDeniedError("Cannot remove last admin from tenant")

        # Remove team member
        db.execute(
            text("""
                DELETE FROM team_members
                WHERE tenant_id = :tenant_id
                AND user_id = :user_id
            """),
            {"tenant_id": tenant_id, "user_id": user_id},
        )

        db.commit()

        logger.info(
            f"Removed team member: tenant={tenant_id}, user={user_id}, "
            f"removed_by={removed_by}"
        )

    except PermissionDeniedError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing team member: {e}")
        raise RBACError(f"Failed to remove team member: {e}")


def list_team_members(tenant_id: str, db: Session) -> List[Dict[str, Any]]:
    """List all team members in tenant.

    Args:
        tenant_id: Tenant ID
        db: Database session

    Returns:
        List of team member dicts
    """
    try:
        results = db.execute(
            text("""
                SELECT 
                    tm.user_id,
                    tm.accepted_at,
                    r.name as role,
                    tm.invited_by
                FROM team_members tm
                JOIN roles r ON tm.role_id = r.id
                WHERE tm.tenant_id = :tenant_id
                AND tm.accepted_at IS NOT NULL
                ORDER BY tm.accepted_at ASC
            """),
            {"tenant_id": tenant_id},
        ).fetchall()

        return [
            {
                "user_id": row[0],
                "joined_at": row[1].isoformat() if row[1] else None,
                "role": row[2],
                "invited_by": row[3],
            }
            for row in results
        ]

    except Exception as e:
        logger.error(f"Error listing team members: {e}")
        return []
