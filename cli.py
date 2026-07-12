#!/usr/bin/env python3
"""OMEGA CLI — Beautiful terminal interface using Rich with multiple themes (Gemini CLI inspired)."""

import shutil
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from rich.markup import escape as rich_escape

# ─── Global session timer ──────────────────────────────────────────────────────
_SESSION_START: float = time.time()
_LAST_HEARTBEAT: list[float] = [time.time()]
_CURRENT_TOOL: list[str | None] = [None]  # name of currently executing tool
_TOOL_START_TIME: list[float] = [0.0]  # when current tool started

def get_elapsed_str() -> str:
    """Return '[HH:MM:SS]' since session start."""
    elapsed = int(time.time() - _SESSION_START)
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    return f"[{h:02d}:{m:02d}:{s:02d}]"

def get_timestamp() -> str:
    """Return '[HH:MM:SS]' current wall clock."""
    return datetime.now().strftime("[%H:%M:%S]")

def set_current_tool(name: str | None) -> None:
    """Set the currently executing tool name for heartbeat display."""
    _CURRENT_TOOL[0] = name
    _TOOL_START_TIME[0] = time.time()

def clear_current_tool() -> None:
    """Clear current tool after execution."""
    _CURRENT_TOOL[0] = None
    _TOOL_START_TIME[0] = 0.0

def get_current_tool_str() -> str:
    """Return a string like '[Running: tool_name (12s)]' or empty string."""
    if _CURRENT_TOOL[0]:
        elapsed = int(time.time() - _TOOL_START_TIME[0])
        return f"[{_CURRENT_TOOL[0]} {elapsed}s]"
    return ""

def heartbeat() -> None:
    """Print heartbeat with tool progress every 5s during long tool execution."""
    now = time.time()
    if now - _LAST_HEARTBEAT[0] >= 5.0:
        tool_info = get_current_tool_str()
        elapsed = int(time.time() - _SESSION_START)
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        ts = datetime.now().strftime("%H:%M:%S")
        if tool_info:
            sys.stdout.write(f"\r  \r  [{h:02d}:{m:02d}:{s:02d}] {tool_info}")
        else:
            sys.stdout.write(f"\r  \r  [{h:02d}:{m:02d}:{s:02d}] ⏳ Active...")
        sys.stdout.flush()
        _LAST_HEARTBEAT[0] = now

def reset_heartbeat() -> None:
    """Reset heartbeat timer after tool output."""
    _LAST_HEARTBEAT[0] = time.time()

# ─── Terminal capability detection ────────────────────────────────────────────

_unicode_safe = False
_term_enc = sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else None
if _term_enc and _term_enc.lower() != 'utf-8':
    try:
        "\u2603".encode(_term_enc)
        _unicode_safe = True
    except (UnicodeEncodeError, LookupError):
        _unicode_safe = False
else:
    _unicode_safe = bool(_term_enc)

_use_rich = False
try:
    if _unicode_safe:
        from rich import box
        from rich.align import Align
        from rich.columns import Columns
        from rich.console import Console
        from rich.markdown import Markdown
        from rich.panel import Panel
        from rich.style import Style
        from rich.syntax import Syntax
        from rich.table import Table
        from rich.text import Text
        from rich.theme import Theme
        _use_rich = True
except ImportError:
    pass

_use_colorama = False
if not _use_rich:
    try:
        import colorama
        from colorama import Fore, Style
        from colorama import init as colorama_init
        colorama_init(autoreset=True)
        _use_colorama = True
    except ImportError:
        pass

if not _use_colorama and not _use_rich:
    import os
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

    class Fore:
        BLACK = '\033[30m'; RED = '\033[31m'; GREEN = '\033[32m'
        YELLOW = '\033[33m'; BLUE = '\033[34m'; MAGENTA = '\033[35m'
        CYAN = '\033[36m'; WHITE = '\033[37m'; RESET = '\033[39m'
        LIGHTBLACK_EX = '\033[90m'; LIGHTRED_EX = '\033[91m'
        LIGHTGREEN_EX = '\033[92m'; LIGHTYELLOW_EX = '\033[93m'
        LIGHTBLUE_EX = '\033[94m'; LIGHTMAGENTA_EX = '\033[95m'
        LIGHTCYAN_EX = '\033[96m'; LIGHTWHITE_EX = '\033[97m'

    class Style:
        BRIGHT = '\033[1m'; DIM = '\033[2m'
        NORMAL = '\033[22m'; RESET_ALL = '\033[0m'

_has_emoji = False
try:
    "\U0001F600".encode("cp1252")
    _has_emoji = True
except (UnicodeEncodeError, LookupError):
    pass


# ─── THEME SYSTEM (Gemini CLI inspired) ────────────────────────────────────────

