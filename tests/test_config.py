"""Tests for Config loader."""

import sys
import os
import tempfile
import importlib
from pathlib import Path

config_module = importlib.import_module("1ai_social.config")
Config = config_module.Config


class TestConfigInit:
    """Test Config initialization."""

    def test_config_with_valid_dict(self):
        """Test creating config with all required fields."""
        config_dict = {
            "postbridge_api_key": "test_key",
            "nvidia_api_key": "test_key",
            "byteplus_api_key": "test_key",
            "groq_api_key": "test_key",
            "database_url": "sqlite:///test.db",
        }
        config = Config(config_dict)
        assert config is not None

    def test_config_missing_required_field(self):
        """Test config raises error when required field missing."""
        config_dict = {
            "postbridge_api_key": "test_key",
            "nvidia_api_key": "test_key",
        }
        try:
            Config(config_dict)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Missing required configuration fields" in str(e)

    def test_config_get_method(self):
        """Test config.get() method."""
        config_dict = {
            "postbridge_api_key": "test_key",
            "nvidia_api_key": "test_key",
            "byteplus_api_key": "test_key",
            "groq_api_key": "test_key",
            "database_url": "sqlite:///test.db",
            "custom_key": "custom_value",
        }
        config = Config(config_dict)
        assert config.get("custom_key") == "custom_value"
        assert config.get("nonexistent", "default") == "default"

    def test_config_attribute_access(self):
        """Test config attribute-style access."""
        config_dict = {
            "postbridge_api_key": "test_key",
            "nvidia_api_key": "test_key",
            "byteplus_api_key": "test_key",
            "groq_api_key": "test_key",
            "database_url": "sqlite:///test.db",
            "custom_key": "custom_value",
        }
        config = Config(config_dict)
        assert config.custom_key == "custom_value"

    def test_config_attribute_not_found(self):
        """Test accessing nonexistent attribute raises error."""
        config_dict = {
            "postbridge_api_key": "test_key",
            "nvidia_api_key": "test_key",
            "byteplus_api_key": "test_key",
            "groq_api_key": "test_key",
            "database_url": "sqlite:///test.db",
        }
        config = Config(config_dict)
        try:
            _ = config.nonexistent_key
            assert False, "Should raise AttributeError"
        except AttributeError as e:
            assert "Configuration key 'nonexistent_key' not found" in str(e)


class TestConfigEnvVars:
    """Test Config environment variable resolution."""

    def test_config_env_var_syntax(self):
        """Test ${VAR} syntax for environment variables."""
        os.environ["TEST_API_KEY"] = "env_value"
        config_dict = {
            "postbridge_api_key": "${TEST_API_KEY}",
            "nvidia_api_key": "test_key",
            "byteplus_api_key": "test_key",
            "groq_api_key": "test_key",
            "database_url": "sqlite:///test.db",
        }
        config = Config(config_dict)
        assert config.postbridge_api_key == "env_value"

    def test_config_env_var_with_default(self):
        """Test ${VAR:-default} syntax."""
        if "NONEXISTENT_VAR" in os.environ:
            del os.environ["NONEXISTENT_VAR"]
        config_dict = {
            "postbridge_api_key": "${NONEXISTENT_VAR:-fallback_value}",
            "nvidia_api_key": "test_key",
            "byteplus_api_key": "test_key",
            "groq_api_key": "test_key",
            "database_url": "sqlite:///test.db",
        }
        config = Config(config_dict)
        assert config.postbridge_api_key == "fallback_value"

    def test_config_env_var_missing_no_default(self):
        """Test missing env var without default returns None."""
        if "MISSING_VAR" in os.environ:
            del os.environ["MISSING_VAR"]
        config_dict = {
            "postbridge_api_key": "${MISSING_VAR}",
            "nvidia_api_key": "test_key",
            "byteplus_api_key": "test_key",
            "groq_api_key": "test_key",
            "database_url": "sqlite:///test.db",
        }
        try:
            Config(config_dict)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Missing required configuration fields" in str(e)


class TestConfigLoad:
    """Test Config.load() classmethod."""

    def test_config_load_from_yaml(self):
        """Test loading config from YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
postbridge_api_key: yaml_key
nvidia_api_key: yaml_nvidia
byteplus_api_key: yaml_byteplus
groq_api_key: yaml_groq
database_url: sqlite:///test.db
""")
            f.flush()
            config_path = f.name

        try:
            config = Config.load(config_path)
            assert config.postbridge_api_key == "yaml_key"
            assert config.nvidia_api_key == "yaml_nvidia"
        finally:
            os.unlink(config_path)

    def test_config_load_file_not_found(self):
        """Test loading from nonexistent file raises error."""
        try:
            Config.load("/nonexistent/path/config.yaml")
            assert False, "Should raise FileNotFoundError"
        except FileNotFoundError as e:
            assert "Configuration file not found" in str(e)

    def test_config_load_empty_yaml(self):
        """Test loading empty YAML file raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            config_path = f.name

        try:
            Config.load(config_path)
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Missing required configuration fields" in str(e)
        finally:
            os.unlink(config_path)
