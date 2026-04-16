"""AWS Secrets Manager integration for 1ai-social.

This module provides secure secrets management using AWS Secrets Manager with:
- Automatic secret retrieval from AWS Secrets Manager
- In-memory caching to avoid rate limits
- Fallback to environment variables for local development
- Comprehensive error handling

Rotation Policy: Secrets are rotated every 90 days via AWS Secrets Manager.
"""

import os
import json
import logging
from typing import Dict, Optional, Any
from functools import lru_cache

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manages secrets from AWS Secrets Manager with local fallback."""

    def __init__(
        self,
        secret_name: Optional[str] = None,
        region_name: Optional[str] = None,
        use_local_fallback: bool = True,
    ):
        """Initialize secrets manager.

        Args:
            secret_name: Name of the secret in AWS Secrets Manager.
                        Defaults to AWS_SECRET_NAME env var or '1ai-social/secrets'.
            region_name: AWS region. Defaults to AWS_REGION env var or 'us-east-1'.
            use_local_fallback: If True, fall back to environment variables when
                              AWS Secrets Manager is unavailable (for local dev).
        """
        self.secret_name = secret_name or os.getenv(
            "AWS_SECRET_NAME", "1ai-social/secrets"
        )
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.use_local_fallback = use_local_fallback
        self._secrets_cache: Optional[Dict[str, Any]] = None
        self._client = None

        if BOTO3_AVAILABLE:
            try:
                session = boto3.session.Session()
                self._client = session.client(
                    service_name="secretsmanager", region_name=self.region_name
                )
                logger.info(
                    f"AWS Secrets Manager client initialized for region: {self.region_name}"
                )
            except NoCredentialsError:
                logger.warning("AWS credentials not found. Using local fallback mode.")
                self._client = None
        else:
            logger.warning("boto3 not installed. Using local fallback mode.")

    def _fetch_from_aws(self) -> Dict[str, Any]:
        """Fetch secrets from AWS Secrets Manager.

        Returns:
            Dictionary of secret key-value pairs.

        Raises:
            ClientError: If AWS API call fails.
        """
        if not self._client:
            raise RuntimeError("AWS Secrets Manager client not available")

        try:
            response = self._client.get_secret_value(SecretId=self.secret_name)

            # Parse secret string (JSON format expected)
            if "SecretString" in response:
                secret_data = json.loads(response["SecretString"])
                logger.info(
                    f"Successfully retrieved secrets from AWS Secrets Manager: {self.secret_name}"
                )
                return secret_data
            else:
                # Binary secrets not supported in this implementation
                raise ValueError(
                    "Binary secrets are not supported. Use SecretString format."
                )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "ResourceNotFoundException":
                logger.error(f"Secret not found: {self.secret_name}")
            elif error_code == "InvalidRequestException":
                logger.error(f"Invalid request: {error_message}")
            elif error_code == "InvalidParameterException":
                logger.error(f"Invalid parameter: {error_message}")
            elif error_code == "DecryptionFailure":
                logger.error(f"Decryption failed: {error_message}")
            elif error_code == "InternalServiceError":
                logger.error(f"AWS service error: {error_message}")
            else:
                logger.error(f"Unexpected AWS error [{error_code}]: {error_message}")

            raise

    def _fetch_from_env(self) -> Dict[str, Any]:
        """Fetch secrets from environment variables (local fallback).

        Returns:
            Dictionary of secret key-value pairs from environment.
        """
        secrets = {
            "POSTBRIDGE_API_KEY": os.getenv("POSTBRIDGE_API_KEY", ""),
            "NVIDIA_API_KEY": os.getenv("NVIDIA_API_KEY", ""),
            "BYTEPLUS_API_KEY": os.getenv("BYTEPLUS_API_KEY", ""),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
            "DATABASE_URL": os.getenv("DATABASE_URL", ""),
        }

        logger.info("Using environment variables for secrets (local development mode)")
        return secrets

    def load_secrets(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load secrets from AWS Secrets Manager or environment variables.

        Secrets are cached in memory after first load to avoid repeated API calls.

        Args:
            force_refresh: If True, bypass cache and fetch fresh secrets.

        Returns:
            Dictionary of secret key-value pairs.

        Raises:
            RuntimeError: If secrets cannot be loaded from any source.
        """
        # Return cached secrets if available
        if self._secrets_cache and not force_refresh:
            logger.debug("Returning cached secrets")
            return self._secrets_cache

        # Try AWS Secrets Manager first
        if self._client:
            try:
                self._secrets_cache = self._fetch_from_aws()
                return self._secrets_cache
            except Exception as e:
                logger.error(f"Failed to fetch from AWS Secrets Manager: {e}")
                if not self.use_local_fallback:
                    raise RuntimeError(f"Failed to load secrets from AWS: {e}")

        # Fallback to environment variables
        if self.use_local_fallback:
            self._secrets_cache = self._fetch_from_env()
            return self._secrets_cache

        raise RuntimeError(
            "Unable to load secrets. AWS Secrets Manager unavailable and local fallback disabled."
        )

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a specific secret value by key.

        Args:
            key: Secret key name.
            default: Default value if key not found.

        Returns:
            Secret value or default.
        """
        secrets = self.load_secrets()
        return secrets.get(key, default)

    def get_required(self, key: str) -> str:
        """Get a required secret value by key.

        Args:
            key: Secret key name.

        Returns:
            Secret value.

        Raises:
            ValueError: If secret key not found or empty.
        """
        value = self.get(key)
        if not value:
            raise ValueError(f"Required secret '{key}' not found or empty")
        return value


# Global singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global SecretsManager instance.

    Returns:
        SecretsManager singleton instance.
    """
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def load_secrets(force_refresh: bool = False) -> Dict[str, Any]:
    """Load secrets using the global SecretsManager instance.

    Args:
        force_refresh: If True, bypass cache and fetch fresh secrets.

    Returns:
        Dictionary of secret key-value pairs.
    """
    manager = get_secrets_manager()
    return manager.load_secrets(force_refresh=force_refresh)


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a specific secret value.

    Args:
        key: Secret key name.
        default: Default value if key not found.

    Returns:
        Secret value or default.
    """
    manager = get_secrets_manager()
    return manager.get(key, default)


def get_required_secret(key: str) -> str:
    """Get a required secret value.

    Args:
        key: Secret key name.

    Returns:
        Secret value.

    Raises:
        ValueError: If secret key not found or empty.
    """
    manager = get_secrets_manager()
    return manager.get_required(key)
