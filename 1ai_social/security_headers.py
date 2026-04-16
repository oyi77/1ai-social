"""Security headers middleware for defense in depth."""

import os
import logging
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Middleware to add comprehensive security headers to all responses."""

    def __init__(self, allowed_origins: str | None = None):
        """Initialize security headers middleware.

        Args:
            allowed_origins: Comma-separated list of allowed origins for CORS.
                           Defaults to http://localhost:3000 for development.
        """
        self.allowed_origins = (
            allowed_origins or os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
        ).split(",")
        self.allowed_origins = [origin.strip() for origin in self.allowed_origins]
        logger.info(
            f"Security headers initialized with origins: {self.allowed_origins}"
        )

    def get_headers(self, origin: str | None = None) -> dict[str, str]:
        """Get security headers for a response.

        Args:
            origin: The request origin to validate for CORS.

        Returns:
            Dictionary of security headers.
        """
        headers = {
            # Prevent clickjacking attacks
            "X-Frame-Options": "DENY",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Enable XSS protection in older browsers
            "X-XSS-Protection": "1; mode=block",
            # Force HTTPS for 1 year including subdomains
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            # Content Security Policy - restrict to same origin
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            # Referrer policy for privacy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy (formerly Feature-Policy)
            "Permissions-Policy": "geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()",
        }

        # Add CORS headers if origin is allowed
        if origin and origin in self.allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-CSRF-Token"
            )
            headers["Access-Control-Max-Age"] = "3600"
            headers["Access-Control-Allow-Credentials"] = "true"

        return headers

    def apply_to_response(
        self, response: dict[str, Any], origin: str | None = None
    ) -> dict[str, Any]:
        """Apply security headers to a response dictionary.

        Args:
            response: Response dictionary to modify.
            origin: The request origin for CORS validation.

        Returns:
            Response with security headers added.
        """
        if "headers" not in response:
            response["headers"] = {}

        headers = self.get_headers(origin)
        response["headers"].update(headers)
        return response

    def middleware_decorator(self, func: Callable) -> Callable:
        """Decorator to apply security headers to a function's response.

        Args:
            func: The function to wrap.

        Returns:
            Wrapped function that adds security headers.
        """

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)

            # Extract origin from kwargs if available (for HTTP context)
            origin = kwargs.get("origin")

            # If result is a dict, apply headers
            if isinstance(result, dict):
                result = self.apply_to_response(result, origin)

            return result

        return wrapper


def create_security_headers_middleware(
    allowed_origins: str | None = None,
) -> SecurityHeadersMiddleware:
    """Factory function to create security headers middleware.

    Args:
        allowed_origins: Comma-separated list of allowed origins.

    Returns:
        SecurityHeadersMiddleware instance.
    """
    return SecurityHeadersMiddleware(allowed_origins)


# Global middleware instance
_middleware_instance: SecurityHeadersMiddleware | None = None


def get_security_middleware() -> SecurityHeadersMiddleware:
    """Get or create the global security headers middleware instance."""
    global _middleware_instance
    if _middleware_instance is None:
        _middleware_instance = create_security_headers_middleware()
    return _middleware_instance


def apply_security_headers(func: Callable) -> Callable:
    """Convenience decorator to apply security headers to any function."""
    middleware = get_security_middleware()
    return middleware.middleware_decorator(func)
