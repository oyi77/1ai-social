"""Encryption module for OAuth token encryption at rest.

This module provides AES-256-GCM encryption for sensitive credentials with:
- AES-256-GCM authenticated encryption
- Key derivation using PBKDF2-HMAC-SHA256
- Key versioning for rotation support
- Secure nonce generation
- Integration with AWS Secrets Manager

Security Features:
- Authenticated encryption (prevents tampering)
- Unique nonce per encryption (prevents replay attacks)
- Key versioning (enables rotation without data loss)
- PBKDF2 key derivation (strengthens master key)

Storage Format: version|salt|nonce|ciphertext
- version: 1 byte (key version for rotation)
- salt: 16 bytes (for key derivation)
- nonce: 12 bytes (for AES-GCM)
- ciphertext: variable length (includes authentication tag)
"""

import os
import logging
from typing import Optional
from base64 import b64encode, b64decode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidTag

from .secrets import get_required_secret

logger = logging.getLogger(__name__)

# Constants
KEY_VERSION = 1  # Current key version
SALT_LENGTH = 16  # bytes
NONCE_LENGTH = 12  # bytes (96 bits, NIST recommended for AES-GCM)
KEY_LENGTH = 32  # bytes (256 bits for AES-256)
PBKDF2_ITERATIONS = 600_000  # OWASP recommendation for 2023+


class EncryptionError(Exception):
    """Base exception for encryption errors."""

    pass


class DecryptionError(Exception):
    """Base exception for decryption errors."""

    pass


class TokenEncryption:
    """Handles encryption and decryption of OAuth tokens."""

    def __init__(self, master_key: Optional[str] = None):
        """Initialize token encryption.

        Args:
            master_key: Master encryption key (base64 encoded).
                       If None, loads from AWS Secrets Manager.

        Raises:
            ValueError: If master key is invalid or unavailable.
        """
        if master_key is None:
            # Load from AWS Secrets Manager
            master_key = get_required_secret("ENCRYPTION_MASTER_KEY")

        if not master_key:
            raise ValueError("Master encryption key is required")

        try:
            # Decode base64 master key
            self._master_key = b64decode(master_key)
            if len(self._master_key) < 32:
                raise ValueError("Master key must be at least 32 bytes")
        except Exception as e:
            raise ValueError(f"Invalid master key format: {e}")

        logger.info("TokenEncryption initialized successfully")

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master key using PBKDF2.

        Args:
            salt: Random salt for key derivation.

        Returns:
            Derived encryption key (32 bytes).
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(self._master_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext token.

        Args:
            plaintext: Token to encrypt.

        Returns:
            Base64-encoded encrypted token with format: version|salt|nonce|ciphertext

        Raises:
            EncryptionError: If encryption fails.
        """
        if not plaintext:
            raise EncryptionError("Plaintext cannot be empty")

        try:
            # Generate random salt and nonce
            salt = os.urandom(SALT_LENGTH)
            nonce = os.urandom(NONCE_LENGTH)

            # Derive encryption key
            derived_key = self._derive_key(salt)

            # Encrypt with AES-256-GCM
            aesgcm = AESGCM(derived_key)
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

            # Pack: version (1 byte) | salt (16 bytes) | nonce (12 bytes) | ciphertext
            version_byte = KEY_VERSION.to_bytes(1, byteorder="big")
            packed = version_byte + salt + nonce + ciphertext

            # Encode to base64 for storage
            encoded = b64encode(packed).decode("ascii")

            logger.debug(f"Token encrypted successfully (version {KEY_VERSION})")
            return encoded

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt token: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt encrypted token.

        Args:
            ciphertext: Base64-encoded encrypted token.

        Returns:
            Decrypted plaintext token.

        Raises:
            DecryptionError: If decryption fails or authentication tag is invalid.
        """
        if not ciphertext:
            raise DecryptionError("Ciphertext cannot be empty")

        try:
            # Decode from base64
            packed = b64decode(ciphertext)

            # Unpack: version (1 byte) | salt (16 bytes) | nonce (12 bytes) | ciphertext
            if len(packed) < 1 + SALT_LENGTH + NONCE_LENGTH:
                raise DecryptionError("Invalid ciphertext format: too short")

            version = int.from_bytes(packed[0:1], byteorder="big")
            salt = packed[1 : 1 + SALT_LENGTH]
            nonce = packed[1 + SALT_LENGTH : 1 + SALT_LENGTH + NONCE_LENGTH]
            encrypted_data = packed[1 + SALT_LENGTH + NONCE_LENGTH :]

            # Check version compatibility
            if version != KEY_VERSION:
                logger.warning(
                    f"Decrypting with old key version {version} (current: {KEY_VERSION})"
                )
                # In production, you might load the old key here for rotation support

            # Derive encryption key
            derived_key = self._derive_key(salt)

            # Decrypt with AES-256-GCM
            aesgcm = AESGCM(derived_key)
            plaintext_bytes = aesgcm.decrypt(nonce, encrypted_data, None)

            plaintext = plaintext_bytes.decode("utf-8")

            logger.debug(f"Token decrypted successfully (version {version})")
            return plaintext

        except InvalidTag:
            logger.error(
                "Decryption failed: Invalid authentication tag (data may be tampered)"
            )
            raise DecryptionError(
                "Authentication failed: token may be corrupted or tampered"
            )
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError(f"Failed to decrypt token: {e}")

    def rotate_key(self, old_ciphertext: str, new_master_key: str) -> str:
        """Rotate encryption key by re-encrypting with new master key.

        Args:
            old_ciphertext: Token encrypted with old key.
            new_master_key: New master key (base64 encoded).

        Returns:
            Token re-encrypted with new master key.

        Raises:
            DecryptionError: If decryption with old key fails.
            EncryptionError: If encryption with new key fails.
        """
        # Decrypt with current key
        plaintext = self.decrypt(old_ciphertext)

        # Create new encryptor with new master key
        new_encryptor = TokenEncryption(master_key=new_master_key)

        # Re-encrypt with new key
        new_ciphertext = new_encryptor.encrypt(plaintext)

        logger.info("Key rotation completed successfully")
        return new_ciphertext


# Global singleton instance
_token_encryption: Optional[TokenEncryption] = None


def get_token_encryption() -> TokenEncryption:
    """Get or create the global TokenEncryption instance.

    Returns:
        TokenEncryption singleton instance.
    """
    global _token_encryption
    if _token_encryption is None:
        _token_encryption = TokenEncryption()
    return _token_encryption


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token using the global TokenEncryption instance.

    Args:
        plaintext: Token to encrypt.

    Returns:
        Base64-encoded encrypted token.
    """
    encryptor = get_token_encryption()
    return encryptor.encrypt(plaintext)


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a token using the global TokenEncryption instance.

    Args:
        ciphertext: Base64-encoded encrypted token.

    Returns:
        Decrypted plaintext token.
    """
    encryptor = get_token_encryption()
    return encryptor.decrypt(ciphertext)
