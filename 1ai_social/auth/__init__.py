"""Authentication module for 1ai-social."""

from .oauth import (
    get_oauth_url,
    handle_callback,
    link_account,
    unlink_account,
    OAuthProvider,
    OAuthError,
)

__all__ = [
    "get_oauth_url",
    "handle_callback",
    "link_account",
    "unlink_account",
    "OAuthProvider",
    "OAuthError",
]