OMEGA_THEMES = {
    # ── Dark Themes ──
    "default-dark": {
        "name": "Default Dark",
        "type": "dark",
        "colors": {
            "background": "#1a1b26",
            "foreground": "#a9b1d6",
            "accent_primary": "#7dcfff",
            "accent_secondary": "#bb9af7",
            "accent_success": "#9ece6a",
            "accent_warning": "#e0af68",
            "accent_error": "#f7768e",
            "accent_info": "#565f89",
            "prompt": "#bb9af7",
            "title": "#7dcfff",
            "dim_text": "#565f89",
            "tool_call": "#e0af68",
            "user_input": "#9ece6a",
            "assistant": "#a9b1d6",
            "highlight": "#1a1b26 on #7dcfff",
        },
        "ansi": {
            "foreground": 7, "accent": 6, "secondary": 5,
            "success": 2, "warning": 3, "error": 1, "info": 8,
            "prompt": 5, "dim": 8, "title": 6, "tool": 3, "user": 2,
        },
    },
    "dracula": {
        "name": "Dracula",
        "type": "dark",
        "colors": {
            "background": "#282a36",
            "foreground": "#f8f8f2",
            "accent_primary": "#8be9fd",
            "accent_secondary": "#bd93f9",
            "accent_success": "#50fa7b",
            "accent_warning": "#f1fa8c",
            "accent_error": "#ff5555",
            "accent_info": "#6272a4",
            "prompt": "#bd93f9",
            "title": "#8be9fd",
            "dim_text": "#6272a4",
            "tool_call": "#ffb86c",
            "user_input": "#50fa7b",
            "assistant": "#f8f8f2",
            "highlight": "#282a36 on #bd93f9",
        },
        "ansi": {
            "foreground": 7, "accent": 6, "secondary": 5,
            "success": 2, "warning": 3, "error": 1, "info": 8,
            "prompt": 5, "dim": 8, "title": 6, "tool": 3, "user": 2,
        },
    },
    "monokai": {
        "name": "Monokai",
        "type": "dark",
        "colors": {
            "background": "#272822",
            "foreground": "#f8f8f2",
            "accent_primary": "#a6e22e",
            "accent_secondary": "#ae81ff",
            "accent_success": "#a6e22e",
            "accent_warning": "#e6db74",
            "accent_error": "#f92672",
            "accent_info": "#75715e",
            "prompt": "#ae81ff",
            "title": "#a6e22e",
            "dim_text": "#75715e",
            "tool_call": "#fd971f",
            "user_input": "#a6e22e",
            "assistant": "#f8f8f2",
            "highlight": "#272822 on #a6e22e",
        },
        "ansi": {
            "foreground": 7, "accent": 2, "secondary": 5,
            "success": 2, "warning": 3, "error": 1, "info": 8,
            "prompt": 5, "dim": 8, "title": 2, "tool": 3, "user": 2,
        },
    },
    "nord": {
        "name": "Nord",
        "type": "dark",
        "colors": {
            "background": "#2e3440",
            "foreground": "#d8dee9",
            "accent_primary": "#88c0d0",
            "accent_secondary": "#b48ead",
            "accent_success": "#a3be8c",
            "accent_warning": "#ebcb8b",
            "accent_error": "#bf616a",
            "accent_info": "#4c566a",
            "prompt": "#b48ead",
            "title": "#88c0d0",
            "dim_text": "#4c566a",
            "tool_call": "#d08770",
            "user_input": "#a3be8c",
            "assistant": "#d8dee9",
            "highlight": "#2e3440 on #88c0d0",
        },
        "ansi": {
            "foreground": 7, "accent": 6, "secondary": 5,
            "success": 2, "warning": 3, "error": 1, "info": 8,
            "prompt": 5, "dim": 8, "title": 6, "tool": 3, "user": 2,
        },
    },
    # ── Light Themes ──
    "default-light": {
        "name": "Default Light",
        "type": "light",
        "colors": {
            "background": "#ffffff",
            "foreground": "#24292f",
            "accent_primary": "#0969da",
            "accent_secondary": "#8250df",
            "accent_success": "#1a7f37",
            "accent_warning": "#9a6700",
            "accent_error": "#cf222e",
            "accent_info": "#656d76",
            "prompt": "#8250df",
            "title": "#0969da",
            "dim_text": "#656d76",
            "tool_call": "#9a6700",
            "user_input": "#1a7f37",
            "assistant": "#24292f",
            "highlight": "#ffffff on #0969da",
        },
        "ansi": {
            "foreground": 0, "accent": 4, "secondary": 5,
            "success": 2, "warning": 3, "error": 1, "info": 7,
            "prompt": 5, "dim": 7, "title": 4, "tool": 3, "user": 2,
        },
    },
    "github-light": {
        "name": "GitHub Light",
        "type": "light",
        "colors": {
            "background": "#ffffff",
            "foreground": "#1f2328",
            "accent_primary": "#0969da",
            "accent_secondary": "#8250df",
            "accent_success": "#1a7f37",
            "accent_warning": "#bf8700",
            "accent_error": "#cf222e",
            "accent_info": "#636c76",
            "prompt": "#8250df",
            "title": "#0969da",
            "dim_text": "#636c76",
            "tool_call": "#9a6700",
            "user_input": "#1a7f37",
            "assistant": "#1f2328",
            "highlight": "#ffffff on #0969da",
        },
        "ansi": {
            "foreground": 0, "accent": 4, "secondary": 5,
            "success": 2, "warning": 3, "error": 1, "info": 7,
            "prompt": 5, "dim": 7, "title": 4, "tool": 3, "user": 2,
        },
    },
}

AVAILABLE_THEMES = list(OMEGA_THEMES.keys())
DEFAULT_THEME = "default-dark"

# Current active theme — set via set_active_theme()
_current_theme_name = DEFAULT_THEME
_current_theme = OMEGA_THEMES[DEFAULT_THEME]
custom_theme: Theme | None = Theme({}) if _use_rich else None


