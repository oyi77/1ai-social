"""Email notification module for 1ai-social."""

from .email import (
    send_email,
    EmailProvider,
    EmailQueue,
    generate_unsubscribe_link,
    EMAIL_TEMPLATES,
)

__all__ = [
    "send_email",
    "EmailProvider",
    "EmailQueue",
    "generate_unsubscribe_link",
    "EMAIL_TEMPLATES",
]
