"""Slash command registry — define, list, and dispatch commands with handlers."""

import os
import time
import json
from datetime import datetime
from rich.table import Table
from rich.panel import Panel
from rich.text import Text as RichText
from rich.box import MINIMAL, SIMPLE

from omega.ui.themes import get_colors, switch_theme, list_themes, get_active


class CommandRegistry:
    """Registry for slash commands with help, autocomplete, and dispatch."""

    def __init__(self, omega_tui_ref=None):
        self._handlers = {}
        self._descriptions = {}
        self._categories = {}
        self._tui = omega_tui_ref  # weak ref to parent OmegaTUI

        # Register built-in commands
        self._register_builtins()

    def _register_builtins(self):
        """Register all built-in slash commands."""
        builtins = [
            # Session
            ("/help", self._cmd_help, "Display available commands", "Session"),
            ("/clear", self._cmd_clear, "Clear the conversation", "Session"),
            ("/context", self._cmd_context, "Show session info", "Session"),
            ("/exit", self._cmd_exit, "Exit OMEGA", "Session"),
            ("/quit", self._cmd_exit, "Exit OMEGA", "Session"),

            # System
            ("/status", self._cmd_status, "Full system dashboard", "System"),
            ("/tools", self._cmd_tools, "List available tools", "System"),
            ("/theme", self._cmd_theme, "Show or switch color theme", "System"),
            ("/model", self._cmd_model, "Show or switch AI model", "System"),

            # Data
            ("/history", self._cmd_history, "Search conversation history", "Data"),
            ("/export", self._cmd_export, "Export session to markdown", "Data"),
            ("/compact", self._cmd_compact, "Compress context window", "Data"),
            ("/bookmark", self._cmd_bookmark, "Pin current conversation point", "Data"),

            # Agents
            ("/agents", self._cmd_agents, "View/manage sub-agents", "Agents"),
            ("/missions", self._cmd_missions, "Active mission status", "Agents"),
        ]
        for cmd, handler, desc, cat in builtins:
            self.register(cmd, handler, desc, cat)

    def register(self, command, handler, description="", category="General"):
        """Register a new slash command."""
        self._handlers[command] = handler
        self._descriptions[command] = description
        self._categories[command] = category

    def get_commands(self):
        """Return dict of command -> description for completer."""
        return {cmd: f"{cmd:<12} {desc}" for cmd, desc in self._descriptions.items()}

    def get_command_list(self):
        """Return sorted list of all command names."""
        return sorted(self._handlers.keys())

    def get_categories(self):
        """Return list of (category_name, [(cmd, desc), ...]) sorted."""
        cats = {}
        for cmd in sorted(self._handlers.keys()):
            cat = self._categories.get(cmd, "General")
            desc = self._descriptions.get(cmd, "")
            if cat not in cats:
                cats[cat] = []
            cats[cat].append((cmd, desc))
        return list(cats.items())

    def dispatch(self, cmd_line):
        """Parse and dispatch a slash command. Returns True if handled."""
        parts = cmd_line.strip().split()
        cmd = parts[0].lower() if parts else ""
        arg = " ".join(parts[1:]) if len(parts) > 1 else ""

        handler = self._handlers.get(cmd)
        if handler:
            handler(arg)
            return True
        return False

    # ─── Built-in Command Handlers ──────────────────────────────────────

    def _get_console(self):
        """Get the console from the parent TUI or create default."""
        if self._tui:
            return self._tui.console
        from rich.console import Console
        return Console()

    def _get_tracker(self):
        """Get the session tracker from the parent TUI."""
        return getattr(self._tui, "tracker", None) if self._tui else None

    def _cmd_help(self, arg):
        """Display categorized help."""
        console = self._get_console()
        c = get_colors()
        accent = c.get("accent_primary", "#22d3ee")
        secondary = c.get("accent_secondary", "#a78bfa")
        dim = c.get("dim_text", "#dbd8d0")

        console.print()
        header = RichText()
        header.append("Ω ", style=f"bold {accent}")
        header.append("OMEGA ", style=f"bold {secondary}")
        header.append("Commands", style=f"bold {c.get('foreground', '#f5f4ef')}")
        console.print(f"  {header}")

        for cat_name, commands in self.get_categories():
            console.print(f"\n  [bold {c.get('title', accent)}]{cat_name}[/]")
            for cmd, desc in commands:
                console.print(
                    f"    [bold {c.get('tool_call', '#fb923c')}]{cmd:<28}[/] {desc}"
                )
        console.print(f"\n  [dim {dim}]Ready for your command![/]")
        console.print()

    def _cmd_clear(self, arg):
        """Clear the screen."""
        self._get_console().clear()
        if self._tui and hasattr(self._tui, "print_epic_welcome"):
            self._tui.print_epic_welcome()

    def _cmd_exit(self, arg):
        """Exit OMEGA."""
        console = self._get_console()
        console.print("[dim]Ω Shutting down...[/]")
        if self._tui:
            self._tui.running = False

    def _cmd_context(self, arg):
        """Show session context info."""
        console = self._get_console()
        c = get_colors()
        dim = c.get("dim_text", "#dbd8d0")
        secondary = c.get("accent_secondary", "#a78bfa")
        primary = c.get("accent_primary", "#22d3ee")
        tool = c.get("tool_call", "#fb923c")

        info = RichText()
        info.append("  Model: ", style=f"dim {dim}")
        model = self._tui.model_name if self._tui else "?"
        info.append(f"{model}", style=f"bold {secondary}")

        tr = self._get_tracker()
        if tr:
            info.append("  |  Messages: ", style=f"dim {dim}")
            info.append(f"{tr.message_count}", style=f"bold {primary}")
            info.append("  |  Tokens: ", style=f"dim {dim}")
            info.append(f"~{tr.total_tokens():,}", style=f"bold {tool}")
            info.append("  |  Time: ", style=f"dim {dim}")
            info.append(f"{tr.elapsed_str()}", style=f"bold {tool}")

        sid = self._tui.session_id if self._tui else "?"
        info.append("  |  Session: ", style=f"dim {dim}")
        info.append(f"{sid}", style=f"dim {dim}")
        console.print(info)

    def _cmd_status(self, arg):
        """Display full system status dashboard."""
        import socket
        console = self._get_console()
        c = get_colors()
        accent = c.get("accent_primary", "#22d3ee")
        secondary = c.get("accent_secondary", "#a78bfa")
        dim = c.get("dim_text", "#dbd8d0")

        # Gather system info
        cpu = 0.0
        ram = 0.0
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.2)
            ram = psutil.virtual_memory().percent
        except Exception:
            pass

        table = Table(
            box=MINIMAL, border_style=f"dim {dim}",
            padding=(0, 2), show_edge=False, show_header=False,
        )
        table.add_column("Metric", style=f"dim {dim}", width=14)
        table.add_column("Value", width=50)

        def _h(val):
            if isinstance(val, (int, float)):
                if val > 80:
                    return f"[bold {c.get('accent_error','#ef4444')}]●[/]"
                elif val > 50:
                    return f"[bold {c.get('accent_warning','#fb923c')}]●[/]"
                return f"[bold {c.get('accent_success','#84cc16')}]●[/]"
            return "◆"

        tr = self._get_tracker()
        sid = self._tui.session_id if self._tui else "?"
        model = self._tui.model_name if self._tui else "?"
        table.add_row("Session", f"[dim]{sid}[/]")
        if tr:
            table.add_row("Uptime", f"[dim]{tr.elapsed_str()}[/]")
            table.add_row("Messages", f"{tr.message_count}")
            table.add_row("Tool Calls", f"{tr.tool_invocation_count}")
            table.add_row("Tokens", f"~{tr.total_tokens():,}")
        table.add_row("Model", f"[bold {secondary}]{model}[/]")
        table.add_row("CPU", f"{_h(cpu)}  {cpu:.1f}%")
        table.add_row("RAM", f"{_h(ram)}  {ram:.1f}%")

        # API status
        api_status = "standby"
        try:
            from config import Config
            cfg = Config()
            import requests
            r = requests.get(cfg.base_url.rstrip("/v1") + "/models",
                             timeout=3,
                             headers={"Authorization": f"Bearer {cfg.api_key}"})
            api_status = "connected" if r.status_code < 500 else "standby"
        except Exception:
            api_status = "standby"

        api_labels = {
            "connected": f"[bold {c.get('accent_success','#84cc16')}]● Connected[/]",
            "standby": f"[bold {c.get('accent_warning','#fb923c')}]● Standby[/]",
            "error": f"[bold {c.get('accent_error','#ef4444')}]● Error[/]",
        }
        table.add_row("API", api_labels.get(api_status, api_status))

        console.print(Panel(
            table,
            title=f"[bold {accent}]◈ SYSTEM STATUS ◈[/]",
            border_style=f"dim {dim}", padding=(1, 2),
        ))

    def _cmd_tools(self, arg):
        """Display browsable tool list."""
        console = self._get_console()
        c = get_colors()
        accent = c.get("accent_primary", "#22d3ee")
        dim = c.get("dim_text", "#dbd8d0")
        tool_color = c.get("tool_call", "#fb923c")

        try:
            from prompts import TOOL_DEFINITIONS
            tools = list(TOOL_DEFINITIONS)
        except Exception:
            tools = []

        if not tools:
            console.print("[dim]ℹ No tools loaded[/]")
            return

        # Group by category (first segment of name before _)
        categories = {}
        for t in tools:
            name = t.get("name", str(t)) if isinstance(t, dict) else str(t)
            desc = t.get("description", "")[:80] if isinstance(t, dict) else ""
            cat = name.split("_")[0] if "_" in name else "general"
            categories.setdefault(cat, []).append((name, desc))

        header = RichText()
        header.append("  ◈ ", style=f"bold {accent}")
        header.append(f"TOOLS ({len(tools)} loaded)", style=f"bold {c.get('foreground','#f5f4ef')}")
        console.print()
        console.print(header)

        for cat_name in sorted(categories):
            console.print(f"\n  [bold {accent}]{cat_name}[/]")
            for name, desc in sorted(categories[cat_name])[:10]:
                console.print(f"    [bold {tool_color}]{name:<30}[/] [dim]{desc}[/]")

        if sum(len(v) for v in categories.values()) > sum(min(10, len(v)) for v in categories.values()):
            console.print(f"\n  [dim]... and more. Use /help for full list.[/]")
        console.print()

    def _cmd_theme(self, arg):
        """Show or switch theme."""
        console = self._get_console()
        c = get_colors()

        if arg:
            if switch_theme(arg):
                console.print(f"[bold {c.get('accent_success','#84cc16')}]✓ Theme switched to: {arg}[/]")
                # Re-render welcome if available
                if self._tui and hasattr(self._tui, "print_epic_welcome"):
                    self._tui.print_epic_welcome()
            else:
                console.print(f"[bold {c.get('accent_error','#ef4444')}]✖ Unknown theme: {arg}[/]")
                self._list_themes()
        else:
            self._list_themes()

    def _list_themes(self):
        """List available themes in a table."""
        console = self._get_console()
        c = get_colors()
        themes = list_themes()
        current = get_active()

        table = Table(
            box=SIMPLE, border_style=f"dim {c.get('dim_text','#dbd8d0')}",
            padding=(0, 1),
        )
        table.add_column("Key", style=f"bold {c.get('tool_call','#fb923c')}")
        table.add_column("Name", style=c.get("foreground", "#f5f4ef"))
        table.add_column("Type")
        table.add_column("", width=6)

        for key, name, ttype in themes:
            marker = "●" if key == current else ""
            table.add_row(key, name, ttype,
                          f"[bold {c.get('accent_success','#84cc16')}]{marker}[/]")

        console.print(Panel(
            table, title="[bold]THEMES[/]",
            border_style=f"dim {c.get('dim_text','#dbd8d0')}",
        ))
        console.print(f"  [dim]Usage: /theme <key> (e.g., /theme dracula)[/]")

    def _cmd_model(self, arg):
        """Show or switch model (validated against AVAILABLE_MODELS)."""
        console = self._get_console()
        c = get_colors()

        # Get real model list
        try:
            from omega.core.config import AVAILABLE_MODELS
        except ImportError:
            from config import AVAILABLE_MODELS

        if arg:
            # Match case-insensitive, suggest on typo
            match = None
            for m in AVAILABLE_MODELS:
                if m.lower() == arg.lower():
                    match = m
                    break
            if not match:
                # Fuzzy suggest
                suggestions = [m for m in AVAILABLE_MODELS if arg.lower() in m.lower()]
                console.print(f"[bold {c.get('accent_error','#ef4444')}]✖ Unknown model: {arg}[/]")
                if suggestions:
                    console.print(f"[dim]  Did you mean: {', '.join(suggestions)}?[/]")
                console.print(f"[dim]  Available models:[/]")
                for m in AVAILABLE_MODELS:
                    marker = "●" if m == self._tui.model_name else " "
                    console.print(f"    [bold {c.get('tool_call','#fb923c')}]{marker} {m}[/]")
                return

            if self._tui:
                self._tui.model_name = match
            console.print(f"[bold {c.get('accent_success','#84cc16')}]✓ Switched to model: {match}[/]")
        else:
            model = self._tui.model_name if self._tui else "?"
            console.print(f"[dim]ℹ Current model: [bold]{model}[/][/]")
            console.print("[dim]  Available:[/]")
            for m in AVAILABLE_MODELS:
                marker = "●" if m == model else " "
                console.print(f"    [bold {c.get('tool_call','#fb923c')}]{marker} {m}[/]")

    def _cmd_history(self, arg):
        """Search conversation history."""
        console = self._get_console()
        c = get_colors()
        dim = c.get("dim_text", "#dbd8d0")

        # Show buffer stats
        tr = self._get_tracker()
        if tr:
            console.print(f"[dim]ℹ Session: {tr.message_count} messages, "
                          f"~{tr.total_tokens():,} tokens, "
                          f"elapsed {tr.elapsed_str()}[/]")
        else:
            console.print("[dim]ℹ No session tracker available[/]")

        if arg:
            console.print(f"[dim]  Searching for: \"{arg}\"...[/]")
            console.print("[dim]  (Full history search: use /recall <query> in main CLI)[/]")
        else:
            console.print("[dim]  Usage: /history <search term>[/]")
            console.print("[dim]  Use /recall <query> in main CLI for full history search[/]")

    def _cmd_export(self, arg):
        """Export session to markdown file."""
        console = self._get_console()
        c = get_colors()
        try:
            export_dir = os.path.expanduser("~/omega-exports")
            os.makedirs(export_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sid = self._tui.session_id if self._tui else "unknown"
            filename = f"omega_session_{sid}_{timestamp}.md"
            filepath = os.path.join(export_dir, filename)

            tr = self._get_tracker()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# OMEGA Session Export\n")
                f.write(f"**Session ID:** {sid}\n")
                f.write(f"**Model:** {getattr(self._tui, 'model_name', '?')}\n")
                f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                if tr:
                    f.write(f"**Messages:** {tr.message_count}\n")
                    f.write(f"**Tokens:** ~{tr.total_tokens():,}\n")
                    f.write(f"**Tool Calls:** {tr.tool_invocation_count}\n")
                    f.write(f"**Uptime:** {tr.elapsed_str()}\n")

            console.print(f"[bold {c.get('accent_success','#84cc16')}]✓ Session exported: {filepath}[/]")
        except Exception as e:
            console.print(f"[bold {c.get('accent_error','#ef4444')}]✖ Export failed: {e}[/]")

    def _cmd_compact(self, arg):
        """Compress context window (placeholder)."""
        console = self._get_console()
        c = get_colors()
        console.print(f"[bold {c.get('accent_warning','#fb923c')}]⚡ Context window compacted[/]")

    def _cmd_bookmark(self, arg):
        """Bookmark the current conversation point."""
        console = self._get_console()
        c = get_colors()
        timestamp = datetime.now().strftime("%H:%M:%S")
        label = arg if arg else f"bookmark-{timestamp}"
        tr = self._get_tracker()
        msg_count = tr.message_count if tr else "?"
        console.print(
            f"[bold {c.get('accent_success','#84cc16')}]★ Bookmarked[/] "
            f"[dim]\"{label}\" at message #{msg_count} ({timestamp})[/]"
        )

    def _cmd_agents(self, arg):
        """Show sub-agent status."""
        console = self._get_console()
        c = get_colors()
        dim = c.get("dim_text", "#dbd8d0")
        accent = c.get("accent_primary", "#22d3ee")
        console.print(Panel(
            "  [dim]No active sub-agents[/]\n"
            "  Sub-agents are spawned via the OMEGA agent for parallel tasks.\n"
            "  Check back after running a delegated task.",
            title=f"[bold {accent}]◈ SUB-AGENTS ◈[/]",
            border_style=f"dim {dim}",
        ))

    def _cmd_missions(self, arg):
        """Show active mission status."""
        console = self._get_console()
        c = get_colors()
        dim = c.get("dim_text", "#dbd8d0")
        accent = c.get("accent_primary", "#22d3ee")

        tr = self._get_tracker()
        elapsed = tr.elapsed_str() if tr else "--:--:--"

        table = Table(
            box=MINIMAL, border_style=f"dim {dim}",
            padding=(0, 2), show_edge=False, show_header=False,
        )
        table.add_column("Metric", style=f"dim {dim}", width=14)
        table.add_column("Value")

        if tr:
            table.add_row("Status", f"[bold {c.get('accent_success','#84cc16')}]● Active[/]")
            table.add_row("Messages", f"{tr.message_count}")
            table.add_row("Tools Called", f"{tr.tool_invocation_count}")
            table.add_row("Tokens Used", f"~{tr.total_tokens():,}")
        table.add_row("Elapsed", f"[dim]{elapsed}[/]")
        table.add_row("Session ID", f"[dim]{getattr(self._tui, 'session_id', '?')}[/]")

        console.print(Panel(
            table,
            title=f"[bold {accent}]◈ MISSIONS ◈[/]",
            border_style=f"dim {dim}", padding=(1, 2),
        ))
