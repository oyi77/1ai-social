"""
LemonSqueezy payment provider integration with webhook handling.

This module provides:
- Webhook signature verification using HMAC-SHA256
- Subscription event processing (created, updated, cancelled, payment events)
- Database storage of subscription data
- Idempotency handling to prevent duplicate processing

Supported Events:
- subscription_created: New subscription created
- subscription_updated: Subscription details changed
- subscription_cancelled: Subscription cancelled
- subscription_payment_success: Payment succeeded
- subscription_payment_failed: Payment failed

Environment Variables:
- LEMONSQUEEZY_WEBHOOK_SECRET: Webhook signing secret
- LEMONSQUEEZY_API_KEY: API key for LemonSqueezy API (optional)
"""

import hashlib
import hmac
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base

logger = logging.getLogger(__name__)

Base = declarative_base()


class Subscription(Base):
    """Subscription model for storing LemonSqueezy subscription data."""

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False)
    lemonsqueezy_subscription_id = Column(String(255), unique=True, nullable=False)
    lemonsqueezy_customer_id = Column(String(255), nullable=True)
    plan = Column(String(50), nullable=False)  # starter/pro/enterprise
    status = Column(String(50), nullable=False)  # active/cancelled/past_due
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class LemonSqueezyWebhookVerifier:
    """
    Verifies LemonSqueezy webhook signatures using HMAC-SHA256.

    LemonSqueezy sends webhooks with X-Signature header containing
    HMAC-SHA256 hash of the raw request body.
    """

    def __init__(self, secret: str):
        """
        Initialize webhook verifier.

        Args:
            secret: Webhook signing secret from LemonSqueezy
        """
        self.secret = secret.encode("utf-8")

    def verify_signature(self, signature: str, body: bytes) -> bool:
        """
        Verify webhook signature using timing-safe comparison.

        Args:
            signature: Signature from X-Signature header
            body: Raw request body bytes

        Returns:
            True if signature is valid, False otherwise
        """
        if not signature:
            logger.warning("Missing X-Signature header")
            return False

        # Compute expected signature
        expected_signature = hmac.new(self.secret, body, hashlib.sha256).hexdigest()

        # Timing-safe comparison
        return hmac.compare_digest(signature, expected_signature)


