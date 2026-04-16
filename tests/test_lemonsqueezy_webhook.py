"""Test LemonSqueezy webhook integration."""

import json
import hashlib
import hmac
from datetime import datetime


def test_webhook_signature():
    """Test HMAC-SHA256 signature generation."""
    secret = "test_secret_key"
    payload = {
        "meta": {
            "event_name": "subscription_created",
            "webhook_id": "test-webhook-123",
        },
        "data": {
            "id": "12345",
            "attributes": {
                "customer_id": "67890",
                "status": "active",
                "variant_id": "111",
                "renews_at": "2026-05-16T00:00:00Z",
            },
        },
    }

    body = json.dumps(payload)
    body_bytes = body.encode("utf-8")

    signature = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    print(f"Payload: {body}")
    print(f"Signature: {signature}")
    print(f"\nTo test webhook, use:")
    print(f"  X-Signature: {signature}")
    print(f"  Body: {body}")

    return signature, body


def generate_test_events():
    """Generate test webhook payloads for different events."""
    secret = "test_secret_key"

    events = {
        "subscription_created": {
            "meta": {
                "event_name": "subscription_created",
                "webhook_id": "webhook-created-001",
            },
            "data": {
                "id": "sub_12345",
                "attributes": {
                    "customer_id": "cust_67890",
                    "status": "active",
                    "variant_id": "variant_starter",
                    "renews_at": "2026-05-16T00:00:00Z",
                    "created_at": "2026-04-16T10:00:00Z",
                },
            },
        },
        "subscription_updated": {
            "meta": {
                "event_name": "subscription_updated",
                "webhook_id": "webhook-updated-001",
            },
            "data": {
                "id": "sub_12345",
                "attributes": {"status": "active", "renews_at": "2026-06-16T00:00:00Z"},
            },
        },
        "subscription_cancelled": {
            "meta": {
                "event_name": "subscription_cancelled",
                "webhook_id": "webhook-cancelled-001",
            },
            "data": {
                "id": "sub_12345",
                "attributes": {
                    "status": "cancelled",
                    "ends_at": "2026-05-16T00:00:00Z",
                },
            },
        },
        "subscription_payment_success": {
            "meta": {
                "event_name": "subscription_payment_success",
                "webhook_id": "webhook-payment-success-001",
            },
            "data": {
                "id": "payment_99999",
                "attributes": {
                    "subscription_id": "sub_12345",
                    "amount": 2900,
                    "status": "paid",
                },
            },
        },
        "subscription_payment_failed": {
            "meta": {
                "event_name": "subscription_payment_failed",
                "webhook_id": "webhook-payment-failed-001",
            },
            "data": {
                "id": "payment_88888",
                "attributes": {
                    "subscription_id": "sub_12345",
                    "amount": 2900,
                    "status": "failed",
                },
            },
        },
    }

    print("=" * 80)
    print("LEMONSQUEEZY WEBHOOK TEST PAYLOADS")
    print("=" * 80)
    print(f"\nWebhook Secret: {secret}")
    print(f"Set environment variable: LEMONSQUEEZY_WEBHOOK_SECRET={secret}\n")

    for event_name, payload in events.items():
        body = json.dumps(payload, indent=2)
        body_bytes = body.encode("utf-8")

        signature = hmac.new(
            secret.encode("utf-8"), body_bytes, hashlib.sha256
        ).hexdigest()

        print(f"\n{'=' * 80}")
        print(f"Event: {event_name}")
        print(f"{'=' * 80}")
        print(f"\nX-Signature: {signature}")
        print(f"\nPayload:\n{body}")
        print(f"\nCURL command:")
        print(f"curl -X POST http://localhost:8000/webhooks/lemonsqueezy \\")
        print(f'  -H "X-Signature: {signature}" \\')
        print(f'  -H "Content-Type: application/json" \\')
        print(f"  -d '{body.replace(chr(10), '')}'")
        print()


if __name__ == "__main__":
    generate_test_events()