def get_theme_names() -> list[tuple[str, str, str]]:
    """Return list of available themes with their display names."""
    return [(k, v["name"], v["type"]) for k, v in OMEGA_THEMES.items()]


def set_active_theme(theme_name: str) -> bool:
    """Switch the active theme. Returns True on success."""
    global _current_theme_name, _current_theme
    if theme_name in OMEGA_THEMES:
        _current_theme_name = theme_name
        _current_theme = OMEGA_THEMES[theme_name]
        _apply_rich_theme()
        return True
    return False


def get_active_theme() -> str | None:
    """Return current theme key."""
    return _current_theme_name


def get_theme_colors() -> dict:
    """Return the color dict for the active theme."""
    return _current_theme["colors"]


def _apply_rich_theme() -> None:
    """Recreate the global Rich console with the new theme colors."""
    global console, error_console, custom_theme
    if not _use_rich:
        return
    c = _current_theme["colors"]
    custom_theme = Theme({
        "info": f"italic {c['accent_info']}",
        "warning": f"bold {c['accent_warning']}",
        "error": f"bold {c['accent_error']}",
        "success": f"bold {c['accent_success']}",
        "title": f"bold {c['title']}",
        "prompt": f"bold {c['prompt']}",
        "assistant": c["assistant"],
        "tool": c["tool_call"],
        "dim": f"dim {c['dim_text']}",
        "highlight": c["highlight"],
        "secondary": c["accent_secondary"],
        "primary": c["accent_primary"],
    })
    console = Console(theme=custom_theme, highlight=False)
    error_console = Console(stderr=False, theme=custom_theme, highlight=False)


# Initialize Rich / fallback console
if _use_rich:
    _apply_rich_theme()
elif _use_colorama:
    console = None
    error_console = None
else:
    class SimpleConsole:
        def print(self, *args: object, **kwargs: object) -> None:
            print(*args)
        def rule(self, *args: object, **kwargs: object) -> None:
            pass
    console = SimpleConsole()
    error_console = SimpleConsole()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def sanitize(text: str) -> str:
    """Sanitize text for Windows console encoding."""
    if not text:
        return text
    text = rich_escape(text)
    try:
        text.encode("cp1252")
        return text
    except UnicodeEncodeError:
        return text.encode("cp1252", errors="replace").decode("cp1252")


def safe_char(ch: str, fallback: str) -> str:
    """Return ch if it can be encoded to cp1252, otherwise fallback."""
    try:
        ch.encode("cp1252")
        return ch
    except UnicodeEncodeError:
        return fallback


# Character fallbacks for non-Unicode consoles
_S = {
    'omega': safe_char('Ω', 'O'),
    'pipe': safe_char('┃', '|'),
    'arrow': safe_char('→', '->'),
    'check': safe_char('✓', '+'),
    'bullet': safe_char('●', '*'),
    'diamond': safe_char('◇', 'o'),
    'rarrow': safe_char('›', '>'),
    'info': safe_char('ℹ', 'i'),
    'warn': safe_char('⚠', '!'),
    'cross': safe_char('✖', 'x'),
    'hbar': safe_char('─', '-'),
    'diamond_filled': safe_char('◆', '*'),
    'bolt': safe_char('⚡', '!'),
}


def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_terminal_width() -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


# ANSI color helpers for fallback mode
def _ansi(n: int, bright: bool = False) -> str:
    """Return ANSI escape code for color number n."""
    if bright:
        return f"\033[{30 + n}m" if n < 8 else f"\033[90m"
    return f"\033[{30 + n if n < 8 else 90}m"


def _theme_ansi(key: str) -> str:
    """Get ANSI escape code for a theme color key."""
    ansi_map = _current_theme.get("ansi", {})
    n = ansi_map.get(key, 7)
    return _ansi(n)


def _theme_ansi_bright(key: str) -> str:
    """Get bright ANSI escape code for a theme color key."""
    ansi_map = _current_theme.get("ansi", {})
    n = ansi_map.get(key, 7)
    return f"\033[{30 + n if n < 8 else 90};1m"


# ─── Banner ───────────────────────────────────────────────────────────────────




def print_banner(config: dict | None = None, compact: bool = False) -> None:
    """Print a sleek, minimal OMEGA banner — Claude Code inspired."""
    model_name = config.model if config else "unknown"

    if _use_rich:
        c = _current_theme["colors"]
        term_width = get_terminal_width()
        sep = "─" * min(term_width - 4, 48)

        text = Text()
        text.append(" Ω ", style=f"bold {c['accent_primary']}")
        text.append("OMEGA", style=f"bold {c['accent_secondary']}")
        text.append(f"  {model_name}", style=f"dim {c['dim_text']}")
        text.append(f"  {sep}", style=f"dim {c['dim_text']}")
        if compact:
            console.print(text)
        else:
            # One-line header, no heavy boxes
            console.print()
            console.print(text)
            console.print()
    else:
        tc = _theme_ansi_bright("title")
        sc = _theme_ansi_bright("secondary")
        dc = _theme_ansi("dim")
        print(f"\n{tc}{_S['omega']}{Style.RESET_ALL} {sc}OMEGA{Style.RESET_ALL} {dc}{model_name}{Style.RESET_ALL}\n")


# ─── Thinking Indicator ───────────────────────────────────────────────────────

