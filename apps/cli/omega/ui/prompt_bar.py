"""Premium input bar — styled prompt, fuzzy completer, multi-line, key bindings."""

import os
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import FuzzyWordCompleter
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style as PTKStyle

from omega.ui.themes import get_colors


# Default prompt_toolkit style
BASE_PTK_STYLE = PTKStyle([
    ("prompt", "bold #a78bfa"),
    ("prompt.dim", "dim #dbd8d0"),
    ("completion-menu", "bg:#2c2b28 fg:#f5f4ef"),
    ("completion-menu.completion", "bg:#2c2b28 fg:#f5f4ef"),
    ("completion-menu.completion.current", "bg:#a78bfa fg:#262624"),
    ("completion-menu.meta", "bg:#3b3b38 fg:#d5d2c9"),
    ("completion-menu.meta.current", "bg:#a78bfa fg:#262624"),
    ("bottom-toolbar", "bg:#262624 fg:#dbd8d0"),
])


def build_default_commands():
    """Return the standard slash command dict for auto-complete."""
    return {
        "/help": "/help     Display available commands",
        "/clear": "/clear    Clear the conversation",
        "/exit": "/exit     Exit OMEGA",
        "/quit": "/quit     Exit OMEGA",
        "/context": "/context  Show session info",
        "/status": "/status   Show full system dashboard",
        "/tools": "/tools    List all available tools",
        "/theme": "/theme [name]  Show or switch color theme",
        "/history": "/history  Search conversation messages",
        "/export": "/export   Export session to markdown",
        "/compact": "/compact  Compress context window",
        "/model": "/model [name]  Switch AI model",
        "/agents": "/agents   View/manage sub-agents",
        "/bookmark": "/bookmark  Pin current message",
        "/transcript": "/transcript  Auto-save toggle",
    }


def build_key_bindings(omega_tui_ref=None):
    """Build KeyBindings for the prompt.

    Enter = submit
    Alt+Enter = newline
    Ctrl+L = clear screen
    Ctrl+D = compact context
    """
    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        """Enter submits the prompt."""
        event.current_buffer.validate_and_handle()

    @kb.add("c-l")
    def _(event):
        """Ctrl+L clears the screen."""
        event.app.current_buffer.text = ""
        if omega_tui_ref and hasattr(omega_tui_ref, "console"):
            omega_tui_ref.console.clear()
            if hasattr(omega_tui_ref, "print_epic_welcome"):
                omega_tui_ref.print_epic_welcome()

    @kb.add("c-d")
    def _(event):
        """Ctrl+D compacts context."""
        event.app.current_buffer.text = "/compact"
        event.current_buffer.validate_and_handle()

    @kb.add("c-r")
    def _(event):
        """Ctrl+R searches history — just focuses search mode."""
        event.app.current_buffer.start_reverse_history_search()

    return kb


def build_prompt_session(command_list, command_display, omega_ref=None):
    """Build a PromptSession with fuzzy completer, history, and key bindings.

    Returns (session, success_bool).
    """
    try:
        history_path = os.path.join(os.path.expanduser("~"), ".omega_history")
        session = PromptSession(
            history=FileHistory(history_path),
            completer=FuzzyWordCompleter(
                command_list,
                display_dict=command_display,
                pattern_func=None,
            ),
            complete_style=CompleteStyle.MULTI_COLUMN,
            auto_suggest=AutoSuggestFromHistory(),
            key_bindings=build_key_bindings(omega_ref),
            multiline=True,
            style=BASE_PTK_STYLE,
        )
        return session, True
    except Exception:
        return None, False


def make_prompt_prefix():
    """Build a styled prompt prefix with OMEGA branding."""
    c = get_colors()
    return FormattedText([
        ("class:prompt", "Ω "),
        ("class:prompt", "omega "),
        ("class:prompt.dim", "> "),
    ])


def make_bottom_toolbar(message_count=0, session_id="", session_start=0):
    """Build a bottom toolbar factory with session stats and char count.

    Returns a callable that prompt_toolkit calls on every render.
    """
    import time

    def _get_toolbar():
        elapsed = int(time.time() - session_start) if session_start else 0
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
        return FormattedText([
            ("class:bottom-toolbar",
             f" {message_count} msgs  |  {time_str}  |  [{session_id}]"),
        ])

    return _get_toolbar
