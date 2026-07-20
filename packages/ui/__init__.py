"""
Ω OMEGA User Interface (§384)

Shared UI components, layouts, and styling.
CLI-specific TUI lives in apps/cli/omega/ui/.
Web-specific components live in the chat app repo.
"""

from __future__ import annotations

import os
import sys

# Ensure apps/cli is on the path so 'from apps.cli.omega...' works
_ui_pkg = os.path.dirname(__file__)     # packages/ui/
_repo_root = os.path.dirname(_ui_pkg)    # packages/
_repo_root = os.path.dirname(_repo_root) # <repo_root>
_cli_path = os.path.join(_repo_root, "apps", "cli")
if os.path.isdir(_cli_path) and _cli_path not in sys.path:
    sys.path.insert(0, _repo_root)
    sys.path.insert(0, _cli_path)

from apps.cli.omega.ui.themes import get_colors, switch_theme, list_themes


__all__ = [
    "get_colors",
    "switch_theme",
    "list_themes",
]
