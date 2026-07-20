"""
Ω OMEGA AI Runtime Service — Model routing, provider health, failover (§384).

Routes requests to the optimal AI provider based on model, availability,
and latency. Handles failover, retry, and streaming.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from packages.agent_runtime import AVAILABLE_MODELS


# ── Types ──────────────────────────────────────────────────────────────────

class ProviderStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ProviderHealth:
    """Health state for a single provider."""
    status: ProviderStatus = ProviderStatus.HEALTHY
    last_check: float = 0.0
    response_time_ms: float = 0.0
    error_count: int = 0
    consecutive_failures: int = 0


@dataclass
class ModelRoute:
    """Routing config for a model."""
    model_id: str
    provider: str
    priority: int = 0
    fallbacks: list[str] = field(default_factory=list)


# ── Provider Registry ──────────────────────────────────────────────────────

class ProviderRegistry:
    """Registry of AI providers with health monitoring."""

    def __init__(self):
        self._providers: dict[str, dict[str, Any]] = {}
        self._health: dict[str, ProviderHealth] = {}
        self._routes: dict[str, ModelRoute] = {}

    def register_provider(self, name: str, **kwargs) -> None:
        """Register an AI provider."""
        self._providers[name] = kwargs
        self._health[name] = ProviderHealth()

    def register_model(self, model_id: str, provider: str, priority: int = 0,
                       fallbacks: Optional[list[str]] = None) -> None:
        """Register a model with its provider and fallbacks."""
        self._routes[model_id] = ModelRoute(
            model_id=model_id,
            provider=provider,
            priority=priority,
            fallbacks=fallbacks or [],
        )

    def get_provider(self, name: str) -> Optional[dict[str, Any]]:
        return self._providers.get(name)

    def get_route(self, model_id: str) -> Optional[ModelRoute]:
        return self._routes.get(model_id)

    def get_health(self, provider: str) -> ProviderHealth:
        return self._health.get(provider, ProviderHealth(status=ProviderStatus.UNAVAILABLE))

    def all_healthy(self) -> list[str]:
        """Return names of all healthy providers."""
        return [
            name for name, health in self._health.items()
            if health.status == ProviderStatus.HEALTHY
        ]

    @property
    def providers(self) -> dict[str, dict[str, Any]]:
        return dict(self._providers)

    @property
    def routes(self) -> dict[str, ModelRoute]:
        return dict(self._routes)


# ── Health Checker ─────────────────────────────────────────────────────────

class HealthChecker:
    """Periodically checks provider health."""

    def __init__(self, registry: ProviderRegistry, interval: float = 60.0):
        self.registry = registry
        self.interval = interval
        self._task: Optional[asyncio.Task] = None

    async def check_provider(self, name: str, config: dict[str, Any]) -> ProviderHealth:
        """Check a single provider's health by hitting its /v1/models endpoint."""
        start = time.time()
        health = self.registry._health.get(name, ProviderHealth())

        # Simulated health check — real implementation calls provider API
        try:
            # TODO: actual HTTP health check against provider base_url
            await asyncio.sleep(0.1)
            health.status = ProviderStatus.HEALTHY
            health.response_time_ms = (time.time() - start) * 1000
            health.consecutive_failures = 0
        except Exception:
            health.consecutive_failures += 1
            if health.consecutive_failures >= 3:
                health.status = ProviderStatus.UNAVAILABLE
            else:
                health.status = ProviderStatus.DEGRADED
            health.response_time_ms = (time.time() - start) * 1000

        health.last_check = time.time()
        self.registry._health[name] = health
        return health

    async def check_all(self) -> dict[str, ProviderHealth]:
        """Check all registered providers."""
        results = {}
        for name, config in self.registry._providers.items():
            results[name] = await self.check_provider(name, config)
        return results

    async def run_loop(self):
        """Continuous health check loop."""
        while True:
            await self.check_all()
            await asyncio.sleep(self.interval)


# ── Model Router ───────────────────────────────────────────────────────────

class ModelRouter:
    """Routes requests to the best available provider for a model."""

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def resolve(self, model_id: str) -> Optional[str]:
        """Resolve a model to its best available provider."""
        route = self.registry.get_route(model_id)
        if not route:
            return None

        # Primary provider
        health = self.registry.get_health(route.provider)
        if health.status == ProviderStatus.HEALTHY:
            return route.provider

        # Try fallbacks in order
        for fallback in route.fallbacks:
            health = self.registry.get_health(fallback)
            if health.status == ProviderStatus.HEALTHY:
                return fallback

        # Last resort: any healthy provider
        healthy = self.registry.all_healthy()
        return healthy[0] if healthy else None

    def get_available_models(self) -> list[dict[str, Any]]:
        """List models with available providers."""
        results = []
        for model_id, route in self.registry.routes.items():
            provider = self.resolve(model_id)
            results.append({
                "id": model_id,
                "provider": route.provider,
                "available": provider is not None,
                "resolved_provider": provider,
            })
        return results


# ── Default Registry ───────────────────────────────────────────────────────

def create_default_registry() -> ProviderRegistry:
    """Create registry pre-loaded with available models."""
    from apps.cli.omega.core.config import MODEL_PROVIDERS

    registry = ProviderRegistry()

    # Register providers
    registry.register_provider("opencode", base_url="opencode.ai/zen/v1")
    registry.register_provider("openrouter", base_url="openrouter.ai/api/v1")
    registry.register_provider("groq", base_url="api.groq.com/openai/v1")

    # Register models from MODEL_PROVIDERS
    for model_id, config in MODEL_PROVIDERS.items():
        provider = config.get("provider", "opencode")
        priority = 1 if provider == "opencode" else 0
        registry.register_model(
            model_id=model_id,
            provider=provider,
            priority=priority,
            fallbacks=["openrouter", "groq"],
        )

    return registry


# Singleton
_default_registry: Optional[ProviderRegistry] = None


def get_default_registry() -> ProviderRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = create_default_registry()
    return _default_registry


def get_default_router() -> ModelRouter:
    return ModelRouter(get_default_registry())
