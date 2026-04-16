"""Test API key generation, validation, and tenant isolation"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib

api_keys = importlib.import_module("1ai_social.api_keys")
generate_api_key = api_keys.generate_api_key
validate_api_key_format = api_keys.validate_api_key_format
InvalidAPIKeyError = api_keys.InvalidAPIKeyError


def test_api_key_generation():
    """Test API key generation produces correct format"""
    print("Testing API key generation...")

    api_key, key_hash = generate_api_key("tenant-123", ["read", "write"], "Test Key")

    print(f"✓ Generated key: {api_key}")
    print(f"✓ Key hash: {key_hash}")
    print(f"✓ Key starts with sk_live_: {api_key.startswith('sk_live_')}")
    print(f"✓ Hash length: {len(key_hash)} (expected 64)")

    assert api_key.startswith("sk_live_"), "Key should start with sk_live_"
    assert len(key_hash) == 64, "SHA-256 hash should be 64 characters"
    assert "_" in api_key, "Key should contain underscores"

    parts = api_key.split("_")
    assert len(parts) == 4, f"Key should have 4 parts, got {len(parts)}"

    print("✓ API key generation test passed\n")


def test_api_key_format_validation():
    """Test API key format validation"""
    print("Testing API key format validation...")

    api_key, _ = generate_api_key("tenant-456", ["read"], "Valid Key")

    assert validate_api_key_format(api_key), "Valid key should pass validation"
    print(f"✓ Valid key passed: {api_key}")

    invalid_keys = [
        "invalid_key",
        "sk_test_abc123",
        "sk_live_",
        "sk_live_abc",
        "",
    ]

    for invalid_key in invalid_keys:
        result = validate_api_key_format(invalid_key)
        print(f"✓ Invalid key rejected: {invalid_key} (result: {result})")

    print("✓ API key format validation test passed\n")


def test_key_uniqueness():
    """Test that generated keys are unique"""
    print("Testing key uniqueness...")

    keys = set()
    for i in range(100):
        api_key, _ = generate_api_key(f"tenant-{i}", ["read"], f"Key {i}")
        keys.add(api_key)

    assert len(keys) == 100, "All generated keys should be unique"
    print(f"✓ Generated 100 unique keys")
    print("✓ Key uniqueness test passed\n")


def test_different_tenants_different_keys():
    """Test that different tenants get different keys"""
    print("Testing tenant isolation in key generation...")

    key1, hash1 = generate_api_key("tenant-A", ["read", "write"], "Tenant A Key")
    key2, hash2 = generate_api_key("tenant-B", ["read", "write"], "Tenant B Key")

    assert key1 != key2, "Different tenants should get different keys"
    assert hash1 != hash2, "Different tenants should get different hashes"

    print(f"✓ Tenant A key: {key1[:30]}...")
    print(f"✓ Tenant B key: {key2[:30]}...")
    print(f"✓ Keys are different: {key1 != key2}")
    print("✓ Tenant isolation test passed\n")


if __name__ == "__main__":
    print("=" * 60)
    print("API Key System Tests")
    print("=" * 60 + "\n")

    try:
        test_api_key_generation()
        test_api_key_format_validation()
        test_key_uniqueness()
        test_different_tenants_different_keys()

        print("=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
