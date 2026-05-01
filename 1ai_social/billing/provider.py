"""
Abstract billing provider interface with LemonSqueezy and Stripe implementations.

This module provides a pluggable billing provider system that allows switching
between different payment processors (LemonSqueezy, Stripe, etc.) via environment
configuration.

Supported Providers:
- lemonsqueezy: LemonSqueezy payment processor (default)
- stripe: Stripe payment processor

Environment Variables:
- BILLING_PROVIDER: Provider to use ('lemonsqueezy' or 'stripe', default: 'lemonsqueezy')
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

try:
    import stripe

    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(
        "stripe library not installed - Stripe provider will not be available"
    )

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

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
        self.verifier = None
        self.api_key = os.getenv("LEMONSQUEEZY_API_KEY")
        self.store_id = os.getenv("LEMONSQUEEZY_STORE_ID")
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
        if not self.api_key or not self.store_id:
            logger.error("LemonSqueezy API key or store ID not configured")
            return {
                "status": "error",
                "provider": "lemonsqueezy",
                "message": "API credentials not configured",
            }

        variant_id = self._get_variant_id_for_plan(plan)
        if not variant_id:
            logger.error(f"No variant ID configured for plan: {plan}")
            return {
                "status": "error",
                "provider": "lemonsqueezy",
                "message": f"Plan {plan} not configured",
            }

        try:
            if HTTPX_AVAILABLE:
                import httpx

                response = httpx.post(
                    "https://api.lemonsqueezy.com/v1/subscriptions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={
                        "data": {
                            "type": "subscriptions",
                            "attributes": {
                                "store_id": self.store_id,
                                "variant_id": variant_id,
                                "customer_email": customer_email,
                                "custom_data": {"tenant_id": tenant_id},
                            },
                        }
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                logger.info(f"LemonSqueezy subscription created for tenant {tenant_id}")
                return {
                    "status": "success",
                    "provider": "lemonsqueezy",
                    "tenant_id": tenant_id,
                    "plan": plan,
                    "subscription_id": data.get("data", {}).get("id"),
                }
            else:
                from urllib.request import Request, urlopen
                import json

                req = Request(
                    "https://api.lemonsqueezy.com/v1/subscriptions",
                    data=json.dumps(
                        {
                            "data": {
                                "type": "subscriptions",
                                "attributes": {
                                    "store_id": self.store_id,
                                    "variant_id": variant_id,
                                    "customer_email": customer_email,
                                    "custom_data": {"tenant_id": tenant_id},
                                },
                            }
                        }
                    ).encode(),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    method="POST",
                )
                with urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode())
                    logger.info(
                        f"LemonSqueezy subscription created for tenant {tenant_id}"
                    )
                    return {
                        "status": "success",
                        "provider": "lemonsqueezy",
                        "tenant_id": tenant_id,
                        "plan": plan,
                        "subscription_id": data.get("data", {}).get("id"),
                    }
        except Exception as e:
            logger.error(f"LemonSqueezy API error: {e}")
            return {
                "status": "error",
                "provider": "lemonsqueezy",
                "message": str(e),
            }

    def cancel_subscription(self, tenant_id: str) -> Dict[str, Any]:
        from .lemonsqueezy import Subscription

        try:
            from .database import get_session

            session = get_session()
        except:
            logger.error("Cannot get database session")
            return {"status": "error", "message": "Database unavailable"}

        subscription = (
            session.query(Subscription).filter_by(tenant_id=tenant_id).first()
        )
        if not subscription or not subscription.lemonsqueezy_subscription_id:
            logger.warning(f"No subscription found for tenant {tenant_id}")
            return {"status": "error", "message": "Subscription not found"}

        if not self.api_key:
            logger.error("LemonSqueezy API key not configured")
            return {"status": "error", "message": "API key not configured"}

        try:
            if HTTPX_AVAILABLE:
                import httpx

                response = httpx.delete(
                    f"https://api.lemonsqueezy.com/v1/subscriptions/{subscription.lemonsqueezy_subscription_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
            else:
                from urllib.request import Request, urlopen

                req = Request(
                    f"https://api.lemonsqueezy.com/v1/subscriptions/{subscription.lemonsqueezy_subscription_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Accept": "application/json",
                    },
                    method="DELETE",
                )
                urlopen(req, timeout=30)

            logger.info(f"LemonSqueezy subscription cancelled for tenant {tenant_id}")
            return {
                "status": "cancelled",
                "provider": "lemonsqueezy",
                "tenant_id": tenant_id,
            }
        except Exception as e:
            logger.error(f"LemonSqueezy cancel error: {e}")
            return {"status": "error", "message": str(e)}

    def update_subscription(self, tenant_id: str, new_plan: str) -> Dict[str, Any]:
        from .lemonsqueezy import Subscription

        try:
            from .database import get_session

            session = get_session()
        except:
            logger.error("Cannot get database session")
            return {"status": "error", "message": "Database unavailable"}

        subscription = (
            session.query(Subscription).filter_by(tenant_id=tenant_id).first()
        )
        if not subscription or not subscription.lemonsqueezy_subscription_id:
            logger.warning(f"No subscription found for tenant {tenant_id}")
            return {"status": "error", "message": "Subscription not found"}

        variant_id = self._get_variant_id_for_plan(new_plan)
        if not variant_id:
            logger.error(f"No variant ID configured for plan: {new_plan}")
            return {"status": "error", "message": f"Plan {new_plan} not configured"}

        if not self.api_key:
            logger.error("LemonSqueezy API key not configured")
            return {"status": "error", "message": "API key not configured"}

        try:
            if HTTPX_AVAILABLE:
                import httpx

                response = httpx.patch(
                    f"https://api.lemonsqueezy.com/v1/subscriptions/{subscription.lemonsqueezy_subscription_id}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={
                        "data": {
                            "type": "subscriptions",
                            "id": subscription.lemonsqueezy_subscription_id,
                            "attributes": {"variant_id": variant_id},
                        }
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
            else:
                from urllib.request import Request, urlopen
                import json

                req = Request(
                    f"https://api.lemonsqueezy.com/v1/subscriptions/{subscription.lemonsqueezy_subscription_id}",
                    data=json.dumps(
                        {
                            "data": {
                                "type": "subscriptions",
                                "id": subscription.lemonsqueezy_subscription_id,
                                "attributes": {"variant_id": variant_id},
                            }
                        }
                    ).encode(),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    method="PATCH",
                )
                urlopen(req, timeout=30)

            logger.info(
                f"LemonSqueezy subscription updated for tenant {tenant_id} to plan {new_plan}"
            )
            return {
                "status": "updated",
                "provider": "lemonsqueezy",
                "tenant_id": tenant_id,
                "plan": new_plan,
            }
        except Exception as e:
            logger.error(f"LemonSqueezy update error: {e}")
            return {"status": "error", "message": str(e)}

    def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        from .lemonsqueezy import Subscription

        try:
            from .database import get_session

            session = get_session()
        except:
            logger.error("Cannot get database session")
            return None

        subscription = (
            session.query(Subscription).filter_by(tenant_id=tenant_id).first()
        )
        if not subscription:
            logger.info(f"No subscription found for tenant {tenant_id}")
            return None

        return {
            "tenant_id": subscription.tenant_id,
            "plan": subscription.plan,
            "status": subscription.status,
            "subscription_id": subscription.lemonsqueezy_subscription_id,
            "current_period_start": subscription.current_period_start.isoformat()
            if subscription.current_period_start
            else None,
            "current_period_end": subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }

    def _get_variant_id_for_plan(self, plan: str) -> Optional[str]:
        variant_map = {
            "starter": os.getenv("LEMONSQUEEZY_VARIANT_STARTER"),
            "pro": os.getenv("LEMONSQUEEZY_VARIANT_PRO"),
            "enterprise": os.getenv("LEMONSQUEEZY_VARIANT_ENTERPRISE"),
        }
        return variant_map.get(plan.lower())

    def verify_webhook_signature(self, signature: str, body: bytes) -> bool:
        """Verify LemonSqueezy webhook signature."""
        if not self.verifier:
            logger.warning("LemonSqueezy webhook verifier not configured")
            return False
        return self.verifier.verify_signature(signature, body)


class StripeProvider(BillingProvider):
    """Stripe billing provider implementation."""

    def __init__(self):
        self.api_key = os.getenv("STRIPE_API_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not self.api_key:
            logger.warning("STRIPE_API_KEY not configured")
        if STRIPE_AVAILABLE and self.api_key:
            stripe.api_key = self.api_key

    def create_subscription(
        self, tenant_id: str, plan: str, customer_email: str
    ) -> Dict[str, Any]:
        if not STRIPE_AVAILABLE:
            logger.error("stripe library not installed")
            return {
                "status": "error",
                "provider": "stripe",
                "message": "stripe library not installed",
            }

        if not self.api_key:
            logger.error("STRIPE_API_KEY not configured")
            return {
                "status": "error",
                "provider": "stripe",
                "message": "API key not configured",
            }

        price_id = self._get_price_id_for_plan(plan)
        if not price_id:
            logger.error(f"No price ID configured for plan: {plan}")
            return {
                "status": "error",
                "provider": "stripe",
                "message": f"Plan {plan} not configured",
            }

        try:
            customer = stripe.Customer.create(
                email=customer_email,
                metadata={"tenant_id": tenant_id},
            )

            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price_id}],
                metadata={"tenant_id": tenant_id, "plan": plan},
            )

            logger.info(f"Stripe subscription created for tenant {tenant_id}")
            return {
                "status": "success",
                "provider": "stripe",
                "tenant_id": tenant_id,
                "plan": plan,
                "subscription_id": subscription.id,
                "customer_id": customer.id,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {e}")
            return {
                "status": "error",
                "provider": "stripe",
                "message": str(e),
            }

    def cancel_subscription(self, tenant_id: str) -> Dict[str, Any]:
        if not STRIPE_AVAILABLE:
            logger.error("stripe library not installed")
            return {"status": "error", "message": "stripe library not installed"}

        subscription_id = self._get_stripe_subscription_id(tenant_id)
        if not subscription_id:
            logger.warning(f"No subscription found for tenant {tenant_id}")
            return {"status": "error", "message": "Subscription not found"}

        try:
            stripe.Subscription.delete(subscription_id)
            logger.info(f"Stripe subscription cancelled for tenant {tenant_id}")
            return {
                "status": "cancelled",
                "provider": "stripe",
                "tenant_id": tenant_id,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe cancel error: {e}")
            return {"status": "error", "message": str(e)}

    def update_subscription(self, tenant_id: str, new_plan: str) -> Dict[str, Any]:
        if not STRIPE_AVAILABLE:
            logger.error("stripe library not installed")
            return {"status": "error", "message": "stripe library not installed"}

        subscription_id = self._get_stripe_subscription_id(tenant_id)
        if not subscription_id:
            logger.warning(f"No subscription found for tenant {tenant_id}")
            return {"status": "error", "message": "Subscription not found"}

        price_id = self._get_price_id_for_plan(new_plan)
        if not price_id:
            logger.error(f"No price ID configured for plan: {new_plan}")
            return {"status": "error", "message": f"Plan {new_plan} not configured"}

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            stripe.Subscription.modify(
                subscription_id,
                items=[
                    {
                        "id": subscription["items"]["data"][0].id,
                        "price": price_id,
                    }
                ],
                metadata={"plan": new_plan},
            )
            logger.info(
                f"Stripe subscription updated for tenant {tenant_id} to plan {new_plan}"
            )
            return {
                "status": "updated",
                "provider": "stripe",
                "tenant_id": tenant_id,
                "plan": new_plan,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe update error: {e}")
            return {"status": "error", "message": str(e)}

    def get_subscription(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        if not STRIPE_AVAILABLE:
            logger.error("stripe library not installed")
            return None

        subscription_id = self._get_stripe_subscription_id(tenant_id)
        if not subscription_id:
            logger.info(f"No subscription found for tenant {tenant_id}")
            return None

        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                "tenant_id": tenant_id,
                "subscription_id": subscription.id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe retrieve error: {e}")
            return None

    def verify_webhook_signature(self, signature: str, body: bytes) -> bool:
        if not STRIPE_AVAILABLE:
            logger.error("stripe library not installed")
            return False

        if not self.webhook_secret:
            logger.warning("STRIPE_WEBHOOK_SECRET not configured")
            return False

        try:
            stripe.WebhookSignature.verify_header(body, signature, self.webhook_secret)
            return True
        except stripe.error.SignatureVerificationError as e:
            logger.warning(f"Stripe webhook signature verification failed: {e}")
            return False

    def _get_price_id_for_plan(self, plan: str) -> Optional[str]:
        price_map = {
            "starter": os.getenv("STRIPE_PRICE_STARTER"),
            "pro": os.getenv("STRIPE_PRICE_PRO"),
            "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE"),
        }
        return price_map.get(plan.lower())

    def _get_stripe_subscription_id(self, tenant_id: str) -> Optional[str]:
        from .lemonsqueezy import Subscription

        try:
            from .database import get_session

            session = get_session()
        except:
            logger.error("Cannot get database session")
            return None

        subscription = (
            session.query(Subscription).filter_by(tenant_id=tenant_id).first()
        )
        if subscription:
            return subscription.lemonsqueezy_subscription_id
        return None


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