class Spinner:
    """Animated spinner that runs in a daemon thread."""
    def __init__(self, message: str = "Thinking") -> None:
        self._running = False
        self._thread: threading.Thread | None = None
        self._message = message
        self._chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        if not _unicode_safe:
            self._chars = ["|", "/", "-", "\\"]

    def __enter__(self) -> 'Spinner':
        self.start()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None) -> None:
        self.stop()

    def start(self) -> None:
        if _use_rich:
            return
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        if not _use_rich:
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

    def _spin(self) -> None:
        idx = 0
        tc = _theme_ansi("accent")
        while self._running:
            sys.stdout.write(f"\r  {tc}{self._chars[idx]}{Style.RESET_ALL} {self._message}...")
            sys.stdout.flush()
            idx = (idx + 1) % len(self._chars)
            time.sleep(0.1)


# ─── User Input / Output ──────────────────────────────────────────────────────

def print_user_input(text: str) -> None:
    """Print user input — Claude Code style: clean header, no panel."""
    text = sanitize(text)
    c = _current_theme["colors"]
    if _use_rich:
        console.print(f"\n[bold {c['user_input']}]┃ You[/bold {c['user_input']}]")
        # Print content with subtle left border or just clean
        for line in text.split('\n'):
            console.print(f"  {line}", style=c['foreground'])
        console.print()
    else:
        uc = _theme_ansi_bright("user")
        print(f"\n{uc}{_S['pipe']} You{Style.RESET_ALL}")
        for line in text.split('\n'):
            print(f"  {uc}{line}{Style.RESET_ALL}")
        print()


# ─── Thinking / Streaming Display ────────────────────────────────────────────
# OMEGA now shows its reasoning process with a clear visual distinction.
# Thinking = dim/italic (internal monologue), Final = normal style (response).

_streaming_header_shown = False
_thinking_active = False
_thinking_has_content = False
_thinking_at_line_start = True

def print_assistant_header() -> None:
    """Print the assistant header before streaming starts — shown once per response."""
    global _streaming_header_shown
    if _streaming_header_shown:
        return
    _streaming_header_shown = True
    c = _current_theme["colors"]
    if _use_rich:
        console.print(f"\n[bold {c['accent_secondary']}]┃ OMEGA[/bold {c['accent_secondary']}]")
    else:
        sc = _theme_ansi_bright("secondary")
        print(f"\n{sc}{_S['pipe']} OMEGA{Style.RESET_ALL}")


def print_thinking_start() -> None:
    """Show the '--- Reasoning ---' header when OMEGA starts thinking."""
    global _thinking_active, _thinking_has_content
    if _thinking_active:
        return
    _thinking_active = True
    _thinking_has_content = False
    _thinking_at_line_start = True
    c = _current_theme["colors"]
    sep = "-" * 40
    if _use_rich:
        console.print(f"  [dim {c['assistant']}]{sep}[/dim {c['assistant']}]")
        console.print(f"  [italic {c['assistant']}]Reasoning:[/italic {c['assistant']}]")
    else:
        dc = _theme_ansi("dim")
        print(f"  {dc}{sep}{Style.RESET_ALL}")
        print(f"  {dc}Reasoning:{Style.RESET_ALL}")


def print_thinking_busy() -> None:
    """Show a subtle live indicator during streaming (overwritten when done)."""
    if _use_rich:
        c = _current_theme["colors"]
        console.print(f"  [italic dim {c['dim_text']}]Thinking...[/italic dim {c['dim_text']}]", end="\r")
    else:
        dc = _theme_ansi("dim")
        bullet = _S.get('bullet', '*')
        sys.stdout.write(f"  {dc}{bullet} Thinking...{Style.RESET_ALL}\r")
        sys.stdout.flush()


def print_assistant_thinking(text: str) -> None:
    """Print streaming thinking/reasoning — shows the live reasoning as the AI thinks."""
    global _thinking_has_content, _thinking_at_line_start
    _thinking_has_content = True
    if not text:
        return
    if _use_rich:
        c = _current_theme["colors"]
        prefix = "  " if _thinking_at_line_start else ""
        _thinking_at_line_start = text.endswith("\n")
        console.print(f"{prefix}{sanitize(text)}", style=f"italic {c['assistant']}", end="")
    else:
        dc = _theme_ansi("dim")
        prefix = "  " if _thinking_at_line_start else ""
        _thinking_at_line_start = text.endswith("\n")
        sys.stdout.write(f"{prefix}{sanitize(text)}")
        sys.stdout.flush()


def print_thinking_block(content: str) -> None:
    """Display the complete thinking block (buffered) with header and content."""
    if not content:
        return
    c = _current_theme["colors"]
    check = _S.get('check', '+')
    bullet = _S.get('bullet', '*')
    # Clear any previous line (from busy indicator)
    width = get_terminal_width()
    if _use_rich:
        console.print(f"\r{' ' * width}\r", end="")
        console.print(f"  [italic dim {c['dim_text']}]{bullet} Thinking...[/italic dim {c['dim_text']}]")
        console.print(sanitize(content), style=f"italic dim {c['dim_text']}")
        console.print(f"  [dim {c['dim_text']}]{check} Analyzed[/dim {c['dim_text']}]")
    else:
        sys.stdout.write(f"\r{' ' * width}\r")
        dc = _theme_ansi("dim")
        print(f"  {dc}{bullet} Thinking...{Style.RESET_ALL}")
        sys.stdout.write(f"{dc}{sanitize(content)}{Style.RESET_ALL}")
        print()
        print(f"  {dc}{check} Analyzed{Style.RESET_ALL}")


