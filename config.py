#!/usr/bin/env python3
"""OMEGA Configuration — securely managed, validated, environment-aware."""

import os
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".omega"
CONFIG_FILE = CONFIG_DIR / "config.json"
SECRETS_FILE = CONFIG_DIR / ".secrets.json"

# Default API key
DEFAULT_API_KEY = "sk-oddl0tKQUeYjsoNB367g2896mS2pKWMrL5Zroct6QzoayXTqC1Uj0aQ3nT4LbKo3"
DEFAULT_BASE_URL = "https://opencode.ai/zen/v1"
DEFAULT_MODEL = "deepseek-v4-flash-free"

AVAILABLE_MODELS = [
    "mimo-v2.5-free",
    "qwen3.6-plus-free",
    "nemotron-3-ultra-free",
    "north-mini-code-free",
    "deepseek-v4-flash-free",
    # Claude models via Aerolink
    "claude-fable-5",
]

# Model-to-provider mapping — switching model auto-configures API endpoint + key
MODEL_PROVIDERS = {
    # Default provider (OpenCode)
    "default": {
        "base_url": "https://opencode.ai/zen/v1",
        "api_key": "sk-oddl0tKQUeYjsoNB367g2896mS2pKWMrL5Zroct6QzoayXTqC1Uj0aQ3nT4LbKo3",
    },
    # Claude Fabel 5 via Aerolink
    "claude-fable-5": {
        "base_url": "https://capi.aerolink.lat",
        "api_key": "aero_live_iCm3uoqcr74HHY0TxbYUKaQe9DWHWKwrad8ch8SSLww",
    },
}


class ConfigError(Exception):
    """Configuration error."""
    pass


class Config:
    # Expose available models as class attribute so agent.py can reference them
    AVAILABLE_MODELS = AVAILABLE_MODELS

    def __init__(self):
        self.api_key = DEFAULT_API_KEY
        self.base_url = DEFAULT_BASE_URL
        self.model = DEFAULT_MODEL
        self.theme = "default-dark"
        self.max_steps = 99999
        self.max_tokens = 128000
        # Advanced feature toggles
        self.enable_batch_operations = True
        self.enable_similar_file_detection = True
        self.enable_predictive_analytics = True
        self.enable_advanced_encoding_detection = True
        self.max_batch_file_size = 10 * 1024 * 1024  # 10MB
        self.max_individual_file_size = 10 * 1024 * 1024  # 10MB
        self._load()

    def _load(self):
        """Load config from file, then override with environment variables."""
        # 1. Load from config file
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self.base_url = data.get("base_url", self.base_url)
                self.model = data.get("model", self.model)
                self.theme = data.get("theme", self.theme)
                self.max_steps = data.get("max_steps", self.max_steps)
                self.max_tokens = data.get("max_tokens", self.max_tokens)
            except (json.JSONDecodeError, OSError) as e:
                raise ConfigError(f"Failed to load config: {e}")

        # 2. Load secrets from separate file (not committed to git)
        if SECRETS_FILE.exists():
            try:
                secrets = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
                self.api_key = secrets.get("api_key", self.api_key)
            except (json.JSONDecodeError, OSError):
                pass

        # 3. Environment variables override everything
        env_api_key = os.environ.get("OMEGA_API_KEY")
        if env_api_key:
            self.api_key = env_api_key

        env_base_url = os.environ.get("OMEGA_BASE_URL")
        if env_base_url:
            self.base_url = env_base_url

        # Auto-configure provider for known models (unless OMEGA_BASE_URL overrides)
        if not env_base_url and self.model in MODEL_PROVIDERS:
            provider = MODEL_PROVIDERS[self.model]
            self.base_url = provider["base_url"]
            if not env_api_key:
                self.api_key = provider["api_key"]

        env_model = os.environ.get("OMEGA_MODEL")
        if env_model:
            self.model = env_model

        env_theme = os.environ.get("OMEGA_THEME")
        if env_theme:
            self.theme = env_theme

        # Backward compatibility: map old "dark"/"light" to new theme names
        legacy_map = {"dark": "default-dark", "light": "default-light"}
        if self.theme in legacy_map:
            self.theme = legacy_map[self.theme]

    def save(self):
        """Save non-sensitive config to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(
                {
                    "base_url": self.base_url,
                    "model": self.model,
                    "theme": self.theme,
                    "max_steps": self.max_steps,
                    "max_tokens": self.max_tokens,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def save_secret(self, key, value):
        """Save a secret (like API key) to a separate, more protected file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        secrets = {}
        if SECRETS_FILE.exists():
            try:
                secrets = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        secrets[key] = value
        SECRETS_FILE.write_text(
            json.dumps(secrets, indent=2),
            encoding="utf-8",
        )
        self.api_key = value

    def validate(self):
        """Validate configuration and return list of issues (empty = all good)."""
        issues = []

        if not self.api_key:
            issues.append(
                "No API key configured. Set OMEGA_API_KEY environment variable "
                "or run: omega --configure"
            )

        if self.model not in AVAILABLE_MODELS:
            issues.append(
                f"Unknown model '{self.model}'. Available: {', '.join(AVAILABLE_MODELS)}"
            )

        if not self.base_url.startswith(("http://", "https://")):
            issues.append(f"Invalid base URL: {self.base_url}")

        if self.max_steps < 1 or self.max_steps > 200000:
            issues.append(f"max_steps must be between 1 and 200000, got {self.max_steps}")

        if self.max_tokens < 1000 or self.max_tokens > 128000:
            issues.append(f"max_tokens must be between 1000 and 128000, got {self.max_tokens}")

        return issues

    def set_model(self, model):
        if model in AVAILABLE_MODELS:
            self.model = model
            # Auto-switch API provider if this model has a specific provider
            if model in MODEL_PROVIDERS:
                provider = MODEL_PROVIDERS[model]
                self.base_url = provider["base_url"]
                # Only override API key if OMEGA_API_KEY env var is not set
                if not os.environ.get("OMEGA_API_KEY"):
                    self.api_key = provider["api_key"]
            else:
                # Fall back to default provider
                provider = MODEL_PROVIDERS["default"]
                if not os.environ.get("OMEGA_BASE_URL"):
                    self.base_url = provider["base_url"]
                if not os.environ.get("OMEGA_API_KEY"):
                    self.api_key = provider["api_key"]
            self.save()
            return True
        return False
