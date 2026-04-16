"""Tenant context middleware for multi-tenancy support.

Extracts tenant_id from JWT tokens or API keys and sets PostgreSQL session
variables for Row-Level Security (RLS) enforcement.
"""

import logging
import os
from typing import Optional, Callable, Any
from functools import wraps
import jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TenantContextMiddleware:
    """Middleware to extract and validate tenant context from requests."""

    def __init__(self, db_session_factory: Callable[[], Session]):
        """Initialize tenant context middleware.

        Args:
            db_session_factory: Factory function to create database sessions
        """
        self.db_session_factory = db_session_factory
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        if not self.jwt_secret:
            logger.warning("JWT_SECRET_KEY not set - JWT validation disabled")

    def extract_tenant_from_jwt(self, token: str) -> Optional[str]:
        """Extract tenant_id from JWT token.

        Args:
            token: JWT token string

        Returns:
            tenant_id if valid, None otherwise
        """
        if not self.jwt_secret:
            logger.error("Cannot validate JWT - JWT_SECRET_KEY not configured")
            return None

        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
            tenant_id = payload.get("tenant_id")

            if not tenant_id:
                logger.warning("JWT token missing tenant_id claim")
                return None

            logger.info(f"Extracted tenant_id from JWT: {tenant_id}")
            return tenant_id

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    def extract_tenant_from_api_key(self, api_key: str, db: Session) -> Optional[str]:
        """Extract tenant_id from API key by looking up in database.

        Args:
            api_key: API key string
            db: Database session

        Returns:
            tenant_id if valid, None otherwise
        """
        try:
            # Query api_keys table for tenant_id
            # Assuming api_keys table structure: (key, tenant_id, is_active)
            result = db.execute(
                text("""
                    SELECT tenant_id, is_active 
                    FROM api_keys 
                    WHERE key = :api_key
                """),
                {"api_key": api_key},
            ).fetchone()

            if not result:
                logger.warning("API key not found")
                return None

            tenant_id, is_active = result

            if not is_active:
                logger.warning(f"API key inactive for tenant: {tenant_id}")
                return None

            logger.info(f"Extracted tenant_id from API key: {tenant_id}")
            return tenant_id

        except Exception as e:
            logger.error(f"Error looking up API key: {e}")
            return None

    def validate_tenant(self, tenant_id: str, db: Session) -> bool:
        """Validate that tenant exists and is active.

        Args:
            tenant_id: Tenant ID to validate
            db: Database session

        Returns:
            True if tenant is valid and active, False otherwise
        """
        try:
            result = db.execute(
                text("""
                    SELECT status 
                    FROM tenants 
                    WHERE id = :tenant_id
                """),
                {"tenant_id": tenant_id},
            ).fetchone()

            if not result:
                logger.warning(f"Tenant not found: {tenant_id}")
                return False

            status = result[0]

            if status != "active":
                logger.warning(f"Tenant not active: {tenant_id} (status: {status})")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating tenant: {e}")
            return False

    def set_tenant_context(
        self, tenant_id: str, db: Session, user_role: str = "user"
    ) -> None:
        """Set PostgreSQL session variables for RLS.

        Args:
            tenant_id: Tenant ID to set in session
            db: Database session
            user_role: User role (user or admin)
        """
        try:
            # Set tenant context
            db.execute(
                text("SET app.current_tenant_id = :tenant_id"), {"tenant_id": tenant_id}
            )

            # Set user role
            db.execute(text("SET app.user_role = :user_role"), {"user_role": user_role})

            db.commit()
            logger.info(f"Set tenant context: tenant_id={tenant_id}, role={user_role}")

        except Exception as e:
            logger.error(f"Error setting tenant context: {e}")
            db.rollback()
            raise

    def extract_tenant_id(
        self, auth_header: Optional[str], api_key_header: Optional[str], db: Session
    ) -> Optional[str]:
        """Extract tenant_id from request headers.

        Args:
            auth_header: Authorization header value (Bearer token)
            api_key_header: X-API-Key header value
            db: Database session

        Returns:
            tenant_id if found and valid, None otherwise
        """
        # Try JWT token first
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            tenant_id = self.extract_tenant_from_jwt(token)
            if tenant_id:
                return tenant_id

        # Try API key
        if api_key_header:
            tenant_id = self.extract_tenant_from_api_key(api_key_header, db)
            if tenant_id:
                return tenant_id

        logger.warning("No valid tenant_id found in request headers")
        return None

    def middleware_decorator(self, func: Callable) -> Callable:
        """Decorator to apply tenant context to MCP tool functions.

        Args:
            func: Function to wrap with tenant context

        Returns:
            Wrapped function with tenant context
        """

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract headers from kwargs (FastMCP passes them)
            auth_header = kwargs.get("_auth_header")
            api_key_header = kwargs.get("_api_key_header")

            # Create database session
            db = self.db_session_factory()

            try:
                # Extract tenant_id
                tenant_id = self.extract_tenant_id(auth_header, api_key_header, db)

                if not tenant_id:
                    logger.error("Missing or invalid tenant context")
                    raise PermissionError("Invalid tenant credentials")

                # Validate tenant
                if not self.validate_tenant(tenant_id, db):
                    logger.error(f"Invalid tenant: {tenant_id}")
                    raise PermissionError("Invalid tenant")

                # Set tenant context for RLS
                self.set_tenant_context(tenant_id, db)

                # Add tenant_id to kwargs for function use
                kwargs["_tenant_id"] = tenant_id
                kwargs["_db_session"] = db

                # Call original function
                result = await func(*args, **kwargs)

                return result

            except PermissionError:
                raise
            except Exception as e:
                logger.error(f"Error in tenant context middleware: {e}")
                raise
            finally:
                db.close()

        return wrapper


# Global middleware instance
_middleware_instance: Optional[TenantContextMiddleware] = None


def get_tenant_middleware(
    db_session_factory: Callable[[], Session],
) -> TenantContextMiddleware:
    """Get or create the global tenant context middleware instance.

    Args:
        db_session_factory: Factory function to create database sessions

    Returns:
        TenantContextMiddleware instance
    """
    global _middleware_instance
    if _middleware_instance is None:
        _middleware_instance = TenantContextMiddleware(db_session_factory)
    return _middleware_instance


def require_tenant_context(db_session_factory: Callable[[], Session]) -> Callable:
    """Decorator factory for requiring tenant context on MCP tools.

    Usage:
        @mcp.tool()
        @require_tenant_context(get_db_session)
        async def my_tool(param: str, _tenant_id: str = None, _db_session: Session = None):
            # _tenant_id and _db_session are injected by middleware
            pass

    Args:
        db_session_factory: Factory function to create database sessions

    Returns:
        Decorator function
    """
    middleware = get_tenant_middleware(db_session_factory)
    return middleware.middleware_decorator
