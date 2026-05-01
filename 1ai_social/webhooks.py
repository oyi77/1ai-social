"""
Webhook signature verification with HMAC-SHA256 and replay protection.

This module provides secure webhook verification with:
- HMAC-SHA256 signature verification
- Timing-safe signature comparison
- Timestamp validation (reject if >5 minutes old)
- Idempotency handling (deduplicate webhook IDs)
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

logger = logging.getLogger(__name__)


class WebhookVerificationError(Exception):
    """Base exception for webhook verification failures."""

    pass


class InvalidSignatureError(WebhookVerificationError):
    """Raised when webhook signature is invalid."""

    pass


class ReplayAttackError(WebhookVerificationError):
    """Raised when webhook timestamp is too old."""

    pass


class DuplicateWebhookError(WebhookVerificationError):
    """Raised when webhook ID has already been processed."""

    pass


class WebhookVerifier:
    """
    Verifies webhook signatures and prevents replay attacks.

    Webhook Format:
        POST /webhooks/:provider
        Headers:
            X-Webhook-Signature: sha256=<hmac>
            X-Webhook-Timestamp: 1234567890
            X-Webhook-ID: unique-id
        Body: JSON payload
    """

    def __init__(
        self,
        secret: str,
        max_timestamp_age: int = 300,  # 5 minutes
        redis_client=None,
        redis_ttl: int = 3600,  # 1 hour
    ):
        """
        Initialize webhook verifier.

        Args:
            secret: Webhook signing secret
            max_timestamp_age: Maximum age of timestamp in seconds (default: 300)
            redis_client: Redis client for idempotency (optional)
            redis_ttl: TTL for webhook IDs in Redis (default: 3600)
        """
        self.secret = secret.encode("utf-8")
        self.max_timestamp_age = max_timestamp_age
        self.redis_client = redis_client
        self.redis_ttl = redis_ttl

    def compute_signature(self, timestamp: str, body: bytes) -> str:
        """
        Compute HMAC-SHA256 signature for webhook payload.

        Args:
            timestamp: Unix timestamp as string
            body: Raw request body bytes

        Returns:
            Signature in format: sha256=<hex_digest>
        """
        # Construct signed payload: timestamp + body
        signed_payload = f"{timestamp}.".encode("utf-8") + body

        # Compute HMAC-SHA256
        signature = hmac.new(self.secret, signed_payload, hashlib.sha256).hexdigest()

        return f"sha256={signature}"

    def verify_signature(self, signature: str, timestamp: str, body: bytes) -> None:
        """
        Verify webhook signature using timing-safe comparison.

        Args:
            signature: Signature from X-Webhook-Signature header
            timestamp: Timestamp from X-Webhook-Timestamp header
            body: Raw request body bytes

        Raises:
            InvalidSignatureError: If signature is invalid
        """
        if not signature:
            raise InvalidSignatureError("Missing signature")

        if not signature.startswith("sha256="):
            raise InvalidSignatureError("Invalid signature format")

        # Compute expected signature
        expected_signature = self.compute_signature(timestamp, body)

        # Timing-safe comparison to prevent timing attacks
        if not secrets.compare_digest(signature, expected_signature):
            logger.warning("Invalid webhook signature")
            raise InvalidSignatureError("Invalid signature")

    def verify_timestamp(self, timestamp: str) -> None:
        """
        Verify webhook timestamp is recent to prevent replay attacks.

        Args:
            timestamp: Unix timestamp as string

        Raises:
            ReplayAttackError: If timestamp is too old
        """
        if not timestamp:
            raise ReplayAttackError("Missing timestamp")

        try:
            webhook_time = int(timestamp)
        except ValueError:
            raise ReplayAttackError("Invalid timestamp format")

        current_time = int(time.time())
        age = current_time - webhook_time

        if age > self.max_timestamp_age:
            logger.warning(f"Webhook timestamp too old: {age}s")
            raise ReplayAttackError(
                f"Timestamp too old: {age}s (max: {self.max_timestamp_age}s)"
            )

        if age < -60:  # Allow 1 minute clock skew
            logger.warning(f"Webhook timestamp in future: {age}s")
            raise ReplayAttackError("Timestamp in future")

    def verify_idempotency(self, webhook_id: str) -> None:
        """
        Verify webhook has not been processed before (idempotency).

        Args:
            webhook_id: Unique webhook ID from X-Webhook-ID header

        Raises:
            DuplicateWebhookError: If webhook ID already processed
        """
        if not webhook_id:
            raise DuplicateWebhookError("Missing webhook ID")

        if not self.redis_client:
            logger.warning("Redis not configured - idempotency check skipped")
            return

        # Check if webhook ID exists in Redis
        redis_key = f"webhook:processed:{webhook_id}"

        if self.redis_client.exists(redis_key):
            logger.warning(f"Duplicate webhook ID: {webhook_id}")
            raise DuplicateWebhookError(f"Webhook already processed: {webhook_id}")

        # Store webhook ID in Redis with TTL
        self.redis_client.setex(redis_key, self.redis_ttl, "1")

    def verify_webhook(
        self, signature: str, timestamp: str, webhook_id: str, body: bytes
    ) -> None:
        """
        Verify webhook signature, timestamp, and idempotency.

        This is the main verification method that performs all checks.

        Args:
            signature: Signature from X-Webhook-Signature header
            timestamp: Timestamp from X-Webhook-Timestamp header
            webhook_id: Webhook ID from X-Webhook-ID header
            body: Raw request body bytes

        Raises:
            WebhookVerificationError: If any verification check fails
        """
        # Step 1: Verify signature
        self.verify_signature(signature, timestamp, body)

        # Step 2: Verify timestamp (replay protection)
        self.verify_timestamp(timestamp)

        # Step 3: Verify idempotency (deduplication)
        self.verify_idempotency(webhook_id)

        logger.info(f"Webhook verified successfully: {webhook_id}")


def get_webhook_secret(provider: str) -> Optional[str]:
    """
    Get webhook secret for a specific provider from environment.

    Args:
        provider: Provider name (e.g., 'stripe', 'github', 'twitter')

    Returns:
        Webhook secret or None if not configured
    """
    env_var = f"WEBHOOK_SECRET_{provider.upper()}"
    return os.getenv(env_var)


def create_verifier(provider: str, redis_client=None) -> WebhookVerifier:
    """
    Create webhook verifier for a specific provider.

    Args:
        provider: Provider name
        redis_client: Redis client for idempotency (optional)

    Returns:
        WebhookVerifier instance

    Raises:
        ValueError: If webhook secret not configured
    """
    secret = get_webhook_secret(provider)
    if not secret:
        raise ValueError(f"Webhook secret not configured for provider: {provider}")

    return WebhookVerifier(secret=secret, redis_client=redis_client)