def print_thinking_done() -> None:
    """Mark the end of the thinking phase — shows the end section."""
    global _thinking_active
    if not _thinking_active:
        return
    _thinking_active = False
    c = _current_theme["colors"]
    sep = "-" * 40
    if _use_rich:
        if _thinking_has_content:
            console.print()
        console.print(f"  [dim {c['assistant']}]{sep}[/dim {c['assistant']}]")
    else:
        dc = _theme_ansi("dim")
        if _thinking_has_content:
            print()
        print(f"  {dc}{sep}{Style.RESET_ALL}")


def print_assistant_done() -> None:
    """Called when assistant finishes a response."""
    if _use_rich:
        pass
    print()


def print_assistant_message(text: str) -> None:
    """Print a complete assistant message — clean, no Panel wrapping."""
    if not text:
        return
    text = sanitize(text)
    c = _current_theme["colors"]
    if _use_rich:
        console.print(f"\n[bold {c['accent_secondary']}]┃ OMEGA[/bold {c['accent_secondary']}]")
        if any(m in text for m in ['```', '**', '#', '- ', '1. ']):
            try:
                md = Markdown(text)
                console.print(md)
            except Exception:
                for line in text.split('\n'):
                    console.print(f"  {line}", style=c['assistant'])
        else:
            for line in text.split('\n'):
                console.print(f"  {line}", style=c['assistant'])
        console.print()
    else:
        sc = _theme_ansi_bright("secondary")
        fc = _theme_ansi("foreground")
        print(f"\n{sc}{_S['pipe']} OMEGA{Style.RESET_ALL}")
        for line in text.split('\n'):
            print(f"  {fc}{line}{Style.RESET_ALL}")
        print()


def reset_streaming_header() -> None:
    """Reset the streaming header flag for the next response."""
    global _streaming_header_shown, _thinking_active, _thinking_has_content, _thinking_at_line_start
    _streaming_header_shown = False
    _thinking_active = False
    _thinking_has_content = False
    _thinking_at_line_start = True


def get_input(model_name: str = "unknown", message_count: int = 0, token_estimate: int = 0) -> str:
    """Get user input — Claude Code style: clean › prompt with minimal context."""
    try:
        if _use_rich:
            c = _current_theme["colors"]
            # Claude Code style: just › with subtle context
            ctx = ""
            if message_count > 0 or token_estimate > 0:
                parts = []
                if message_count > 0:
                    parts.append(f"{message_count}msgs")
                if token_estimate > 0:
                    parts.append(f"~{token_estimate:,}tok")
                ctx = f" [dim {c['dim_text']}]({' '.join(parts)})[/dim {c['dim_text']}]"
            user_input = console.input(
                f"\n[bold {c['prompt']}]›[/bold {c['prompt']}]{ctx} "
            ).strip()
            return user_input
        else:
            ctx_parts = []
            if message_count > 0:
                ctx_parts.append(f"{message_count}msgs")
            if token_estimate > 0:
                ctx_parts.append(f"~{token_estimate:,}tok")
            ctx_str = f"({' '.join(ctx_parts)})" if ctx_parts else ""
            pc = _theme_ansi_bright("prompt")
            dc = _theme_ansi("dim")
            prompt = f"\n{pc}{_S['rarrow']}{Style.RESET_ALL}{dc} {ctx_str}{Style.RESET_ALL} " if ctx_str else f"\n{pc}{_S['rarrow']}{Style.RESET_ALL} "
            user_input = input(prompt).strip()
            return user_input
    except (EOFError, KeyboardInterrupt):
        return None


# ─── Tool Call Display ────────────────────────────────────────────────────────

def _protocol_name(name: str) -> str:
    """Convert a tool name to a JARVIS-style protocol name."""
    protocol_map = {
        "execute_command": "Executing Shell Command",
        "read_file": "Reading File",
        "write_file": "Writing File",
        "edit_file": "Modifying File",
        "glob": "Searching Files",
        "grep": "Content Search",
        "web_fetch": "Fetching Web Resource",
        "web_search": "Web Intelligence Search",
        "list_dir": "Scanning Directory",
        "system_info": "System Analysis",
        "self_diagnose": "Running Self-Diagnostics",
        "hash_file": "Generating File Hash",
        "download_file": "Downloading Resource",
        "diff_files": "Comparing Files",
        "remember": "Committing to Memory",
        "recall": "Memory Retrieval",
        "search_memory": "Memory Search",
        "forget": "Memory Erasure",
        "save_note": "Saving Note",
        "read_note": "Reading Note",
        "delete_note": "Deleting Note",
        "list_notes": "Listing Notes",
        "zip_files": "Archiving Files",
        "unzip_file": "Extracting Archive",
        "list_processes": "Process Analysis",
        "kill_process": "Terminating Process",
        "backup_memories": "Initiating Memory Backup",
        "import_memories": "Restoring Memory Backup",
        "get_env": "Environment Probe",
        "cache_stats": "Cache Analysis",
        "clear_cache": "Purging Cache",
        "check_update": "Checking for Updates",
        "move_file": "Relocating File",
        "copy_file": "Duplicating File",
        "delete_file": "Removing File",
        "tree": "Directory Mapping",
        "calculate": "Computing",
        "json_tool": "JSON Processing",
        "base64": "Base64 Encoding",
        "get_public_ip": "External IP Probe",
        "camera_list": "Camera Detection",
        "camera_capture": "Capturing Image",
        "camera_analyze": "Analyzing Visual Feed",
        "camera_watch": "Surveillance Protocol",
        "camera_stream": "Video Stream Init",
        "get_date": "Chronometric Reading",
        "finish": "Mission Complete",
    }
    return protocol_map.get(name, name.replace("_", " ").title())


