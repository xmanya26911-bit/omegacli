#!/usr/bin/env python3
"""OMEGA TUI — rich Console + prompt_toolkit PromptSession + asyncio.

Architecture:
  - rich.Console for ALL output (Markdown, Syntax, Panel, Spinner)
  - prompt_toolkit.PromptSession for async input with history + completer
  - asyncio event loop ties them together
  - Agent runs in a thread, patched cli functions call Console directly

This is clean. No ANSI conversion hacks. No FormattedTextControl fight.
"""

import sys
import os
import time
import threading
import asyncio
from io import StringIO
from datetime import datetime

# Fix Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        os.environ["PYTHONIOENCODING"] = "utf-8"

# rich
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text as RichText
from rich.style import Style as RichStyle
from rich.syntax import Syntax
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner

# prompt_toolkit — for input only
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

# ─── Claude Design System Colors ─────────────────────────────────────────────
CLAY = "#d97757"
MUTED = "#b8b5a9"
DIM = "#a6a39a"
TEXT = "#f5f4ef"
BG = "#262624"
SURFACE = "#2c2b28"
BORDER = "#3b3b38"
RED = "#ef4444"
GREEN = "#84cc16"
BLUE = "#60a5fa"

# ─── Claude Code-style "rich" console theme ──────────────────────────────────
CLAUDE_STYLE = RichStyle(bgcolor=BG)

def make_console():
    """Create a Console with Claude Code dark theme."""
    return Console(
        force_terminal=True,
        color_system="truecolor",
    )

# ─── Conversation Log ────────────────────────────────────────────────────────
# We keep a simple list of messages so we can re-display them on /clear, etc.
# But output is printed directly via Console — no fragment buffer needed.


# ═══════════════════════════════════════════════════════════════════════════════
# CLAUDE TUI — rich Console + PromptSession
# ═══════════════════════════════════════════════════════════════════════════════

