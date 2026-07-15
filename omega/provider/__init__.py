"""
OmegaCLI Provider — Custom model provider like OpenCode.

Serves 5 free models, manages API keys, handles authentication,
rate limiting, and model routing.

Usage:
    from omega.provider import OmegaCLIProvider
    provider = OmegaCLIProvider()
    models = provider.list_models()
    response = provider.chat("deepseek-v4-flash-free", messages)
"""

import json
import os
import time
import uuid
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import requests

# ─── 5 Free Models ────────────────────────────────────────────────────────────

FREE_MODELS = [
    {
        "id": "deepseek-v4-flash-free",
        "name": "DeepSeek V4 Flash",
        "context": 16384,
        "description": "Fast, lightweight model for everyday tasks",
    },
    {
        "id": "mimo-v2.5-free",
        "name": "Mimo 2.5",
        "context": 8192,
        "description": "Balanced performance for general purpose",
    },
    {
        "id": "nemotron-3-ultra-free",
        "name": "Nemotron 3 Ultra",
        "context": 65536,
        "description": "Large context window for complex reasoning",
    },
    {
        "id": "north-mini-code-free",
        "name": "North Mini Code",
        "context": 16384,
        "description": "Optimized for code generation and analysis",
    },
    {
        "id": "hy3-free",
        "name": "Hybrid 3",
        "context": 32768,
        "description": "Versatile hybrid model for mixed workloads",
    },
]

# ─── API Key Management ──────────────────────────────────────────────────────

API_KEY_PREFIX = "omg_"


def generate_api_key() -> str:
    """Generate a new OmegaCLI API key."""
    return f"{API_KEY_PREFIX}{secrets.token_hex(24)}"


def validate_api_key(key: str) -> bool:
    """Validate an API key format (actual validation against store in production)."""
    return key.startswith(API_KEY_PREFIX) and len(key) >= 32


@dataclass
class APIKeyRecord:
    """Stores metadata about a generated API key."""
    key: str
    label: str
    created: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_used: str = ""
    requests_count: int = 0
    active: bool = True


class APIKeyStore:
    """Simple in-memory API key store (pluggable to SQLite/DB)."""

    def __init__(self):
        self._keys: dict[str, APIKeyRecord] = {}

    def create_key(self, label: str = "default") -> APIKeyRecord:
        key = generate_api_key()
        record = APIKeyRecord(key=key, label=label)
        self._keys[key] = record
        return record

    def revoke_key(self, key: str) -> bool:
        if key in self._keys:
            self._keys[key].active = False
            return True
        return False

    def validate(self, key: str) -> bool:
        if key not in self._keys:
            return False
        record = self._keys[key]
        if not record.active:
            return False
        record.last_used = datetime.utcnow().isoformat()
        record.requests_count += 1
        return True

    def list_keys(self) -> list[APIKeyRecord]:
        return list(self._keys.values())


# ─── Rate Limiter ────────────────────────────────────────────────────────────


class RateLimiter:
    """Sliding-window rate limiter per API key."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        if key not in self._buckets:
            self._buckets[key] = []
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]
        if len(self._buckets[key]) >= self.max_requests:
            return False
        self._buckets[key].append(now)
        return True


# ─── Provider ────────────────────────────────────────────────────────────────

OPENCODE_BASE_URL = "https://opencode.ai/zen/v1"
DEFAULT_API_KEY = os.environ.get("OMEGA_API_KEY", "")


class OmegaCLIProvider:
    """The OmegaCLI custom model provider.

    Wraps the OpenCode Zen API and serves 5 free models with API key auth.
    Can be extended to self-host models directly.
    """

    def __init__(
        self,
        base_url: str = OPENCODE_BASE_URL,
        api_key: str = DEFAULT_API_KEY,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.key_store = APIKeyStore()
        self.rate_limiter = RateLimiter()
        self._session = requests.Session()

    # ── Models API ───────────────────────────────────────────────────────

    def list_models(self) -> list[dict[str, Any]]:
        """Return the 5 free models available through this provider."""
        return [
            {
                "id": m["id"],
                "object": "model",
                "created": int(time.time()),
                "owned_by": "omegacli",
                "permission": "free",
                "context_length": m["context"],
                "description": m["description"],
            }
            for m in FREE_MODELS
        ]

    def get_model(self, model_id: str) -> dict[str, Any] | None:
        """Get a specific model by ID."""
        for m in FREE_MODELS:
            if m["id"] == model_id:
                return m
        return None

    # ── Chat Completion API ──────────────────────────────────────────────

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        api_key: str | None = None,
        stream: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """Send a chat completion request.

        Args:
            model: Model ID from FREE_MODELS
            messages: List of {"role": ..., "content": ...} dicts
            api_key: Optional API key for auth (uses default if omitted)
            stream: Whether to stream the response
            **kwargs: Additional params (temperature, max_tokens, etc.)
        """
        # Validate model
        if not self.get_model(model):
            raise ValueError(f"Unknown model: {model}. Available: {[m['id'] for m in FREE_MODELS]}")

        # Auth check
        key = api_key or self.api_key
        if key and not self.key_store.validate(key) and key != self.api_key:
            raise PermissionError("Invalid or revoked API key")

        # Rate limit
        if not self.rate_limiter.check(key or "anonymous"):
            raise RuntimeError("Rate limit exceeded. Try again in 60 seconds.")

        # Build request
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs,
        }
        headers = {
            "Authorization": f"Bearer {key or self.api_key}",
            "Content-Type": "application/json",
        }

        if stream:
            return self._chat_stream(payload, headers)
        return self._chat_sync(payload, headers)

    def _chat_sync(
        self, payload: dict, headers: dict
    ) -> dict[str, Any]:
        resp = self._session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    def _chat_stream(self, payload: dict, headers: dict):
        resp = self._session.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                yield line.decode("utf-8")

    # ── Key Management API ───────────────────────────────────────────────

    def create_api_key(self, label: str = "default") -> dict[str, Any]:
        """Generate a new API key for accessing OmegaCLI models."""
        record = self.key_store.create_key(label)
        return {
            "key": record.key,
            "label": record.label,
            "created": record.created,
            "message": "Store this key securely — it won't be shown again",
        }

    def revoke_api_key(self, key: str) -> dict[str, Any]:
        """Revoke an existing API key."""
        success = self.key_store.revoke_key(key)
        return {"success": success, "key": key}

    def list_api_keys(self) -> list[dict[str, Any]]:
        """List all API keys with metadata."""
        return [
            {
                "key": r.key,
                "label": r.label,
                "created": r.created,
                "last_used": r.last_used,
                "requests": r.requests_count,
                "active": r.active,
            }
            for r in self.key_store.list_keys()
        ]
