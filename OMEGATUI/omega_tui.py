#!/usr/bin/env python3
"""OMEGA TUI — Modular UI coordinator.

Phases implemented:
  Phase 1: Epic Welcome Screen        → omega/ui/welcome.py
  Phase 2: Premium Input Bar          → omega/ui/prompt_bar.py
  Phase 3: Live Status Ticker         → omega/ui/status.py + omega/ui/message.py
  Phase 4: Beautiful Message Display  → omega/ui/message.py
  Phase 5: Smart Slash Commands       → omega/ui/commands.py
  Phase 6: Theme System Upgrade       → cli.py themes + omega/ui/themes.py
  Phase 7: Smart Features             → prompt_bar keybindings, auto-save, toasts
  Phase 8: Architecture Cleanup       → split into omega/ui/ modules

This module is the thin coordinator — all logic lives in omega/ui/*.py.
"""

import sys
import os
import asyncio
import time
import uuid
from datetime import datetime

from rich.console import Console
from rich.style import Style as RichStyle
from rich.markdown import Markdown
from rich.panel import Panel

from prompt_toolkit.formatted_text import FormattedText

from omega.ui import (
    get_colors,
    make_prompt_prefix,
    make_bottom_toolbar,
    display_user_message,
    display_assistant_header,
    on_tool_call as ui_tool_call,
    on_tool_result as ui_tool_result,
    on_markdown,
    on_chunk,
    on_error,
    on_info,
    on_success,
    on_warning,
    protocol_name,
    SessionTracker,
    CommandRegistry,
    print_epic_welcome,
)
from omega.ui.prompt_bar import build_prompt_session, build_default_commands

# Fix Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        os.environ["PYTHONIOENCODING"] = "utf-8"

# ─── Console ─────────────────────────────────────────────────────────────────

def make_console():
    return Console(force_terminal=True, color_system="truecolor")


# ═══════════════════════════════════════════════════════════════════════════════
# OMEGA TUI — INTEGRATION LAYER
# ═══════════════════════════════════════════════════════════════════════════════