def print_tool_call(name: str, args: str | None = None, duration: str | None = None) -> None:
    """Print a tool call — with timestamp so user sees progress."""
    reset_heartbeat()
    ts = get_timestamp()
    args_str = ""
    if args:
        try:
            import json
            args_obj = json.loads(args) if isinstance(args, str) else args
            important_args = {k: v for k, v in args_obj.items() if k not in ("content",)}
            if important_args:
                arg_parts = []
                for k, v in important_args.items():
                    v_str = str(v)
                    if len(v_str) > 60:
                        v_str = v_str[:57] + "..."
                    arg_parts.append(f"{k}={v_str}")
                args_str = "(" + ", ".join(arg_parts) + ")"
        except Exception:
            args_str = ""

    protocol = _protocol_name(name)
    c = _current_theme["colors"]
    if _use_rich:
        text = Text()
        text.append(f"{ts} ", style=f"dim {c['dim_text']}")
        text.append("  → ", style=f"dim {c['dim_text']}")
        text.append(protocol, style=f"bold {c['tool_call']}")
        if args_str:
            text.append(f" {args_str}", style=f"dim {c['dim_text']}")
        if duration is not None:
            text.append(f"  ({duration:.1f}s)", style=f"dim {c['dim_text']}")
        console.print(text)
    else:
        tc = _theme_ansi_bright("tool")
        dc = _theme_ansi("dim")
        dur = f" ({duration:.1f}s)" if duration is not None else ""
        print(f"  {dc}{ts}{Style.RESET_ALL} {_S['arrow']} {tc}{protocol}{Style.RESET_ALL}{dc}{args_str}{dur}{Style.RESET_ALL}")
    sys.stdout.flush()


def print_tool_result(content: str, is_error: bool = False) -> None:
    """Print tool execution result — with timestamp so user sees progress."""
    reset_heartbeat()
    if not content:
        return
    lines = content.split("\n")
    max_lines = min(len(lines), 20)
    truncated = len(lines) > max_lines

    c = _current_theme["colors"]
    if _use_rich:
        style = c['accent_error'] if is_error else f"dim {c['dim_text']}"
        for line in lines[:max_lines]:
            console.print(f"    {sanitize(line)}", style=style)
        if truncated:
            console.print(
                f"    ┊ ({len(lines) - max_lines} more lines)",
                style=f"italic dim {c['dim_text']}"
            )
    else:
        ec = _theme_ansi("error")
        dc = _theme_ansi("dim")
        for line in lines[:max_lines]:
            line = sanitize(line)
            if is_error:
                print(f"    {ec}{line}{Style.RESET_ALL}")
            else:
                print(f"    {dc}{line}{Style.RESET_ALL}")
        if truncated:
            print(f"    {dc}┊ ({len(lines) - max_lines} more lines){Style.RESET_ALL}")
    sys.stdout.flush()


def print_task_complete(summary: str) -> None:
    """Print task completion — clean checkmark, no heavy rules."""
    c = _current_theme["colors"]
    if _use_rich:
        console.print(f"\n  [bold {c['accent_success']}]✓ {sanitize(summary)}[/bold {c['accent_success']}]")
        console.print()
    else:
        sc = _theme_ansi_bright("success")
        print(f"\n  {sc}{_S['check']} {sanitize(summary)}{Style.RESET_ALL}")
        print()


# ─── Info / Warning / Error ───────────────────────────────────────────────────

def print_info(text: str) -> None:
    """Print informational message — minimal."""
    c = _current_theme["colors"]
    if _use_rich:
        console.print(f"  [info]ℹ {sanitize(text)}[/info]")
    else:
        ic = _theme_ansi("info")
        print(f"  {ic}{_S['info']} {text}{Style.RESET_ALL}")


# ─── Diff Display ────────────────────────────────────────────────────────────

def print_diff(diff_text: str, max_lines: int = 50) -> None:
    """Print a unified diff with colour-coded additions/removals."""
    if not diff_text or diff_text.strip() == "(no changes)":
        print_info("(no changes)")
        return

    lines = diff_text.split("\n")
    added = 0
    removed = 0
    c = _current_theme["colors"]

    if _use_rich:
        for line in lines[:max_lines]:
            if line.startswith("+") and not line.startswith("+++"):
                console.print(f"  [success]{sanitize(line)}[/success]")
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                console.print(f"  [error]{sanitize(line)}[/error]")
                removed += 1
            elif line.startswith("@@"):
                console.print(f"  [dim]{sanitize(line)}[/dim]")
            elif line.startswith(("diff --git", "index ")):
                continue
            elif line.strip():
                console.print(f"  {sanitize(line)}")
        if len(lines) > max_lines:
            console.print(f"  [dim]┊ ({len(lines) - max_lines} more lines)[/dim]")
        console.print(f"  [bold {c['accent_success']}]┊ +{added} -{removed}[/bold {c['accent_success']}]")
    else:
        sc = _theme_ansi_bright("success")
        ec = _theme_ansi_bright("error")
        dc = _theme_ansi("dim")
        for line in lines[:max_lines]:
            if line.startswith("+") and not line.startswith("+++"):
                print(f"  {sc}{line}{Style.RESET_ALL}")
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                print(f"  {ec}{line}{Style.RESET_ALL}")
                removed += 1
            elif line.startswith("@@"):
                print(f"  {dc}{line}{Style.RESET_ALL}")
            elif line.strip():
                print(f"  {line}")
        dc = _theme_ansi("dim")
        print(f"  {dc}┊ +{added} -{removed}{Style.RESET_ALL}")