class ClaudeTUI:
    """Claude Code-style TUI using rich Console + prompt_toolkit PromptSession.

    Output: rich.Console (Markdown, Syntax, Panel, Spinner)
    Input: prompt_toolkit.PromptSession (async, history, WordCompleter)
    Concurrency: asyncio event loop + threaded agent execution
    """

    def __init__(self, model_name="omega"):
        self.model_name = model_name
        self.console = make_console()
        # PromptSession — works in PowerShell/cmd.exe, needs fallback for MSYS
        try:
            self.session = PromptSession(
                history=FileHistory(
                    os.path.join(os.path.expanduser("~"), ".omega_history")
                ),
                completer=WordCompleter(
                    ["/help", "/clear", "/exit", "/quit", "/context"],
                    ignore_case=True,
                    display_dict={
                        "/help": "/help     Display available commands",
                        "/clear": "/clear    Clear the conversation",
                        "/exit": "/exit     Exit OMEGA",
                        "/quit": "/quit     Exit OMEGA",
                        "/context": "/context  Show session info",
                    },
                ),
                auto_suggest=AutoSuggestFromHistory(),
            )
            self._use_prompt_session = True
        except Exception:
            # Fallback: use builtins.input for MSYS/Cygwin environments
            self._use_prompt_session = False
            self.session = None
            self.console.print("[yellow]⚠ PromptSession unavailable, using basic input[/]")
        self.running = True
        self.message_count = 0
        self.session_start = time.time()

    def run(self, agent):
        """Sync entry point (delegates to async)."""
        asyncio.run(self._run(agent))

    async def _run(self, agent):
        """Main async loop — rich output + PromptSession input."""
        # ── Welcome ──
        from prompts import TOOL_DEFINITIONS
        try:
            tool_count = len(TOOL_DEFINITIONS)
        except Exception:
            tool_count = 0
        self.console.print(f"[dim]OMEGA · {self.model_name}[/]")
        self.console.print(f"[dim]Loaded {tool_count} tools · Type a message or /help for commands[/]")
        self.console.print()

        # ── Main Loop ──
        while self.running:
            try:
                if self._use_prompt_session:
                    user_input = await self.session.prompt_async("› ")
                else:
                    # Fallback for MSYS/bash environments
                    user_input = await asyncio.to_thread(input, "› ")
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # Handle slash commands BEFORE agent processing
            if user_input.startswith("/"):
                await self._handle_command(user_input)
                continue

            # ── Display user message ──
            self.console.print()
            self.console.print(f"[bold {CLAY}]┃ You[/]")
            self.console.print(f"  {user_input}")
            self.console.print(f"[bold {CLAY}]┃ OMEGA[/]")

            # ── Run agent in thread (it's sync) ──
            self.message_count += 1
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_agent_once, agent, user_input)

            self.console.print()

        # ── Shutdown ──
        self.console.print("[dim]OMEGA shut down[/]")

    # ─── Agent Execution ─────────────────────────────────────────────────────

    def _run_agent_once(self, agent, user_input):
        """Run agent.run_once() with patched cli functions."""
        import cli

        # Save originals
        _orig = {}
        _patches = {
            "print_user_input": lambda t: None,  # already displayed
            "print_assistant_header": lambda: None,
            "print_assistant_thinking": self._on_chunk,
            "print_assistant_message": self._on_markdown,
            "print_thinking_block": self._on_markdown,
            "print_thinking_start": lambda: None,  # header already shown
            "print_thinking_busy": lambda: None,
            "print_thinking_done": lambda: None,
            "print_tool_call": self._on_tool_call,
            "print_tool_result": self._on_tool_result,
            "print_error": self._on_error,
            "print_info": self._on_info,
            "print_success": self._on_success,
            "print_warning": self._on_warning,
        }

        for name, func in _patches.items():
            if hasattr(cli, name):
                _orig[name] = getattr(cli, name)
                setattr(cli, name, func)

        # Also patch agent module's local copies
        import agent as agent_mod
        for name, func in _patches.items():
            if hasattr(agent_mod, name):
                setattr(agent_mod, name, func)

        # Suppress welcome banner
        _orig["print_welcome"] = cli.print_welcome
        cli.print_welcome = lambda *a, **kw: None

        try:
            agent.run_once(user_input)
        except Exception as e:
            self.console.print(Panel(
                str(e),
                title="[red]ERROR[/]",
                border_style="red",
            ))
        finally:
            for name, func in _orig.items():
                setattr(cli, name, func)
                if hasattr(agent_mod, name):
                    setattr(agent_mod, name, func)

    # ─── Output Handlers (called from agent thread) ──────────────────────────

    def _on_chunk(self, text):
        """Print a streaming thinking chunk."""
        end = "" if text.endswith("\n") else ""
        self.console.print(text, end=end)

    def _on_markdown(self, text):
        """Print a markdown-rendered assistant response."""
        if text.strip():
            self.console.print(Markdown(text))

    def _on_tool_call(self, name, args=None, duration=None):
        """Print a tool call indicator."""
        args_str = f"({args})" if args else ""
        dur = f" ({duration:.1f}s)" if duration else ""
        self.console.print(f"  [dim]→ {name}{args_str}{dur}[/]")

    def _on_tool_result(self, content, is_error=False):
        """Print a tool result (collapsed / truncated)."""
        if content:
            prefix = "[dim]" if not is_error else "[red]"
            content_str = str(content)[:500]
            if len(str(content)) > 500:
                content_str += "..."
            self.console.print(f"  {prefix}{content_str}[/]")

    def _on_error(self, text):
        """Print an error in a rich red-bordered Panel."""
        self.console.print(Panel(
            str(text),
            title="[red]ERROR[/]",
            border_style="red",
        ))

    def _on_info(self, text):
        """Print an info message."""
        self.console.print(f"[dim]ℹ {text}[/]")

    def _on_success(self, text):
        """Print a success message."""
        self.console.print(f"[dim]✓ {text}[/]")

    def _on_warning(self, text):
        """Print a warning."""
        self.console.print(Panel(
            str(text),
            title="[yellow]WARNING[/]",
            border_style="yellow",
        ))

    # ─── Slash Commands ─────────────────────────────────────────────────────

    async def _handle_command(self, cmd_line):
        """Handle slash commands."""
        cmd = cmd_line.lower().split()[0]
        if cmd in ("/exit", "/quit"):
            self.console.print("[dim]Shutting down...[/]")
            self.running = False
        elif cmd == "/clear":
            self.console.clear()
        elif cmd == "/help":
            self.console.print(Panel(
                "[bold]Available commands[/]\n\n"
                "  [bold]/help[/]     Show this help\n"
                "  [bold]/clear[/]    Clear the screen\n"
                "  [bold]/exit[/]     Exit OMEGA\n"
                "  [bold]/quit[/]     Exit OMEGA\n"
                "  [bold]/context[/]  Show session info\n",
                title="Help",
                border_style=CLAY,
            ))
        elif cmd == "/context":
            elapsed = int(time.time() - self.session_start)
            self.console.print(
                f"[dim]Model: {self.model_name}  "
                f"Messages: {self.message_count}  "
                f"Time: {elapsed // 60}m{elapsed % 60:02d}s[/]"
            )
        else:
            self.console.print(f"[dim]Unknown command: {cmd}. Type /help for commands.[/]")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def run_tui(agent):
    """Run the TUI with the given agent.

    Called from main.py when TUI mode is enabled.
    """
    model = agent.config.model if hasattr(agent, "config") else "omega"
    tui = ClaudeTUI(model_name=model)
    tui.run(agent)


if __name__ == "__main__":
    print("OMEGA TUI — testing mode")
    print("Import this module from main.py to use the TUI.")
