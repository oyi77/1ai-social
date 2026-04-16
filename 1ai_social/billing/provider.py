"""
Abstract billing provider interface with LemonSqueezy and Stripe implementations.

This module provides a pluggable billing provider system that allows switching
between different payment processors (LemonSqueezy, Stripe, etc.) via environment
configuration.

Supported Providers:
- lemonsqueezy: LemonSqueezy payment processor (default)
- stripe: Stripe payment processor (stub for future implementation)

Environment Variables:
- BILLING_PROVIDER: Provider to use ('lemonsqueezy' or 'stripe', default: 'lemonsqueezy')
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class BillingProvider(ABC):
    """Abstract base class for billing providers."""

    @abstractmethod
    def create_subscription(
        self, tenant_id: str, plan: str, customer_email: str
    ) -> Dict[str, Any]:
        """
        Create a new subscription for a tenant.

        Args:
            tenant_id: Unique tenant identifier
            plan: Plan name (starter, pro, enterprise)
            customer_email: Customer email address

        Returns:
            Dict with subscription details including provider-specific ID
        """
        pass

    @abstractmethod
    def cancel_subscription(self, tenant_id: str) -> Dict[str, Any]:
        """
        Cancel an active subscription.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            Dict with cancellation status
        """
        pass

    @abstractmethod
    def update_subscription(self, tenant_id: str, new_plan: str) -> Dict[str, Any]:
        """
        Update subscription to a different plan.

        Args:
            tenant_id: Unique tenant identifier
            new_plan: New plan name (starter, pro, enterprise)

        Returns:
            Dict with updated subscription details
        """
        pass

    @abstractmethod
    def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve subscription details for a tenant.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            Dict with subscription details or None if not found
        """
        pass

    @abstractmethod
    def verify_webhook_signature(self, signature: str, body: bytes) -> bool:
        """
        Verify webhook signature from provider.

        Args:
            signature: Signature from webhook header
            body: Raw webhook body bytes

        Returns:
            True if signature is valid, False otherwise
        """
        pass


class LemonSqueezyProvider(BillingProvider):
    """LemonSqueezy billing provider implementation."""

    def __init__(self):
        """Initialize LemonSqueezy provider."""
        self.verifier = None
        secret = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET")
        if secret:
            try:
                from .lemonsqueezy import LemonSqueezyWebhookVerifier

                self.verifier = LemonSqueezyWebhookVerifier(secret)
            except ImportError:
                logger.warning("Could not import LemonSqueezyWebhookVerifier")

    def create_subscription(
        self, tenant_id: str, plan: str, customer_email: str
    ) -> Dict[str, Any]:
        """
        Create subscription via LemonSqueezy.

        Note: This is a placeholder. Actual implementation would call
        LemonSqueezy API to create a subscription.
        """
        logger.info(
            f"LemonSqueezy: Creating subscription for tenant {tenant_id}, plan {plan}"
        )
        return {
            "status": "pending",
            "provider": "lemonsqueezy",
            "tenant_id": tenant_id,
            "plan": plan,
        }

    def cancel_subscription(self, tenant_id: str) -> Dict[str, Any]:
        """Cancel subscription via LemonSqueezy."""
        logger.info(f"LemonSqueezy: Cancelling subscription for tenant {tenant_id}")
        return {
            "status": "cancelled",
            "provider": "lemonsqueezy",
            "tenant_id": tenant_id,
        }

    def update_subscription(self, tenant_id: str, new_plan: str) -> Dict[str, Any]:
        """Update subscription plan via LemonSqueezy."""
        logger.info(
            f"LemonSqueezy: Updating subscription for tenant {tenant_id} to plan {new_plan}"
        )
        return {
            "status": "updated",
            "provider": "lemonsqueezy",
            "tenant_id": tenant_id,
            "plan": new_plan,
        }

    def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve subscription details from LemonSqueezy."""
        logger.info(f"LemonSqueezy: Retrieving subscription for tenant {tenant_id}")
        return None

    def verify_webhook_signature(self, signature: str, body: bytes) -> bool:
        """Verify LemonSqueezy webhook signature."""
        if not self.verifier:
            logger.warning("LemonSqueezy webhook verifier not configured")
            return False
        return self.verifier.verify_signature(signature, body)


class StripeProvider(BillingProvider):
    """Stripe billing provider implementation (stub for future use)."""

    def __init__(self):
        """Initialize Stripe provider."""
        self.api_key = os.getenv("STRIPE_API_KEY")
        if not self.api_key:
            logger.warning("STRIPE_API_KEY not configured")

    def create_subscription(
        self, tenant_id: str, plan: str, customer_email: str
    ) -> Dict[str, Any]:
        """
        Create subscription via Stripe.

        TODO: Implement Stripe API integration
        """
        logger.info(
            f"Stripe: Creating subscription for tenant {tenant_id}, plan {plan}"
        )
        return {
            "status": "pending",
            "provider": "stripe",
            "tenant_id": tenant_id,
            "plan": plan,
            "message": "Stripe integration not yet implemented",
        }

    def cancel_subscription(self, tenant_id: str) -> Dict[str, Any]:
        """Cancel subscription via Stripe."""
        logger.info(f"Stripe: Cancelling subscription for tenant {tenant_id}")
        return {
            "status": "cancelled",
            "provider": "stripe",
            "tenant_id": tenant_id,
            "message": "Stripe integration not yet implemented",
        }

    def update_subscription(self, tenant_id: str, new_plan: str) -> Dict[str, Any]:
        """Update subscription plan via Stripe."""
        logger.info(
            f"Stripe: Updating subscription for tenant {tenant_id} to plan {new_plan}"
        )
        return {
            "status": "updated",
            "provider": "stripe",
            "tenant_id": tenant_id,
            "plan": new_plan,
            "message": "Stripe integration not yet implemented",
        }

    def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve subscription details from Stripe."""
        logger.info(f"Stripe: Retrieving subscription for tenant {tenant_id}")
        return None

    def verify_webhook_signature(self, signature: str, body: bytes) -> bool:
        """Verify Stripe webhook signature."""
        logger.warning("Stripe webhook verification not yet implemented")
        return False


def get_billing_provider() -> BillingProvider:
    """
    Factory function to get the configured billing provider.

    Returns the provider specified by BILLING_PROVIDER environment variable.
    Defaults to LemonSqueezy if not specified.

    Returns:
        BillingProvider instance (LemonSqueezyProvider or StripeProvider)

    Raises:
        ValueError: If BILLING_PROVIDER is set to an unknown provider
    """
    provider_name = os.getenv("BILLING_PROVIDER", "lemonsqueezy").lower()

    if provider_name == "stripe":
        logger.info("Using Stripe billing provider")
        return StripeProvider()
    elif provider_name == "lemonsqueezy":
        logger.info("Using LemonSqueezy billing provider")
        return LemonSqueezyProvider()
    else:
        raise ValueError(
            f"Unknown billing provider: {provider_name}. "
            "Supported providers: lemonsqueezy, stripe"
        )
