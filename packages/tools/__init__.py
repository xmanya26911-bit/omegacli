"""
Ω OMEGA Tool Registry (§384)

Tool definitions, execution, and file operations.
Reusable across CLI and agent contexts.

Current implementation lives in apps/cli/omega/tools/.
"""

from __future__ import annotations

import os
import sys

# Ensure apps/cli is on the path for re-exports
_pkg = os.path.dirname(__file__)       # packages/tools/
_root = os.path.dirname(_pkg)           # packages/
_root = os.path.dirname(_root)          # <repo_root>
_cli = os.path.join(_root, "apps", "cli")
if os.path.isdir(_cli) and _cli not in sys.path:
    sys.path.insert(0, _root)
    sys.path.insert(0, _cli)

from apps.cli.omega.tools.registry import (
    ToolRegistry,
    BaseTool,
    ToolCategory,
    ParamType,
    tool,
)


__all__ = [
    "ToolRegistry",
    "BaseTool",
    "ToolCategory",
    "ParamType",
    "tool",
]
