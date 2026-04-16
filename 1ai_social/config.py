import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv


class Config:
    """Configuration loader for 1ai-social application."""

    REQUIRED_FIELDS = [
        "postbridge_api_key",
        "nvidia_api_key",
        "byteplus_api_key",
        "groq_api_key",
        "database_url",
        "audit_secret_key",
    ]

    def __init__(self, config_dict: dict):
        self._config = config_dict
        self._validate()

    def _validate(self):
        """Validate that all required fields are present."""
        missing = []
        for field in self.REQUIRED_FIELDS:
            value = self._get_env_value(self._config.get(field))
            if not value:
                missing.append(field)

        if missing:
            raise ValueError(
                f"Missing required configuration fields: {', '.join(missing)}. "
                "Set them via environment variables or .env file."
            )

    def _get_env_value(self, value: str) -> Optional[str]:
        """Extract environment variable value from ${VAR} syntax."""
        if not isinstance(value, str):
            return value

        if value.startswith("${") and value.endswith("}"):
            var_name = value[2:-1]
            if ":-" in var_name:
                var_name, default = var_name.split(":-", 1)
                return os.getenv(var_name, default)
            return os.getenv(var_name)

        return value

    def get(self, key: str, default=None):
        """Get configuration value by key, resolving environment variables."""
        value = self._config.get(key, default)
        return self._get_env_value(value)

    def __getattr__(self, name: str):
        """Allow attribute-style access to config values."""
        if name.startswith("_"):
            return super().__getattribute__(name)

        value = self._config.get(name)
        if value is None:
            raise AttributeError(f"Configuration key '{name}' not found")

        return self._get_env_value(value)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Config":
        """Load configuration from YAML file and environment variables.

        Args:
            config_path: Path to config.yaml. Defaults to project root.

        Returns:
            Config instance with validated configuration.

        Raises:
            ValueError: If required fields are missing.
            FileNotFoundError: If config file not found.
        """
        load_dotenv()

        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f) or {}

        return cls(config_dict)
