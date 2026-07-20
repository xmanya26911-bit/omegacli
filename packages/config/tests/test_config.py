"""Tests for the Ω OMEGA Configuration System (§396)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from packages.config import (
    AVAILABLE_MODELS,
    ApplicationConfig,
    AIConfig,
    RepositoryConfig,
    SecurityConfig,
    DeveloperConfig,
    OmegaConfig,
)


class TestConfigSections(unittest.TestCase):
    """Test individual config sections."""

    def test_application_defaults(self):
        app = ApplicationConfig()
        self.assertEqual(app.theme, "default-dark")
        self.assertEqual(app.language, "en")
        self.assertEqual(app.appearance, "dark")

    def test_ai_defaults(self):
        ai = AIConfig()
        self.assertEqual(ai.default_model, "deepseek-v4-flash-free")
        self.assertEqual(ai.context_limit_tokens, 128000)
        self.assertTrue(ai.streaming)

    def test_repository_defaults(self):
        repo = RepositoryConfig()
        self.assertTrue(repo.auto_index)
        self.assertTrue(repo.background_sync)

    def test_security_defaults(self):
        sec = SecurityConfig()
        self.assertEqual(sec.session_timeout_minutes, 60)

    def test_developer_defaults(self):
        dev = DeveloperConfig()
        self.assertFalse(dev.debug_mode)
        self.assertEqual(dev.log_level, "INFO")


class TestOmegaConfig(unittest.TestCase):
    """Test the master OmegaConfig class."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.config_path = self.tmpdir / "config.json"
        self.secrets_path = self.tmpdir / ".secrets.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_default(self):
        cfg = OmegaConfig.load(
            config_file=self.config_path,
            secrets_file=self.secrets_path,
        )
        self.assertEqual(cfg.ai.default_model, "deepseek-v4-flash-free")
        self.assertTrue(cfg.is_valid())

    def test_load_from_file(self):
        data = {
            "application": {"theme": "light", "language": "hi"},
            "ai": {"default_model": "nemotron-3-ultra-free"},
        }
        self.config_path.write_text(json.dumps(data), encoding="utf-8")
        cfg = OmegaConfig.load(
            config_file=self.config_path,
            secrets_file=self.secrets_path,
        )
        self.assertEqual(cfg.application.theme, "light")
        self.assertEqual(cfg.application.language, "hi")
        self.assertEqual(cfg.ai.default_model, "nemotron-3-ultra-free")

    def test_load_flat_backward_compat(self):
        """Backward compat: flat keys model/base_url/theme/max_tokens."""
        data = {
            "model": "north-mini-code-free",
            "theme": "solarized",
            "max_tokens": 64000,
        }
        self.config_path.write_text(json.dumps(data), encoding="utf-8")
        cfg = OmegaConfig.load(
            config_file=self.config_path,
            secrets_file=self.secrets_path,
        )
        self.assertEqual(cfg.ai.default_model, "north-mini-code-free")
        self.assertEqual(cfg.application.theme, "solarized")
        self.assertEqual(cfg.ai.context_limit_tokens, 64000)

    def test_env_override(self):
        os.environ["OMEGA_MODEL"] = "mimo-v2.5-free"
        os.environ["OMEGA_THEME"] = "light"
        cfg = OmegaConfig.load(
            config_file=self.config_path,
            secrets_file=self.secrets_path,
        )
        self.assertEqual(cfg.ai.default_model, "mimo-v2.5-free")
        self.assertEqual(cfg.application.theme, "light")
        del os.environ["OMEGA_MODEL"]
        del os.environ["OMEGA_THEME"]

    def test_save_and_reload(self):
        cfg = OmegaConfig.load(
            config_file=self.config_path,
            secrets_file=self.secrets_path,
        )
        cfg.ai.default_model = "nemotron-3-ultra-free"
        cfg.application.theme = "light"
        cfg.save()
        cfg2 = OmegaConfig.load(
            config_file=self.config_path,
            secrets_file=self.secrets_path,
        )
        self.assertEqual(cfg2.ai.default_model, "nemotron-3-ultra-free")
        self.assertEqual(cfg2.application.theme, "light")

    def test_secrets_storage(self):
        test_key = "X_TEST_API_KEY_12345"
        cfg = OmegaConfig.load(
            config_file=self.config_path,
            secrets_file=self.secrets_path,
        )
        cfg.save_secret("api_key", test_key)
        self.assertEqual(cfg._api_key, test_key)
        self.assertTrue(self.secrets_path.exists())
        cfg2 = OmegaConfig.load(
            config_file=self.config_path,
            secrets_file=self.secrets_path,
        )
        self.assertEqual(cfg2._api_key, test_key)

    def test_to_dict(self):
        cfg = OmegaConfig.load(
            config_file=self.config_path,
            secrets_file=self.secrets_path,
        )
        d = cfg.to_dict()
        self.assertIn("application", d)
        self.assertIn("ai", d)
        self.assertIn("repository", d)
        self.assertIn("security", d)
        self.assertIn("developer", d)


class TestValidation(unittest.TestCase):
    """Test configuration validation."""

    def test_valid_config(self):
        cfg = OmegaConfig()
        self.assertTrue(cfg.is_valid())
        self.assertEqual(cfg.validate(), [])

    def test_invalid_model(self):
        cfg = OmegaConfig()
        cfg.ai.default_model = "nonexistent-model"
        issues = cfg.validate()
        self.assertTrue(any("Unknown model" in i for i in issues))

    def test_invalid_base_url(self):
        cfg = OmegaConfig()
        cfg.ai.base_url = "not-a-url"
        issues = cfg.validate()
        self.assertTrue(any("Invalid base URL" in i for i in issues))

    def test_invalid_context_limit(self):
        cfg = OmegaConfig()
        cfg.ai.context_limit_tokens = 50
        issues = cfg.validate()
        self.assertTrue(any("context_limit_tokens" in i for i in issues))

    def test_invalid_appearance(self):
        cfg = OmegaConfig()
        cfg.application.appearance = "neon"
        issues = cfg.validate()
        self.assertTrue(any("appearance" in i for i in issues))


class TestDeadModelFallback(unittest.TestCase):
    """Test dead model auto-fallback."""

    def test_dead_model_in_file(self):
        tmpdir = Path(tempfile.mkdtemp())
        config_path = tmpdir / "config.json"
        config_path.write_text(json.dumps({"model": "qwen3.6-plus-free"}), encoding="utf-8")
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = OmegaConfig.load(config_file=config_path, secrets_file=tmpdir / ".secrets.json")
            self.assertEqual(cfg.ai.default_model, "deepseek-v4-flash-free")
            self.assertTrue(any("no longer supported" in str(msg.message) for msg in w))
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
