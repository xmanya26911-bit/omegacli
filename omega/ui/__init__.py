"""OMEGA UI — Modular terminal interface components.

Package structure:
    themes.py       — Theme integration (wraps cli theme system)
    prompt_bar.py   — Input prompt styling, fuzzy completer, key bindings
    message.py      — Message display (user, assistant, tool calls, errors)
    status.py       — Session stats, token tracking, response footer
    commands.py     — Slash command registry and handlers
    welcome.py      — Welcome screen with ASCII art + system dashboard

Usage:
    from omega.ui import OmegaUI
    ui = OmegaUI(model_name="...", tool_count=42)
    ui.run(agent)
"""

from omega.ui.themes import get_colors
from omega.ui.prompt_bar import make_prompt_prefix, make_bottom_toolbar
from omega.ui.message import (
    display_user_message,
    display_assistant_header,
    on_tool_call,
    on_tool_result,
    on_markdown,
    on_chunk,
    on_error,
    on_info,
    on_success,
    on_warning,
    protocol_name,
)
from omega.ui.status import SessionTracker
from omega.ui.commands import CommandRegistry
from omega.ui.welcome import print_epic_welcome

__all__ = [
    "get_colors",
    "make_prompt_prefix",
    "make_bottom_toolbar",
    "display_user_message",
    "display_assistant_header",
    "on_tool_call",
    "on_tool_result",
    "on_markdown",
    "on_chunk",
    "on_error",
    "on_info",
    "on_success",
    "on_warning",
    "protocol_name",
    "SessionTracker",
    "CommandRegistry",
    "print_epic_welcome",
]
