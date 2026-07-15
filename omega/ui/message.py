"""Beautiful message display — user bubbles, assistant headers, tool calls, errors."""

from datetime import datetime
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text as RichText
from rich.box import ROUNDED
from rich.syntax import Syntax

from omega.ui.themes import get_colors


def display_user_message(console, text):
    """Display user message in a styled bubble with rounded panel."""
    c = get_colors()
    user_color = c.get("user_input", "#84cc16")
    dim = c.get("dim_text", "#dbd8d0")

    sep = "─" * 24
    console.print(f"  [dim {dim}]{sep}[/]")

    header = RichText()
    header.append("  ◆ ", style=f"bold {user_color}")
    header.append("You", style=f"bold {user_color}")
    console.print(header)

    content = text.strip()
    if content:
        from rich.markup import escape
        console.print(Panel(
            escape(content),
            border_style=f"dim {dim}",
            padding=(0, 1),
            box=ROUNDED,
        ))
    console.print()


def display_assistant_header(console):
    """Display assistant header before streaming begins."""
    c = get_colors()
    secondary = c.get("accent_secondary", "#a78bfa")
    dim = c.get("dim_text", "#dbd8d0")

    sep = "─" * 24
    console.print(f"  [dim {dim}]{sep}[/]")
    header = RichText()
    header.append("  ◇ ", style=f"bold {secondary}")
    header.append("OMEGA", style=f"bold {secondary}")
    console.print(header)


def display_response_footer(console, tracker):
    """Display a compact status footer after each assistant response.

    Shows: token estimate, tools used, elapsed session time.
    """
    c = get_colors()
    dim = c.get("dim_text", "#dbd8d0")
    success = c.get("accent_success", "#84cc16")

    elapsed = int(tracker.elapsed())
    h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    tok_in = tracker.token_count_input
    tok_out = tracker.token_count_output
    tool_calls = tracker.tool_invocation_count

    parts = []
    if tok_in or tok_out:
        total = tok_in + tok_out
        parts.append(f"~{total:,} tok")
    if tool_calls:
        parts.append(f"{tool_calls} tools")
    parts.append(f"{h:02d}:{m:02d}:{s:02d}")

    footer = f"[dim {dim}]─[/dim {dim}] "
    for i, part in enumerate(parts):
        if i > 0:
            footer += f" [dim {dim}]·[/dim {dim}] "
        footer += f"[dim {dim}]{part}[/dim {dim}]"

    console.print(f"  {footer}")
    console.print()


_thinking_started = False
_thinking_style = None

def on_chunk(console, text):
    """Print a streaming thinking chunk inline (no newline per token).

    Uses style= parameter instead of inline markup tags to avoid orphan [/] errors.
    """
    global _thinking_started, _thinking_style
    c = get_colors()
    if _thinking_style is None:
        _thinking_style = f"dim {c.get('dim_text', '#dbd8d0')}"

    if not _thinking_started:
        console.print("  💭 ", style=_thinking_style, end="")
        _thinking_started = True

    console.print(escape(text), style=_thinking_style, end="")

    # Flush thinking line on newline
    if "\n" in text:
        _thinking_started = False


def on_markdown(console, text):
    """Print a markdown-rendered assistant response."""
    global _thinking_started
    _thinking_started = False
    if text.strip():
        console.print(Markdown(text))


def on_tool_call(console, name, args=None, duration=None):
    """Print tool call with timestamp and JARVIS-style protocol name."""
    ts = datetime.now().strftime("%H:%M:%S")
    args_str = f"({args})" if args else ""
    dur = f" ({duration:.1f}s)" if duration else ""

    c = get_colors()
    tool_color = c.get("tool_call", "#fb923c")
    dim = c.get("dim_text", "#dbd8d0")

    text = RichText()
    text.append(f"  {ts} ", style=f"dim {dim}")
    text.append("  → ", style=f"dim {dim}")
    text.append(protocol_name(name), style=f"bold {tool_color}")
    if args_str:
        text.append(f" {args_str}", style=f"dim {dim}")
    if dur:
        text.append(f" {dur}", style=f"dim {dim}")
    console.print(text)


def on_tool_result(console, content, is_error=False):
    """Print a tool result (collapsed / truncated to 500 chars)."""
    if not content:
        return
    c = get_colors()
    dim = c.get("dim_text", "#dbd8d0")
    style = c.get("accent_error", "#ef4444") if is_error else f"dim {dim}"
    content_str = str(content)[:500]
    if len(str(content)) > 500:
        content_str += "..."
    from rich.markup import escape
    console.print(f"  {escape(content_str)}", style=style)


def on_error(console, text):
    """Print an error in a rich red-bordered Panel (escaped)."""
    from rich.markup import escape
    console.print(Panel(escape(str(text)), title="[red]ERROR[/]", border_style="red"))


def on_info(console, text):
    """Print an info message."""
    console.print(f"  [dim]ℹ {escape(str(text))}[/]")


def on_success(console, text):
    """Print a success message."""
    c = get_colors()
    console.print(f"  [bold {c.get('accent_success', '#84cc16')}]✓ {escape(str(text))}[/]")


def on_warning(console, text):
    """Print a warning in a yellow-bordered Panel (escaped)."""
    from rich.markup import escape
    console.print(Panel(escape(str(text)), title="[yellow]WARNING[/]", border_style="yellow"))


def show_toast(console, message, style="info"):
    """Show a toast-style notification (brief one-liner with icon)."""
    icons = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✖"}
    icon = icons.get(style, "•")
    c = get_colors()
    colors = {
        "info": f"dim {c.get('dim_text', '#dbd8d0')}",
        "success": f"bold {c.get('accent_success', '#84cc16')}",
        "warning": f"bold {c.get('accent_warning', '#fb923c')}",
        "error": f"bold {c.get('accent_error', '#ef4444')}",
    }
    style_str = colors.get(style, f"dim {c.get('dim_text', '#dbd8d0')}")
    console.print(f"  [{style_str}]{icon} {escape(str(message))}[/]")


def protocol_name(name):
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
