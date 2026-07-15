"""Theme integration — wraps cli.py theme system for the TUI."""

from rich.text import Text as RichText

# Fallback colors when cli module isn't available
FALLBACK = {
    "background": "#262624",
    "foreground": "#f5f4ef",
    "accent_primary": "#22d3ee",
    "accent_secondary": "#a78bfa",
    "accent_success": "#84cc16",
    "accent_warning": "#fb923c",
    "accent_error": "#ef4444",
    "dim_text": "#dbd8d0",
    "tool_call": "#fb923c",
    "user_input": "#84cc16",
    "prompt": "#a78bfa",
    "title": "#22d3ee",
    "assistant": "#f5f4ef",
    "highlight": "#a78bfa",
}


def get_colors():
    """Get current theme colors from cli module, with fallback."""
    try:
        from cli import get_theme_colors
        return get_theme_colors()
    except Exception:
        return dict(FALLBACK)


def switch_theme(name):
    """Switch the active theme. Returns True on success."""
    try:
        from cli import set_active_theme
        return set_active_theme(name)
    except Exception:
        return False


def list_themes():
    """Return list of (key, display_name, type) tuples."""
    try:
        from cli import get_theme_names
        return get_theme_names()
    except Exception:
        return []


def get_active():
    """Return current theme key."""
    try:
        from cli import get_active_theme
        return get_active_theme()
    except Exception:
        return "default-dark"
