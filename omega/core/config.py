#!/usr/bin/env python3
"""
OMEGA Configuration — securely managed, validated, environment-aware.

Provides Config class with:
    - Layered loading: file → secrets → environment variables
    - Provider auto-switching when model changes
    - Full validation on access
    - Type-safe accessors
    - Secure secrets storage (separate from main config)
"""

from __future__ import annotations

import contextlib
import json
import os
import warnings
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_DIR = Path.home() / ".omega"
CONFIG_FILE = CONFIG_DIR / "config.json"
SECRETS_FILE = CONFIG_DIR / ".secrets.json"

DEFAULT_BASE_URL = "https://opencode.ai/zen/v1"
DEFAULT_MODEL = "deepseek-v4-flash-free"

AVAILABLE_MODELS: list[str] = [
    "mimo-v2.5-free",
    "nemotron-3-ultra-free",
    "north-mini-code-free",
    "deepseek-v4-flash-free",
    # Claude models via Aerolink
    "claude-fable-5",
]

# Models that exist in AVAILABLE_MODELS but are confirmed dead/non-functional
# on the current API endpoint. Config will auto-fallback to DEFAULT_MODEL.
DEAD_MODELS: frozenset[str] = frozenset({
    "qwen3.6-plus-free",
})

MODEL_PROVIDERS: dict[str, dict[str, str]] = {
    "default": {
        "base_url": DEFAULT_BASE_URL,
        "api_key": "",  # Must be set via env var OMEGA_API_KEY or secrets file
    },
    "claude-fable-5": {
        "base_url": "https://capi.aerolink.lat",
        "api_key": "",  # Must be set via env var or secrets file
    },
}

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ConfigError(Exception):
    """Configuration error — invalid, missing, or corrupted config."""



# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class Config:
    """Central configuration manager for OMEGA.

    Loads configuration from three sources (in order of precedence):
        1. Environment variables (highest priority)
        2. Secrets file (~/.omega/.secrets.json)
        3. Config file (~/.omega/config.json)
        4. Hardcoded defaults (lowest priority)

    Usage:
        cfg = Config()
        print(cfg.model)      # -> "deepseek-v4-flash-free"
        cfg.set_model("claude-fable-5")  # auto-switches API provider
        issues = cfg.validate()
    """

    # Expose available models as class attribute for external reference
    AVAILABLE_MODELS: list[str] = AVAILABLE_MODELS

    def __init__(self) -> None:
        # Core connection settings
        self.api_key: str = ""
        self.base_url: str = DEFAULT_BASE_URL
        self.model: str = DEFAULT_MODEL

        # UI / UX
        self.theme: str = "default-dark"

        # Execution limits
        self.max_steps: int = 99999
        self.max_tokens: int = 128000

        # Feature toggles
        self.enable_batch_operations: bool = True
        self.enable_similar_file_detection: bool = True
        self.enable_predictive_analytics: bool = True
        self.enable_advanced_encoding_detection: bool = True

        # Size limits
        self.max_batch_file_size: int = 10 * 1024 * 1024  # 10 MB
        self.max_individual_file_size: int = 10 * 1024 * 1024  # 10 MB

        self._load()

    # ---- Loading ----

    def _load(self) -> None:
        """Load config from file, secrets, and environment variables."""
        self._load_from_file()
        self._load_from_secrets()
        self._apply_environment_overrides()
        self._resolve_provider()

    def _load_from_file(self) -> None:
        """Load non-sensitive config from ~/.omega/config.json."""
        if not CONFIG_FILE.exists():
            return
        try:
            data: dict[str, Any] = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            self.base_url = data.get("base_url", self.base_url)
            self.model = data.get("model", self.model)
            # Auto-fallback from dead models
            if self.model in DEAD_MODELS:
                warnings.warn(
                    f"Model '{self.model}' is no longer supported on this API. "
                    f"Falling back to '{DEFAULT_MODEL}'. "
                    f"Use /model to switch to a working model."
                )
                self.model = DEFAULT_MODEL
            self.theme = data.get("theme", self.theme)
            self.max_steps = data.get("max_steps", self.max_steps)
            self.max_tokens = data.get("max_tokens", self.max_tokens)
        except (json.JSONDecodeError, OSError) as e:
            raise ConfigError(f"Failed to load config from {CONFIG_FILE}: {e}")

    # ---- Known placeholder keys (set by security layers, not real credentials) ----
    _PLACEHOLDER_KEYS: frozenset[str] = frozenset({
        "sk-saved-secret-key",
    })

    @staticmethod
    def _is_placeholder_key(key: str) -> bool:
        """Return True if key looks like a placeholder rather than a real credential."""
        if not key:
            return True
        if key in Config._PLACEHOLDER_KEYS:
            return True
        # Very short sk- keys (< 24 chars) are almost certainly placeholders
        if key.startswith("sk-") and len(key) < 24:
            return True
        return False

    def _load_from_secrets(self) -> None:
        """Load API key from separate secrets file (not committed to git)."""
        if not SECRETS_FILE.exists():
            return
        try:
            secrets: dict[str, Any] = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
            raw_key = secrets.get("api_key", self.api_key)
            self.api_key = "" if self._is_placeholder_key(raw_key) else raw_key
        except (json.JSONDecodeError, OSError):
            warnings.warn(f"Could not read secrets file: {SECRETS_FILE}")

    def _apply_environment_overrides(self) -> None:
        """Environment variables override everything else."""
        env_api_key = os.environ.get("OMEGA_API_KEY")
        if env_api_key and not self._is_placeholder_key(env_api_key):
            self.api_key = env_api_key

        env_base_url = os.environ.get("OMEGA_BASE_URL")
        if env_base_url:
            self.base_url = env_base_url

        env_model = os.environ.get("OMEGA_MODEL")
        if env_model:
            self.model = env_model

        env_theme = os.environ.get("OMEGA_THEME")
        if env_theme:
            self.theme = env_theme

    def _resolve_provider(self) -> None:
        """Auto-configure provider for known models unless env vars override."""
        env_api_key = os.environ.get("OMEGA_API_KEY")
        env_base_url = os.environ.get("OMEGA_BASE_URL")

        if not env_base_url and self.model in MODEL_PROVIDERS:
            provider = MODEL_PROVIDERS[self.model]
            self.base_url = provider.get("base_url", self.base_url)
            if not env_api_key and provider.get("api_key"):
                self.api_key = provider["api_key"]

    # ---- Validation ----

    def validate(self) -> list[str]:
        """Validate configuration and return list of issues (empty = all good).

        Checks:
            - API key is set
            - Model is in the known list
            - Base URL is well-formed
            - Numeric limits are in range
        """
        issues: list[str] = []

        if not self.api_key:
            issues.append(
                "No API key configured. Set OMEGA_API_KEY environment variable "
                "or run: omega --configure"
            )

        if self.model not in AVAILABLE_MODELS:
            issues.append(
                f"Unknown model '{self.model}'. "
                f"Available: {', '.join(AVAILABLE_MODELS)}"
            )

        if not self.base_url.startswith(("http://", "https://")):
            issues.append(f"Invalid base URL: {self.base_url}")

        if self.max_steps < 1 or self.max_steps > 200000:
            issues.append(
                f"max_steps must be between 1 and 200000, got {self.max_steps}"
            )

        if self.max_tokens < 1000 or self.max_tokens > 128000:
            issues.append(
                f"max_tokens must be between 1000 and 128000, got {self.max_tokens}"
            )

        return issues

    def is_valid(self) -> bool:
        """Quick validity check — returns True if no configuration issues."""
        return len(self.validate()) == 0

    # ---- Model Switching ----

    def set_model(self, model: str) -> bool:
        """Switch to a different model, auto-configuring the API provider.

        Args:
            model: Name of the model (must be in AVAILABLE_MODELS).

        Returns:
            True if the switch succeeded, False if model is unknown.
        """
        if model not in AVAILABLE_MODELS:
            return False

        self.model = model

        # Auto-switch API provider if this model has a specific provider
        if model in MODEL_PROVIDERS:
            provider = MODEL_PROVIDERS[model]
            self.base_url = provider.get("base_url", self.base_url)
            if not os.environ.get("OMEGA_API_KEY") and provider.get("api_key"):
                self.api_key = provider["api_key"]
        else:
            # Fall back to default provider
            provider = MODEL_PROVIDERS.get("default", {})
            if not os.environ.get("OMEGA_BASE_URL"):
                self.base_url = provider.get("base_url", self.base_url)
            if not os.environ.get("OMEGA_API_KEY") and provider.get("api_key"):
                self.api_key = provider["api_key"]

        self.save()
        return True

    # ---- Persistence ----

    def save(self) -> None:
        """Save non-sensitive config to ~/.omega/config.json."""
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

    def save_secret(self, key: str, value: str) -> None:
        """Save a secret (like API key) to the protected secrets file.

        Args:
            key: Secret name (e.g., 'api_key').
            value: Secret value.
        """
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        secrets: dict[str, Any] = {}
        if SECRETS_FILE.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                secrets = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))
        secrets[key] = value
        SECRETS_FILE.write_text(json.dumps(secrets, indent=2), encoding="utf-8")

        if key == "api_key":
            self.api_key = value

    # ---- Serialization ----

    def to_dict(self) -> dict[str, Any]:
        """Export current configuration as a dictionary (key values redacted)."""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "api_key": self.api_key[:8] + "..." if self.api_key else "(not set)",
            "theme": self.theme,
            "max_steps": self.max_steps,
            "max_tokens": self.max_tokens,
            "valid": self.is_valid(),
        }

    def __repr__(self) -> str:
        return (
            f"Config(model={self.model}, base_url={self.base_url}, "
            f"theme={self.theme}, valid={self.is_valid()})"
        )