class LemonSqueezyWebhookHandler:
    """
    Handles LemonSqueezy webhook events and updates subscription data.
    """

    def __init__(self, db_session: Session, redis_client=None):
        """
        Initialize webhook handler.

        Args:
            db_session: SQLAlchemy database session
            redis_client: Redis client for idempotency (optional)
        """
        self.db = db_session
        self.redis = redis_client

    def check_idempotency(self, webhook_id: str) -> bool:
        """
        Check if webhook has already been processed.

        Args:
            webhook_id: Unique webhook ID from meta.webhook_id

        Returns:
            True if webhook is new, False if already processed
        """
        if not self.redis:
            logger.warning("Redis not configured - idempotency check skipped")
            return True

        redis_key = f"lemonsqueezy:webhook:{webhook_id}"

        if self.redis.exists(redis_key):
            logger.warning(f"Duplicate webhook: {webhook_id}")
            return False

        # Store webhook ID with 24-hour TTL
        self.redis.setex(redis_key, 86400, "1")
        return True

    def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """
        Process webhook event and update database.

        Args:
            payload: Webhook payload from LemonSqueezy

        Returns:
            Dict with status and message
        """
        try:
            # Extract event metadata
            meta = payload.get("meta", {})
            event_name = meta.get("event_name")
            webhook_id = meta.get("webhook_id")

            if not event_name:
                return {"status": "error", "message": "Missing event_name"}

            # Check idempotency
            if webhook_id and not self.check_idempotency(webhook_id):
                return {"status": "skipped", "message": "Duplicate webhook"}

            # Route to appropriate handler
            if event_name == "subscription_created":
                return self._handle_subscription_created(payload)
            elif event_name == "subscription_updated":
                return self._handle_subscription_updated(payload)
            elif event_name == "subscription_cancelled":
                return self._handle_subscription_cancelled(payload)
            elif event_name == "subscription_payment_success":
                return self._handle_payment_success(payload)
            elif event_name == "subscription_payment_failed":
                return self._handle_payment_failed(payload)
            else:
                logger.info(f"Unhandled event type: {event_name}")
                return {
                    "status": "ignored",
                    "message": f"Event type not handled: {event_name}",
                }

        except Exception as e:
            logger.error(f"Webhook processing failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def _handle_subscription_created(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription_created event."""
        data = payload.get("data", {})
        attributes = data.get("attributes", {})

        subscription_id = data.get("id")
        customer_id = attributes.get("customer_id")
        status = attributes.get("status")
        variant_id = attributes.get("variant_id")

        # Parse timestamps
        renews_at = attributes.get("renews_at")
        created_at = attributes.get("created_at")

        # Map variant to plan (this should be configured based on your LemonSqueezy setup)
        plan = self._map_variant_to_plan(variant_id)

        # Create subscription record
        subscription = Subscription(
            tenant_id=self._get_tenant_id_from_customer(customer_id),
            lemonsqueezy_subscription_id=subscription_id,
            lemonsqueezy_customer_id=customer_id,
            plan=plan,
            status=status,
            current_period_end=self._parse_timestamp(renews_at),
            cancel_at_period_end=False,
        )

        self.db.add(subscription)
        self.db.commit()

        logger.info(f"Subscription created: {subscription_id}")
        return {"status": "success", "message": "Subscription created"}

    def _handle_subscription_updated(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription_updated event."""
        data = payload.get("data", {})
        attributes = data.get("attributes", {})

        subscription_id = data.get("id")
        status = attributes.get("status")
        renews_at = attributes.get("renews_at")
        ends_at = attributes.get("ends_at")

        # Find existing subscription
        subscription = (
            self.db.query(Subscription)
            .filter_by(lemonsqueezy_subscription_id=subscription_id)
            .first()
        )

        if not subscription:
            logger.warning(f"Subscription not found: {subscription_id}")
            return {"status": "error", "message": "Subscription not found"}

        # Update subscription
        subscription.status = status
        subscription.current_period_end = self._parse_timestamp(renews_at or ends_at)
        subscription.cancel_at_period_end = bool(ends_at and not renews_at)
        subscription.updated_at = datetime.utcnow()

        self.db.commit()

        logger.info(f"Subscription updated: {subscription_id}")
        return {"status": "success", "message": "Subscription updated"}

    def _handle_subscription_cancelled(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription_cancelled event."""
        data = payload.get("data", {})
        subscription_id = data.get("id")

        # Find existing subscription
        subscription = (
            self.db.query(Subscription)
            .filter_by(lemonsqueezy_subscription_id=subscription_id)
            .first()
        )

        if not subscription:
            logger.warning(f"Subscription not found: {subscription_id}")
            return {"status": "error", "message": "Subscription not found"}

        # Update subscription status
        subscription.status = "cancelled"
        subscription.updated_at = datetime.utcnow()

        self.db.commit()

        logger.info(f"Subscription cancelled: {subscription_id}")
        return {"status": "success", "message": "Subscription cancelled"}

    def _handle_payment_success(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription_payment_success event."""
        data = payload.get("data", {})
        attributes = data.get("attributes", {})
        subscription_id = attributes.get("subscription_id")

        if not subscription_id:
            return {"status": "ignored", "message": "No subscription_id in payment"}

        # Find subscription and update status
        subscription = (
            self.db.query(Subscription)
            .filter_by(lemonsqueezy_subscription_id=str(subscription_id))
            .first()
        )

        if subscription:
            subscription.status = "active"
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Payment success for subscription: {subscription_id}")

        return {"status": "success", "message": "Payment recorded"}

    def _handle_payment_failed(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription_payment_failed event."""
        data = payload.get("data", {})
        attributes = data.get("attributes", {})
        subscription_id = attributes.get("subscription_id")

        if not subscription_id:
            return {"status": "ignored", "message": "No subscription_id in payment"}

        # Find subscription and update status
        subscription = (
            self.db.query(Subscription)
            .filter_by(lemonsqueezy_subscription_id=str(subscription_id))
            .first()
        )

        if subscription:
            subscription.status = "past_due"
            subscription.updated_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Payment failed for subscription: {subscription_id}")

        return {"status": "success", "message": "Payment failure recorded"}

    def _map_variant_to_plan(self, variant_id: str) -> str:
        """
        Map LemonSqueezy variant ID to plan name.

        TODO: Configure this mapping based on your LemonSqueezy product setup.
        """
        # Default mapping - should be configured via environment variables
        variant_map = {
            os.getenv("LEMONSQUEEZY_VARIANT_STARTER"): "starter",
            os.getenv("LEMONSQUEEZY_VARIANT_PRO"): "pro",
            os.getenv("LEMONSQUEEZY_VARIANT_ENTERPRISE"): "enterprise",
        }
        return variant_map.get(variant_id, "starter")

    def _get_tenant_id_from_customer(self, customer_id: str) -> str:
        """
        Get tenant_id from customer_id.

        TODO: Implement customer-to-tenant mapping.
        For now, use customer_id as tenant_id.
        """
        # This should query your customer/tenant mapping
        return customer_id

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 timestamp string to datetime."""
        if not timestamp_str:
            return None

        try:
            # Handle ISO 8601 format: 2026-05-16T00:00:00Z
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return None


def get_webhook_secret() -> str:
    """
    Get LemonSqueezy webhook secret from environment.

    Returns:
        Webhook secret

    Raises:
        ValueError: If secret not configured
    """
    secret = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")
    if not secret:
        raise ValueError("LEMONSQUEEZY_WEBHOOK_SECRET not configured")
    return secret
