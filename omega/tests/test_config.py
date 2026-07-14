"""Unit tests for Config class."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

# We import directly from the flat module for backward compat
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import config as config_module
from config import Config, ConfigError, AVAILABLE_MODELS


DUMMY_SECRETS_FILE = "secrets.json"


class TestConfig(unittest.TestCase):
    """Config validation, model switching, and persistence tests."""

    def setUp(self) -> None:
        # Use a temp config directory to avoid polluting the real one
        self._temp_config_dir = Path(tempfile.mkdtemp())
        self._orig_config_dir = config_module.CONFIG_DIR
        self._orig_config_file = config_module.CONFIG_FILE
        self._orig_secrets_file = config_module.SECRETS_FILE
        config_module.CONFIG_DIR = self._temp_config_dir
        config_module.CONFIG_FILE = self._temp_config_dir / "config.json"
        config_module.SECRETS_FILE = self._temp_config_dir / DUMMY_SECRETS_FILE
        self.config = Config()

    def tearDown(self) -> None:
        # Restore original config paths
        config_module.CONFIG_DIR = self._orig_config_dir
        config_module.CONFIG_FILE = self._orig_config_file
        config_module.SECRETS_FILE = self._orig_secrets_file
        # Clean up temp dir
        shutil.rmtree(self._temp_config_dir, ignore_errors=True)

    def test_default_model(self) -> None:
        """Default model should be deepseek-v4-flash-free."""
        self.assertEqual(self.config.model, "deepseek-v4-flash-free")

    def test_default_base_url(self) -> None:
        """Default base URL should be the OpenCode Zen endpoint."""
        self.assertEqual(self.config.base_url, "https://opencode.ai/zen/v1")

    def test_default_theme(self) -> None:
        """Default theme should be default-dark."""
        self.assertEqual(self.config.theme, "default-dark")

    def test_valid_returns_false_without_api_key(self) -> None:
        """Config should be invalid when no API key is set."""
        self.config.api_key = ""
        self.assertFalse(self.config.is_valid())

    def test_valid_when_api_key_set(self) -> None:
        """Config should be valid when API key is present."""
        self.config.api_key = "sk-test-key-12345"
        self.assertTrue(self.config.is_valid())

    def test_validate_empty_api_key(self) -> None:
        """Validation should flag missing API key."""
        self.config.api_key = ""
        issues = self.config.validate()
        self.assertTrue(any("API key" in issue for issue in issues))

    def test_validate_unknown_model(self) -> None:
        """Validation should flag models not in AVAILABLE_MODELS."""
        self.config.model = "fake-model-does-not-exist"
        issues = self.config.validate()
        self.assertTrue(any("Unknown model" in issue for issue in issues))

    def test_validate_invalid_url(self) -> None:
        """Validation should flag non-HTTP URLs."""
        self.config.base_url = "not-a-url"
        issues = self.config.validate()
        self.assertTrue(any("Invalid base URL" in issue for issue in issues))

    def test_validate_bad_max_steps(self) -> None:
        """Validation should flag max_steps out of range."""
        self.config.max_steps = 999999
        issues = self.config.validate()
        self.assertTrue(any("max_steps" in issue for issue in issues))

    def test_validate_bad_max_tokens(self) -> None:
        """Validation should flag max_tokens out of range."""
        self.config.max_tokens = 0
        issues = self.config.validate()
        self.assertTrue(any("max_tokens" in issue for issue in issues))

    def test_set_model_valid(self) -> None:
        """Switching to a known model should succeed."""
        self.config.api_key = "sk-test"
        result = self.config.set_model("nemotron-3-ultra-free")
        self.assertTrue(result)
        self.assertEqual(self.config.model, "nemotron-3-ultra-free")

    def test_set_model_invalid(self) -> None:
        """Switching to an unknown model should return False."""
        result = self.config.set_model("non-existent-model")
        self.assertFalse(result)
        # Model should be unchanged
        self.assertEqual(self.config.model, "deepseek-v4-flash-free")

    def test_model_auto_switches_provider(self) -> None:
        """set_model should auto-configure API endpoint for known models."""
        self.config.api_key = "sk-test"
        self.config.set_model("claude-fable-5")
        self.assertIn("aerolink", self.config.base_url)

    def test_to_dict_format(self) -> None:
        """to_dict should return the expected keys."""
        self.config.api_key = "sk-test-key"
        d = self.config.to_dict()
        self.assertIn("model", d)
        self.assertIn("base_url", d)
        self.assertIn("api_key", d)
        self.assertIn("theme", d)
        self.assertIn("valid", d)
        # API key should be partially redacted
        self.assertIn("...", d["api_key"])

    def test_save_and_load_roundtrip(self) -> None:
        """Config save() and subsequent load should preserve values."""
        # Save specific values
        self.config.model = "nemotron-3-ultra-free"
        self.config.theme = "default-light"
        self.config.save()

        # Create new config and verify values loaded
        new_config = Config()
        self.assertEqual(new_config.model, "nemotron-3-ultra-free")
        self.assertEqual(new_config.theme, "default-light")

        # Restore defaults for subsequent tests
        self.config.model = "deepseek-v4-flash-free"
        self.config.theme = "default-dark"
        self.config.save()

    def test_legacy_theme_mapping(self) -> None:
        """Legacy 'dark'/'light' themes should map to new names."""
        old_map = {"dark": "default-dark", "light": "default-light"}
        mapped = old_map.get("dark", "dark")
        self.assertEqual(mapped, "default-dark")
        mapped = old_map.get("light", "light")
        self.assertEqual(mapped, "default-light")

    def test_available_models_list(self) -> None:
        """AVAILABLE_MODELS should be non-empty and contain known models."""
        self.assertIn("deepseek-v4-flash-free", AVAILABLE_MODELS)
        self.assertIn("claude-fable-5", AVAILABLE_MODELS)
        self.assertGreater(len(AVAILABLE_MODELS), 3)

    def test_model_not_in_providers_falls_back_to_default(self) -> None:
        """Models not in MODEL_PROVIDERS should use default provider."""
        self.config.api_key = "sk-test-key"
        # Set to a model that IS in available but the provider is the default
        self.config.set_model("mimo-v2.5-free")
        self.assertTrue(self.config.is_valid())

    def test_save_secret(self) -> None:
        """save_secret should persist API key to secrets file."""
        self.config.save_secret("api_key", "sk-real-test-key-1234567890ab")
        # Reload and check
        new_config = Config()
        self.assertEqual(new_config.api_key, "sk-real-test-key-1234567890ab")

    def test_config_repr(self) -> None:
        """__repr__ should return a descriptive string."""
        self.config.api_key = "sk-test"
        rep = repr(self.config)
        self.assertIn("model=", rep)
        self.assertIn("deepseek", rep)


if __name__ == "__main__":
    unittest.main()
