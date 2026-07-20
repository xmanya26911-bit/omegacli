"""
Ω OMEGA Agent Runtime (§384)

Core LLM routing, streaming, tool execution, and context management.
Reusable across CLI, web, and desktop apps.

Current implementation lives in apps/cli/omega/core/.
This package defines the public API boundary.
"""

from __future__ import annotations

import os
import sys

# Ensure apps/cli is on the path for re-exports
_pkg = os.path.dirname(__file__)       # packages/agent_runtime/
_root = os.path.dirname(_pkg)           # packages/
_root = os.path.dirname(_root)          # <repo_root>
_cli = os.path.join(_root, "apps", "cli")
if os.path.isdir(_cli) and _cli not in sys.path:
    sys.path.insert(0, _root)
    sys.path.insert(0, _cli)

from typing import Any, AsyncIterator, Optional

# Re-export from CLI core implementation
from apps.cli.omega.core import (
    # Exception hierarchy
    OmegaError,
    ToolExecutionError,
    ConfigurationError,
    ProviderError,
    # State types
    ErrorLevel,
    ToolResult,
    Permission,
)

# Config types from packages/config (Phase 1 structured config)
from packages.config import (
    OmegaConfig,
    ApplicationConfig,
    AIConfig,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
)


__all__ = [
    "OmegaError",
    "ToolExecutionError",
    "ConfigurationError",
    "ProviderError",
    "ErrorLevel",
    "ToolResult",
    "Permission",
    "AVAILABLE_MODELS",
    "DEFAULT_MODEL",
    "OmegaConfig",
    "ApplicationConfig",
    "AIConfig",
]
