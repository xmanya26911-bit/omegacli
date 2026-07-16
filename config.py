#!/usr/bin/env python3
"""
OMEGA Configuration — re-exported from omega.core.config for backward compatibility.

This module is maintained for backward compatibility.
New code should import from omega.core directly:

    from omega.core import Config
"""
from __future__ import annotations

# Re-export everything from the canonical location
from omega.core.config import (  # noqa: F401
    AVAILABLE_MODELS,
    CONFIG_DIR,
    CONFIG_FILE,
    Config,
    ConfigError,
    DEAD_MODELS,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    MODEL_PROVIDERS,
    SECRETS_FILE,
)