def print_warning(text: str) -> None:
    """Print warning message — minimal."""
    c = _current_theme["colors"]
    if _use_rich:
        console.print(f"  [warning]⚠ {sanitize(text)}[/warning]")
    else:
        wc = _theme_ansi_bright("warning")
        print(f"  {wc}{_S['warn']} {text}{Style.RESET_ALL}")


def print_error(text: str) -> None:
    """Print error message — minimal."""
    if _use_rich:
        error_console.print(f"  [error]✖ {sanitize(text)}[/error]")
    else:
        ec = _theme_ansi_bright("error")
        print(f"  {ec}{_S['cross']} {text}{Style.RESET_ALL}")


def print_success(text: str) -> None:
    """Print success message — minimal."""
    c = _current_theme["colors"]
    if _use_rich:
        console.print(f"  [success]✓ {sanitize(text)}[/success]")
    else:
        sc = _theme_ansi_bright("success")
        print(f"  {sc}{_S['check']} {text}{Style.RESET_ALL}")


# ─── Tables ────────────────────────────────────────────────────────────────────

def print_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
    """Print a table — clean, minimal borders."""
    c = _current_theme["colors"]
    if _use_rich:
        table = Table(
            title=title,
            box=box.SIMPLE,
            border_style=f"dim {c['dim_text']}",
            header_style=f"bold {c['title']}",
            title_style=f"bold {c['foreground']}",
            padding=(0, 1),
        )
        for col in columns:
            table.add_column(col, no_wrap=False)
        for row in rows:
            table.add_row(*[str(cell) for cell in row])
        console.print(table)
    else:
        tc = _theme_ansi_bright("title")
        dc = _theme_ansi("dim")
        nc = Style.RESET_ALL
        print(f"  {tc}{title}{nc}")
        if not rows:
            print(f"  {dc}(empty){nc}")
            return
        col_widths = [len(str(col)) for col in columns]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        max_width = get_terminal_width() - 4 - (len(columns) - 1) * 3
        total = sum(col_widths)
        if total > max_width:
            scale = max_width / total
            col_widths = [max(10, int(w * scale)) for w in col_widths]
        h = _S['hbar']
        v = _S['pipe']
        sep = h * (sum(col_widths) + (len(columns) - 1) * 3)
        print(f"  +{sep}+")
        header = v + " " + f" {v} ".join(str(col).ljust(col_widths[i]) for i, col in enumerate(columns)) + f" {v}"
        print(f"  {header}")
        print(f"  +{sep}+")
        for row in rows:
            cells = []
            for i, cell in enumerate(row):
                s = str(cell)
                if len(s) > col_widths[i]:
                    s = s[:col_widths[i] - 3] + "..."
                cells.append(s.ljust(col_widths[i]))
            print(f"  {v} " + f" {v} ".join(cells) + f" {v}")
        print(f"  +{sep}+")


# ─── Code Display ─────────────────────────────────────────────────────────────

def print_code(code: str, language: str = "python") -> None:
    """Print syntax-highlighted code — minimal, no panel wrapping."""
    if _use_rich:
        try:
            syntax = Syntax(code, language, theme="monokai", line_numbers=False)
            console.print(syntax)
        except Exception:
            console.print(code)
    else:
        print(sanitize(code))


# ─── Help / Welcome ────────────────────────────────────────────────────────────

def print_welcome(model_name: str = "unknown") -> None:
    """Print a sleek, Claude Code-inspired welcome message."""
    from datetime import datetime
    hour = datetime.now().hour
    if hour < 12:
        greeting = "morning"
    elif hour < 17:
        greeting = "afternoon"
    else:
        greeting = "evening"

    c = _current_theme["colors"]
    if _use_rich:
        term_width = get_terminal_width()
        sep = "─" * min(term_width - 4, 48)

        # Sleek one-line greeting
        line = Text()
        line.append(f"  Hey! Good {greeting} ☀️", style=c['foreground'])
        console.print(line)

        line2 = Text()
        line2.append("  OMEGA here! Ready to rock. 🤘", style=f"dim {c['dim_text']}")
        line2.append("  ", style=f"dim {c['dim_text']}")
        line2.append("🔥 Claude Code+ features loaded", style=f"bold {c['accent_success']}")
        console.print(line2)
        line3 = Text()
        line3.append("  Try ", style=f"dim {c['dim_text']}")
        line3.append("/compass", style=f"bold {c['tool_call']}")
        line3.append(" for project map, ", style=f"dim {c['dim_text']}")
        line3.append("/project", style=f"bold {c['tool_call']}")
        line3.append(" for config, ", style=f"dim {c['dim_text']}")
        line3.append("/find", style=f"bold {c['tool_call']}")
        line3.append(" to discover files, ", style=f"dim {c['dim_text']}")
        line3.append("/cost", style=f"bold {c['tool_call']}")
        line3.append(" for usage", style=f"dim {c['dim_text']}")
        console.print(line3)
        console.print(f"  {sep}", style=f"dim {c['dim_text']}")
        console.print()
    else:
        fc = _theme_ansi("foreground")
        dc = _theme_ansi("dim")
        tc = _theme_ansi_bright("tool")
        sc = _theme_ansi_bright("success")
        print(f"  Hey! Good {greeting} ☀️")
        print(f"  OMEGA here! Ready to rock. 🤘  {sc}🔥 Claude Code+ features loaded{Style.RESET_ALL}")
        print(f"  Try {tc}/compass{dc} for project map, {tc}/project{dc} for config, {tc}/find{dc} files, {tc}/cost{dc} usage")
        print()
        hbar = _S['hbar']
        print(f"  {dc}{hbar * 40}{Style.RESET_ALL}")
        print()


