"""
Ω OMEGA Configuration System (§396)

Configuration organized into logical sections:
    - Application: Theme, language, timezone, appearance, keyboard
    - AI: Default model, routing rules, memory policy, context limits, streaming
    - Repository: Auto-index, background sync, search settings, branch preferences
    - Security: Session timeout, device trust, API tokens, connected accounts
    - Developer: Debug mode, logs, experimental features, performance overlay

All configuration changes should be validated before being applied.
"""

from __future__ import annotations

import json
import os
import warnings
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_CONFIG_DIR = Path.home() / ".omega"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_SECRETS_FILE = DEFAULT_CONFIG_DIR / ".secrets.json"
DEFAULT_BASE_URL = "https://opencode.ai/zen/v1"
DEFAULT_MODEL = "deepseek-v4-flash-free"

AVAILABLE_MODELS: list[str] = [
    "mimo-v2.5-free",
    "nemotron-3-ultra-free",
    "north-mini-code-free",
    "deepseek-v4-flash-free",
    "claude-fable-5",
    "glm-5.2",
]

DEAD_MODELS: frozenset[str] = frozenset({
    "qwen3.6-plus-free",
    "glm-5.2",
})


# ── Config Sections (§396) ────────────────────────────────────────────────────

@dataclass
class ApplicationConfig:
    """Application-level settings."""
    theme: str = "default-dark"
    language: str = "en"
    timezone: str = "UTC"
    appearance: str = "dark"  # dark | light | auto
    keyboard_preferences: Dict[str, str] = field(default_factory=lambda: {
        "enter_send": "true",
        "vim_mode": "false",
    })


@dataclass
class AIConfig:
    """AI runtime settings."""
    default_model: str = DEFAULT_MODEL
    model_routing_rules: Dict[str, str] = field(default_factory=dict)
    memory_policy: str = "conversation"  # conversation | project | infinite
    context_limit_tokens: int = 128000
    streaming: bool = True
    max_steps: int = 99999
    base_url: str = DEFAULT_BASE_URL
    api_key_placeholder: str = ""  # Real key stored in secrets file


@dataclass
class RepositoryConfig:
    """Repository/git integration settings."""
    auto_index: bool = True
    background_sync: bool = True
    search_settings: Dict[str, Any] = field(default_factory=lambda: {
        "max_results": 50,
        "include_hidden": False,
    })
    branch_preferences: Dict[str, str] = field(default_factory=lambda: {
        "default_branch": "main",
        "auto_fetch": "true",
    })


@dataclass
class SecurityConfig:
    """Security and access control settings."""
    session_timeout_minutes: int = 60
    device_trust: bool = False
    api_tokens: List[str] = field(default_factory=list)
    connected_accounts: Dict[str, str] = field(default_factory=dict)


@dataclass
class DeveloperConfig:
    """Developer-mode settings."""
    debug_mode: bool = False
    log_level: str = "INFO"  # DEBUG | INFO | WARNING | ERROR
    log_file: str = ""
    experimental_features: List[str] = field(default_factory=list)
    performance_overlay: bool = False


# ── Validation Error ──────────────────────────────────────────────────────────

class ConfigValidationError(Exception):
    """Raised when a configuration value fails validation."""
    pass


# ── Section Validators ────────────────────────────────────────────────────────

def validate_application(section: ApplicationConfig) -> list[str]:
    issues: list[str] = []
    if section.appearance not in ("dark", "light", "auto"):
        issues.append(f"Invalid appearance '{section.appearance}' — must be dark/light/auto")
    return issues


def validate_ai(section: AIConfig) -> list[str]:
    issues: list[str] = []
    if section.default_model not in AVAILABLE_MODELS:
        issues.append(f"Unknown model '{section.default_model}' — must be one of {AVAILABLE_MODELS}")
    if not section.base_url.startswith(("http://", "https://")):
        issues.append(f"Invalid base URL: {section.base_url}")
    if section.context_limit_tokens < 1000 or section.context_limit_tokens > 200000:
        issues.append(f"context_limit_tokens must be between 1000 and 200000")
    return issues


def validate_security(section: SecurityConfig) -> list[str]:
    issues: list[str] = []
    if section.session_timeout_minutes < 1:
        issues.append("session_timeout_minutes must be >= 1")
    return issues


def validate_developer(section: DeveloperConfig) -> list[str]:
    issues: list[str] = []
    if section.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        issues.append(f"Invalid log_level '{section.log_level}'")
    return issues


# ── Master Config ─────────────────────────────────────────────────────────────

