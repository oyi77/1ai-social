#!/usr/bin/env python3
"""Test script for encryption module."""

import os
import sys
import importlib
from base64 import b64encode

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

encryption_module = importlib.import_module("1ai_social.encryption")
TokenEncryption = encryption_module.TokenEncryption
EncryptionError = encryption_module.EncryptionError
DecryptionError = encryption_module.DecryptionError


def test_encryption_roundtrip():
    """Test basic encryption and decryption."""
    print("Test 1: Basic encryption/decryption roundtrip")

    test_key = b64encode(os.urandom(32)).decode("ascii")
    encryptor = TokenEncryption(master_key=test_key)

    plaintext = "oauth_token_12345_secret"
    print(f"  Original: {plaintext}")

    encrypted = encryptor.encrypt(plaintext)
    print(f"  Encrypted: {encrypted[:50]}...")

    decrypted = encryptor.decrypt(encrypted)
    print(f"  Decrypted: {decrypted}")

    assert plaintext == decrypted, "Decryption failed"
    print("  ✓ PASSED\n")


def test_multiple_encryptions_different():
    """Test that same plaintext produces different ciphertexts."""
    print("Test 2: Multiple encryptions produce different ciphertexts")

    test_key = b64encode(os.urandom(32)).decode("ascii")
    encryptor = TokenEncryption(master_key=test_key)

    plaintext = "same_token_value"
    encrypted1 = encryptor.encrypt(plaintext)
    encrypted2 = encryptor.encrypt(plaintext)

    print(f"  Encryption 1: {encrypted1[:50]}...")
    print(f"  Encryption 2: {encrypted2[:50]}...")

    assert encrypted1 != encrypted2, "Encryptions should differ"
    assert encryptor.decrypt(encrypted1) == plaintext
    assert encryptor.decrypt(encrypted2) == plaintext
    print("  ✓ PASSED\n")


def test_tampered_ciphertext():
    """Test that tampered ciphertext is detected."""
    print("Test 3: Tampered ciphertext detection")

    test_key = b64encode(os.urandom(32)).decode("ascii")
    encryptor = TokenEncryption(master_key=test_key)

    plaintext = "sensitive_token"
    encrypted = encryptor.encrypt(plaintext)

    tampered = encrypted[:-10] + "XXXXXXXXXX"

    try:
        encryptor.decrypt(tampered)
        print("  ✗ FAILED: Should have raised DecryptionError")
        sys.exit(1)
    except DecryptionError as e:
        print(f"  Correctly detected tampering: {e}")
        print("  ✓ PASSED\n")


def test_key_rotation():
    """Test key rotation functionality."""
    print("Test 4: Key rotation")

    old_key = b64encode(os.urandom(32)).decode("ascii")
    new_key = b64encode(os.urandom(32)).decode("ascii")

    encryptor = TokenEncryption(master_key=old_key)

    plaintext = "token_to_rotate"
    old_encrypted = encryptor.encrypt(plaintext)
    print(f"  Encrypted with old key: {old_encrypted[:50]}...")

    new_encrypted = encryptor.rotate_key(old_encrypted, new_key)
    print(f"  Re-encrypted with new key: {new_encrypted[:50]}...")

    new_encryptor = TokenEncryption(master_key=new_key)
    decrypted = new_encryptor.decrypt(new_encrypted)

    assert decrypted == plaintext, "Key rotation failed"
    print(f"  Decrypted: {decrypted}")
    print("  ✓ PASSED\n")


def test_empty_plaintext():
    """Test error handling for empty plaintext."""
    print("Test 5: Empty plaintext handling")

    test_key = b64encode(os.urandom(32)).decode("ascii")
    encryptor = TokenEncryption(master_key=test_key)

    try:
        encryptor.encrypt("")
        print("  ✗ FAILED: Should have raised EncryptionError")
        sys.exit(1)
    except EncryptionError as e:
        print(f"  Correctly rejected empty plaintext: {e}")
        print("  ✓ PASSED\n")


def test_long_token():
    """Test encryption of long tokens."""
    print("Test 6: Long token encryption")

    test_key = b64encode(os.urandom(32)).decode("ascii")
    encryptor = TokenEncryption(master_key=test_key)

    long_token = "x" * 1000
    encrypted = encryptor.encrypt(long_token)
    decrypted = encryptor.decrypt(encrypted)

    assert decrypted == long_token, "Long token encryption failed"
    print(f"  Token length: {len(long_token)} chars")
    print(f"  Encrypted length: {len(encrypted)} chars")
    print("  ✓ PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("ENCRYPTION MODULE TEST SUITE")
    print("=" * 60 + "\n")

    try:
        test_encryption_roundtrip()
        test_multiple_encryptions_different()
        test_tampered_ciphertext()
        test_key_rotation()
        test_empty_plaintext()
        test_long_token()

        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