class OmegaTUI:
    """OMEGA TUI — coordinates all omega/ui/ modules into a cohesive app."""

    def __init__(self, model_name="omega", tool_count=0):
        self.model_name = model_name
        self.tool_count = tool_count
        self.console = make_console()
        self.running = True
        self.session_id = str(uuid.uuid4())[:8]
        self.session_start = time.time()

        # Session tracker (Phase 3 stats)
        self.tracker = SessionTracker()

        # Command registry (Phase 5)
        self.commands = CommandRegistry(omega_tui_ref=self)

        # Build prompt session (Phase 2)
        cmd_list = self.commands.get_command_list()
        cmd_display = self.commands.get_commands()
        self.session, self._use_prompt_session = build_prompt_session(
            cmd_list, cmd_display, omega_ref=self,
        )

        # Auto-transcript
        self._transcript_path = None
        self._auto_transcript = True

        # Message buffer (rolling window, Phase 7/8)
        self._message_buffer = []
        self._buffer_max = 200

    # ═══════════════════════════════════════════════════════════════════════════
    # RUN
    # ═══════════════════════════════════════════════════════════════════════════

    def run(self, agent):
        """Sync entry point (delegates to async)."""
        asyncio.run(self._run(agent))

    async def _run(self, agent):
        """Main async loop."""
        # Phase 1: Epic Welcome
        print_epic_welcome(
            self.console, self.model_name,
            self.tool_count, self.session_id,
        )

        # Start auto-transcript
        self._start_transcript()

        # Phase 2: Main loop with premium input bar
        while self.running:
            try:
                c = get_colors()
                prefix = make_prompt_prefix()
                toolbar = make_bottom_toolbar(
                    self.tracker.message_count,
                    self.session_id,
                    self.session_start,
                )

                if self._use_prompt_session:
                    user_input = await self.session.prompt_async(
                        prefix, bottom_toolbar=toolbar,
                    )
                else:
                    user_input = await asyncio.to_thread(input, "Ω omega > ")
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            # Phase 5: Dispatch slash commands
            if user_input.startswith("/"):
                if not self.commands.dispatch(user_input):
                    self.console.print("[dim]ℹ Unknown command. Type /help[/]")
                continue

            # Phase 4: Display user message
            self.console.print()
            display_user_message(self.console, user_input)

            # Phase 7: Track input tokens
            self.tracker.record_token_input(user_input)
            self.tracker.message_count += 1
            self._buffer_append("user", user_input)

            # Run agent
            self.console.print()
            display_assistant_header(self.console)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_agent_once, agent, user_input)

            # Phase 3: Response footer (status ticker)
            from omega.ui.message import display_response_footer
            display_response_footer(self.console, self.tracker)

        # ── Shutdown ──
        self._close_transcript()
        self.console.print(f"[dim]Ω OMEGA shut down. Session [{self.session_id}][/]")

    # ═══════════════════════════════════════════════════════════════════════════
    # AGENT EXECUTION (with patch system)
    # ═══════════════════════════════════════════════════════════════════════════

    def _run_agent_once(self, agent, user_input):
        """Run agent.run_once() with patched cli functions."""
        import cli

        _orig = {}
        _patches = {
            "print_user_input": lambda t: None,
            "print_assistant_header": lambda: None,
            "print_assistant_thinking": self._on_chunk,
            "print_assistant_message": self._on_markdown,
            "print_thinking_block": self._on_markdown,
            "print_thinking_start": lambda: None,
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

        import agent as agent_mod
        for name, func in _patches.items():
            if hasattr(agent_mod, name):
                setattr(agent_mod, name, func)

        _orig["print_welcome"] = cli.print_welcome
        cli.print_welcome = lambda *a, **kw: None

        try:
            agent.run_once(user_input)
        except Exception as e:
            from rich.text import Text as RichText
            from omega.ui.message import _thinking_started as _ts
            # Reset thinking state so Rich tags don't leak
            import omega.ui.message as _msg
            if _msg._thinking_started:
                _msg._thinking_started = False
            # Use escape() to prevent Rich markup parsing in error messages
            from rich.markup import escape
            self.console.print(Panel(escape(str(e)), title="[red]ERROR[/]", border_style="red"))
        finally:
            for name, func in _orig.items():
                setattr(cli, name, func)
                if hasattr(agent_mod, name):
                    setattr(agent_mod, name, func)

    # ─── Output Handlers ─────────────────────────────────────────────────

    def _on_chunk(self, text):
        on_chunk(self.console, text)

    def _on_markdown(self, text):
        on_markdown(self.console, text)
        if text.strip():
            self.tracker.record_token_output(text)

    def _on_tool_call(self, name, args=None, duration=None):
        ui_tool_call(self.console, name, args, duration)
        self.tracker.record_tool_call(name, duration)

    def _on_tool_result(self, content, is_error=False):
        ui_tool_result(self.console, content, is_error)

    def _on_error(self, text):
        self._buffer_append("error", text)
        on_error(self.console, text)

    def _on_info(self, text):
        on_info(self.console, text)

    def _on_success(self, text):
        on_success(self.console, text)

    def _on_warning(self, text):
        on_warning(self.console, text)

    # ─── Buffer & Transcript (Phase 7) ───────────────────────────────────

    def print_epic_welcome(self):
        """Re-display welcome screen (used by /clear)."""
        print_epic_welcome(
            self.console, self.model_name,
            self.tool_count, self.session_id,
        )

    def _buffer_append(self, role, content):
        """Append a message to the rolling buffer."""
        self._message_buffer.append({
            "role": role,
            "content": content,
            "time": time.time(),
        })
        if len(self._message_buffer) > self._buffer_max:
            self._message_buffer = self._message_buffer[-self._buffer_max:]

    def _start_transcript(self):
        """Start auto-saving session transcript."""
        if not self._auto_transcript:
            return
        try:
            export_dir = os.path.expanduser("~/omega-exports")
            os.makedirs(export_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._transcript_path = os.path.join(
                export_dir, f"transcript_{self.session_id}_{ts}.md",
            )
            with open(self._transcript_path, "w", encoding="utf-8") as f:
                f.write(f"# OMEGA Transcript — Session {self.session_id}\n")
                f.write(f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Model:** {self.model_name}\n\n")
                f.write("*Transcripting active...*\n\n")
        except Exception:
            self._transcript_path = None

    def _close_transcript(self):
        """Finalize transcript on shutdown."""
        if self._transcript_path and os.path.isfile(self._transcript_path):
            try:
                with open(self._transcript_path, "a", encoding="utf-8") as f:
                    f.write(f"\n---\n**Ended:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"**Messages:** {self.tracker.message_count}\n")
                    f.write(f"**Tokens:** ~{self.tracker.total_tokens():,}\n")
                    f.write(f"**Tools Called:** {self.tracker.tool_invocation_count}\n")
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def run_tui(agent):
    """Run the TUI with the given agent. Called from main.py."""
    model = agent.config.model if hasattr(agent, "config") else "omega"
    try:
        from prompts import TOOL_DEFINITIONS
        tool_count = len(TOOL_DEFINITIONS)
    except Exception:
        tool_count = 0

    tui = OmegaTUI(model_name=model, tool_count=tool_count)
    tui.run(agent)


if __name__ == "__main__":
    print("OMEGA TUI — Modular Edition")
    print("Import this module from main.py to use the TUI.")