@dataclass
class OmegaConfig:
    """
    Master configuration container — all sections, validation, and persistence.

    Usage:
        cfg = OmegaConfig.load()
        cfg.ai.default_model = "nemotron-3-ultra-free"
        cfg.save()
    """

    application: ApplicationConfig = field(default_factory=ApplicationConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    repository: RepositoryConfig = field(default_factory=RepositoryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    developer: DeveloperConfig = field(default_factory=DeveloperConfig)

    # Internal
    _config_dir: Path = DEFAULT_CONFIG_DIR
    _config_file: Path = DEFAULT_CONFIG_FILE
    _secrets_file: Path = DEFAULT_SECRETS_FILE
    _api_key: str = ""

    # ── Loading ──────────────────────────────────────────────────────────

    @classmethod
    def load(
        cls,
        config_file: Optional[Path] = None,
        secrets_file: Optional[Path] = None,
    ) -> "OmegaConfig":
        """Load config from file + secrets + env vars (highest precedence)."""
        cfg = cls()
        if config_file:
            cfg._config_file = config_file
        if secrets_file:
            cfg._secrets_file = secrets_file
        cfg._config_dir = cfg._config_file.parent

        cfg._load_from_file()
        cfg._load_from_secrets()
        cfg._apply_env_overrides()
        return cfg

    def _load_from_file(self) -> None:
        if not self._config_file.exists():
            return
        try:
            data: dict[str, Any] = json.loads(self._config_file.read_text(encoding="utf-8"))
            self._apply_dict(data)
        except (json.JSONDecodeError, OSError) as e:
            warnings.warn(f"Failed to load config from {self._config_file}: {e}")

    def _load_from_secrets(self) -> None:
        if not self._secrets_file.exists():
            return
        try:
            secrets: dict[str, Any] = json.loads(self._secrets_file.read_text(encoding="utf-8"))
            raw_key = secrets.get("api_key", "")
            if raw_key and not self._is_placeholder_key(raw_key):
                self._api_key = raw_key
        except (json.JSONDecodeError, OSError):
            warnings.warn(f"Could not read secrets file: {self._secrets_file}")

    @staticmethod
    def _is_placeholder_key(key: str) -> bool:
        if not key:
            return True
        known: frozenset[str] = frozenset({"«redacted:sk-…»"})
        if key in known:
            return True
        if key.startswith("sk-") and len(key) < 24:
            return True
        return False

    def _apply_env_overrides(self) -> None:
        env_api_key = os.environ.get("OMEGA_API_KEY")
        if env_api_key and not self._is_placeholder_key(env_api_key):
            self._api_key = env_api_key

        env_base_url = os.environ.get("OMEGA_BASE_URL")
        if env_base_url:
            self.ai.base_url = env_base_url

        env_model = os.environ.get("OMEGA_MODEL")
        if env_model:
            self.ai.default_model = env_model

        env_theme = os.environ.get("OMEGA_THEME")
        if env_theme:
            self.application.theme = env_theme

        # Dead-model fallback
        if self.ai.default_model in DEAD_MODELS:
            warnings.warn(
                f"Model '{self.ai.default_model}' is no longer supported. "
                f"Falling back to '{DEFAULT_MODEL}'."
            )
            self.ai.default_model = DEFAULT_MODEL

    def _apply_dict(self, data: dict[str, Any]) -> None:
        """Apply a flat or nested dict to the config."""
        # Application section
        if app_data := data.get("application", data.get("theme") is not None):
            if isinstance(app_data, dict):
                for k, v in app_data.items():
                    if hasattr(self.application, k):
                        setattr(self.application, k, v)
            else:
                # Backward compat: flat keys
                if "theme" in data:
                    self.application.theme = data["theme"]
                if "language" in data:
                    self.application.language = data["language"]

        # AI section
        if ai_data := data.get("ai", data.get("model") is not None):
            if isinstance(ai_data, dict):
                for k, v in ai_data.items():
                    if hasattr(self.ai, k):
                        setattr(self.ai, k, v)
            else:
                if "model" in data:
                    self.ai.default_model = data["model"]
                if "base_url" in data:
                    self.ai.base_url = data["base_url"]
                if "max_tokens" in data:
                    self.ai.context_limit_tokens = data["max_tokens"]
                if "max_steps" in data:
                    self.ai.max_steps = data["max_steps"]

    # ── Validation ───────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Validate all sections. Returns list of issues (empty = valid)."""
        issues: list[str] = []
        issues.extend(f"[Application] {e}" for e in validate_application(self.application))
        issues.extend(f"[AI] {e}" for e in validate_ai(self.ai))
        issues.extend(f"[Security] {e}" for e in validate_security(self.security))
        issues.extend(f"[Developer] {e}" for e in validate_developer(self.developer))
        return issues

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    # ── Persistence ──────────────────────────────────────────────────────

    def save(self) -> None:
        """Save to config file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_file.write_text(
            json.dumps(self.to_dict(redact_secrets=False), indent=2),
            encoding="utf-8",
        )

    def save_secret(self, key: str, value: str) -> None:
        """Save a secret (like API key) to the protected secrets file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        secrets: dict[str, Any] = {}
        if self._secrets_file.exists():
            try:
                secrets = json.loads(self._secrets_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        secrets[key] = value
        self._secrets_file.write_text(json.dumps(secrets, indent=2), encoding="utf-8")
        if key == "api_key":
            self._api_key = value

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self, redact_secrets: bool = True) -> dict[str, Any]:
        """Export as nested dict."""
        result = {
            "application": asdict(self.application),
            "ai": asdict(self.ai),
            "repository": asdict(self.repository),
            "security": asdict(self.security),
            "developer": asdict(self.developer),
        }
        if not redact_secrets:
            result["ai"]["api_key"] = self._api_key
        else:
            result["ai"]["api_key_placeholder"] = (
                self._api_key[:8] + "..." if self._api_key else "(not set)"
            )
            del result["ai"]["api_key_placeholder"]
        return result

    def __repr__(self) -> str:
        return (
            f"OmegaConfig(model={self.ai.default_model}, "
            f"theme={self.application.theme}, "
            f"valid={self.is_valid()})"
        )
