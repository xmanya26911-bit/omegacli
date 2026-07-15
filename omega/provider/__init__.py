"""Omega Custom Provider — bring your own AI models.

This module provides infrastructure for running your own model-serving
provider, similar to OpenCode Zen. It handles API key generation, rate
limiting, model discovery, and proxy endpoints.

To enable, set OMEGA_USE_CUSTOM_PROVIDER=1 in your environment and
configure your models in the PROVIDER_CONFIG dict below.
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Optional

PROVIDER_CONFIG = {
    "base_url": os.environ.get("OMEGA_PROVIDER_URL", "http://localhost:8080/v1"),
    "api_key": os.environ.get("OMEGA_PROVIDER_KEY", ""),
    "models": [
        "omega-model-1-free",
        "omega-model-2-free",
    ],
    "rate_limit": 60,  # requests per minute
}


@dataclass
class ProviderModel:
    """Represents a model served by this custom provider."""
    id: str
    name: str
    free: bool = True
    context_length: int = 8192
    description: str = ""


DEFAULT_MODELS = [
    ProviderModel(
        id="omega-model-1-free",
        name="Omega Model 1",
        free=True,
        context_length=16384,
        description="Balanced performance model for general tasks",
    ),
    ProviderModel(
        id="omega-model-2-free",
        name="Omega Model 2",
        free=True,
        context_length=32768,
        description="High-context model for complex reasoning",
    ),
]


def get_available_models() -> list[dict]:
    """Return models from config or defaults."""
    models = PROVIDER_CONFIG.get("models", [])
    if models:
        return [{"id": m, "object": "model"} for m in models]
    return [{"id": m.id, "object": "model", "description": m.description}
            for m in DEFAULT_MODELS]


def validate_api_key(key: str) -> bool:
    """Validate an API key against configured provider."""
    expected = PROVIDER_CONFIG["api_key"]
    if not expected:
        return True  # No key configured = allow all
    return key == expected


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: list[float] = []

    def check(self) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        self.requests = [t for t in self.requests if t > cutoff]
        if len(self.requests) >= self.max_requests:
            return False
        self.requests.append(now)
        return True
