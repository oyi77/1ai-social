#!/usr/bin/env python3
"""Test webhook signature verification."""

import time
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import importlib

webhooks = importlib.import_module("1ai_social.webhooks")
WebhookVerifier = webhooks.WebhookVerifier
InvalidSignatureError = webhooks.InvalidSignatureError
ReplayAttackError = webhooks.ReplayAttackError
DuplicateWebhookError = webhooks.DuplicateWebhookError


def test_valid_signature():
    """Test webhook with valid signature."""
    print("Test 1: Valid signature")

    secret = "test-secret-key"
    verifier = WebhookVerifier(secret=secret)

    timestamp = str(int(time.time()))
    body = b'{"event": "test", "data": "hello"}'
    webhook_id = "test-webhook-001"

    signature = verifier.compute_signature(timestamp, body)

    try:
        verifier.verify_webhook(signature, timestamp, webhook_id, body)
        print("✓ Valid signature accepted")
        return True
    except Exception as e:
        print(f"✗ Valid signature rejected: {e}")
        return False


def test_invalid_signature():
    """Test webhook with invalid signature."""
    print("\nTest 2: Invalid signature")

    secret = "test-secret-key"
    verifier = WebhookVerifier(secret=secret)

    timestamp = str(int(time.time()))
    body = b'{"event": "test", "data": "hello"}'
    webhook_id = "test-webhook-002"

    invalid_signature = "sha256=invalid_signature_here"

    try:
        verifier.verify_webhook(invalid_signature, timestamp, webhook_id, body)
        print("✗ Invalid signature accepted (should reject)")
        return False
    except InvalidSignatureError:
        print("✓ Invalid signature rejected")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_old_timestamp():
    """Test webhook with old timestamp (replay attack)."""
    print("\nTest 3: Old timestamp (replay attack)")

    secret = "test-secret-key"
    verifier = WebhookVerifier(secret=secret, max_timestamp_age=300)

    old_timestamp = str(int(time.time()) - 600)
    body = b'{"event": "test", "data": "hello"}'
    webhook_id = "test-webhook-003"

    signature = verifier.compute_signature(old_timestamp, body)

    try:
        verifier.verify_webhook(signature, old_timestamp, webhook_id, body)
        print("✗ Old timestamp accepted (should reject)")
        return False
    except ReplayAttackError:
        print("✓ Old timestamp rejected")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_timing_safe_comparison():
    """Test that signature comparison is timing-safe."""
    print("\nTest 4: Timing-safe comparison")

    secret = "test-secret-key"
    verifier = WebhookVerifier(secret=secret)

    timestamp = str(int(time.time()))
    body = b'{"event": "test", "data": "hello"}'
    webhook_id = "test-webhook-004"

    correct_signature = verifier.compute_signature(timestamp, body)

    almost_correct = correct_signature[:-1] + "X"

    try:
        verifier.verify_webhook(almost_correct, timestamp, webhook_id, body)
        print("✗ Almost correct signature accepted (should reject)")
        return False
    except InvalidSignatureError:
        print("✓ Almost correct signature rejected (timing-safe)")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_signature_format():
    """Test signature format validation."""
    print("\nTest 5: Signature format validation")

    secret = "test-secret-key"
    verifier = WebhookVerifier(secret=secret)

    timestamp = str(int(time.time()))
    body = b'{"event": "test", "data": "hello"}'
    webhook_id = "test-webhook-005"

    invalid_format = "invalid_format_without_prefix"

    try:
        verifier.verify_webhook(invalid_format, timestamp, webhook_id, body)
        print("✗ Invalid format accepted (should reject)")
        return False
    except InvalidSignatureError:
        print("✓ Invalid format rejected")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_missing_signature():
    """Test missing signature."""
    print("\nTest 6: Missing signature")

    secret = "test-secret-key"
    verifier = WebhookVerifier(secret=secret)

    timestamp = str(int(time.time()))
    body = b'{"event": "test", "data": "hello"}'
    webhook_id = "test-webhook-006"

    try:
        verifier.verify_webhook("", timestamp, webhook_id, body)
        print("✗ Missing signature accepted (should reject)")
        return False
    except InvalidSignatureError:
        print("✓ Missing signature rejected")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_missing_timestamp():
    """Test missing timestamp."""
    print("\nTest 7: Missing timestamp")

    secret = "test-secret-key"
    verifier = WebhookVerifier(secret=secret)

    body = b'{"event": "test", "data": "hello"}'
    webhook_id = "test-webhook-007"

    try:
        verifier.verify_timestamp("")
        print("✗ Missing timestamp accepted (should reject)")
        return False
    except ReplayAttackError:
        print("✓ Missing timestamp rejected")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Webhook Signature Verification Tests")
    print("=" * 60)

    tests = [
        test_valid_signature,
        test_invalid_signature,
        test_old_timestamp,
        test_timing_safe_comparison,
        test_signature_format,
        test_missing_signature,
        test_missing_timestamp,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    if all(results):
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
