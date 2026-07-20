"""
Ω OMEGA User Interface (§384)

Shared UI components, layouts, and styling.
CLI-specific TUI lives in apps/cli/omega/ui/.
Web-specific components live in the chat app repo.
"""

from __future__ import annotations

from apps.cli.omega.ui.themes import get_colors, switch_theme, list_themes


__all__ = [
    "get_colors",
    "switch_theme",
    "list_themes",
]