def print_theme_list(current_theme: str) -> None:
    """Print available themes — clean list."""
    rows: list[list[str]] = []
    for key, info in OMEGA_THEMES.items():
        marker = f" {_S['bullet']}" if key == current_theme else ""
        rows.append([f"{key}{marker}", str(info["name"]), str(info["type"])])
    print_table("Themes", ["Key", "Display Name", "Type"], rows)
    print_info(f"Current: {current_theme}")
    print_info("Usage: /theme <key>  (e.g., /theme dracula)")


def print_help() -> None:
    """Print comprehensive help — Claude Code style: clean, organized."""
    c = _current_theme["colors"]
    if _use_rich:
        console.print()
        header = Text()
        header.append("Ω OMEGA", style=f"bold {c['accent_secondary']}")
        header.append(" Commands", style=f"bold {c['foreground']}")
        console.print(f"  {header}")

        categories = [
            ("Session", [
                ("/clear", "Reset conversation context"),
                ("/save [name]", "Save session to persistent storage"),
                ("/load <name>", "Load a previously saved session"),
                ("/sessions", "List all archived sessions"),
                ("/stats", "Display token & tool usage statistics"),
                ("/exit", "Shut down OMEGA"),
            ]),
            ("Model & Config", [
                ("/model <name>", "Switch AI model"),
                ("/configure", "View or modify API key, URL, model"),
                ("/theme [name]", "Show or switch color theme"),
            ]),
            ("Memory & Data", [
                ("/memory [query]", "Search or list persistent memories"),
                ("/recall <query>", "Search ALL conversation history (Total Recall)"),
                ("/history", "Show Total Recall statistics"),
                ("/notes [tag]", "List saved notes"),
                ("/forget <key>", "Erase a specific memory"),
                ("/backup [path]", "Export all memories to JSON"),
            ]),
            ("System", [
                ("/system", "Full system analysis"),
                ("/env [var]", "Environment variables"),
                ("/ps [filter]", "Process analysis"),
                ("/cache [clear]", "Cache analysis or purge"),
                ("/update", "Check for OMEGA updates"),
                ("/diagnose", "Run comprehensive self-diagnostics"),
            ]),
        ]

        for cat_name, commands in categories:
            console.print(f"\n  [bold {c['title']}]{cat_name}[/bold {c['title']}]")
            for cmd, desc in commands:
                console.print(f"    [bold {c['tool_call']}]{cmd:<22}[/bold {c['tool_call']}] {desc}")

        console.print(f"\n  [dim {c['dim_text']}]What can I help you with? 😊[/dim {c['dim_text']}]")
        console.print()
    else:
        tc = _theme_ansi_bright("title")
        cmd_color = _theme_ansi_bright("tool")
        desc_color = _theme_ansi("foreground")
        dc = _theme_ansi("dim")
        print(f"  {_S['omega']} OMEGA Commands")
        print()

        categories = [
            ("Session", [
                ("/clear", "Reset conversation context"),
                ("/save [name]", "Save session to disk"),
                ("/load <name>", "Load a saved session"),
                ("/sessions", "List all saved sessions"),
                ("/stats", "Show token & tool usage stats"),
                ("/exit", "Exit OMEGA"),
            ]),
            ("Model & Config", [
                ("/model <name>", "Switch AI model"),
                ("/configure", "View/change API key, URL, model"),
                ("/theme [name]", "Show or switch color theme"),
            ]),
            ("Memory & Data", [
                ("/memory [query]", "Search/list persistent memories"),
                ("/recall <query>", "Search ALL conversations (Total Recall)"),
                ("/history", "Total Recall stats & dates"),
                ("/notes [tag]", "List saved notes"),
                ("/forget <key>", "Delete a specific memory"),
                ("/backup [path]", "Export all memories to JSON"),
            ]),
            ("System", [
                ("/system", "Show system information"),
                ("/env [var]", "Show environment variables"),
                ("/ps [filter]", "List running processes"),
                ("/cache [clear]", "Show/clear cache stats"),
                ("/update", "Check for OMEGA updates"),
                ("/diagnose", "Run self-diagnostics"),
            ]),
        ]

        for cat_name, commands in categories:
            print(f"  {tc}{cat_name}:{Style.RESET_ALL}")
            for cmd, desc in commands:
                print(f"    {cmd_color}{cmd:<22}{Style.RESET_ALL} {desc_color}{desc}{Style.RESET_ALL}")
            print()

        print(f"  {dc}What can I help you with? 😊{Style.RESET_ALL}")
        print()
