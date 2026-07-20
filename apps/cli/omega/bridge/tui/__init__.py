"""
Supervisor TUI — Live multi-agent dashboard.

Shows:
    - Live scrolling feed of agent messages
    - Task progress bars
    - Connected agent status indicators
    - Approval request popups
    - Input prompt for the user

Built on top of OMEGA's existing UI components (themes, prompt bar, etc.).
"""
from __future__ import annotations

import queue
import sys
import threading
import time
from datetime import datetime
from typing import Any

from omega.bridge.protocol.message import AgentMessage
from omega.bridge.protocol.event_types import EventType
from omega.bridge.bus.event_bus import EventBus
from omega.bridge.supervisor.core import Supervisor

# ── Styling Constants ───────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Agent colors
COLORS = {
    "Supervisor": "\033[38;5;220m",   # Gold
    "Omega":      "\033[38;5;75m",    # Blue
    "Hermes":     "\033[38;5;82m",    # Green
    "User":       "\033[38;5;245m",   # Gray
    "System":     "\033[38;5;240m",   # Dark gray
    "Error":      "\033[38;5;196m",   # Red
    "Success":    "\033[38;5;46m",    # Bright green
}

AGENT_EVENT_STYLES = {
    EventType.TASK_CREATED: ("System", "📋"),
    EventType.TASK_ASSIGNED: ("Supervisor", "🎯"),
    EventType.PLAN_READY: ("Omega", "📐"),
    EventType.CODE_FINISHED: ("Hermes", "✅"),
    EventType.AGENT_QUESTION: ("System", "❓"),
    EventType.AGENT_FEEDBACK: ("System", "💬"),
    EventType.AGENT_PROPOSAL: ("System", "💡"),
    EventType.AGENT_BLOCKED: ("Error", "🚫"),
    EventType.AGENT_CONNECTED: ("Success", "🔗"),
    EventType.AGENT_DISCONNECTED: ("System", "🔌"),
    EventType.APPROVAL_NEEDED: ("Supervisor", "⚠️"),
    EventType.SESSION_END: ("Success", "🏁"),
    EventType.USER_MESSAGE: ("User", "👤"),
    EventType.SYSTEM_LOG: ("System", "ℹ️"),
}

DEFAULT_EVENT_STYLE = ("System", "•")


class SupervisorTUI:
    """Terminal UI for the Supervisor multi-agent system.

    Displays a live feed of agent messages and task progress.
    Designed for scrolling rich terminal (not full-screen TUI).
    """

    def __init__(self, supervisor: Supervisor, bus: EventBus,
                 show_progress: bool = True):
        self.supervisor = supervisor
        self.bus = bus
        self.show_progress = show_progress
        self._message_queue: queue.Queue[tuple[str, AgentMessage]] = queue.Queue()
        self._running = False
        self._start_time = time.time()

        # Subscribe to all events for display
        self.bus.subscribe("*", self._on_event)

    # ── Event Handling ────────────────────────────────────────────

    def _on_event(self, event_type: str, msg: AgentMessage) -> None:
        """Queue incoming events for TUI display."""
        if self._running:
            self._message_queue.put((event_type, msg))

    # ── Rendering ─────────────────────────────────────────────────

    def render_message(self, event_type: str, msg: AgentMessage) -> str:
        """Format a single message line for display."""
        style_key, icon = AGENT_EVENT_STYLES.get(event_type, DEFAULT_EVENT_STYLE)
        color = COLORS.get(style_key, COLORS["System"])

        # Truncate content for single-line display
        content = msg.content.replace("\n", " | ")[:120]
        if len(msg.content) > 120:
            content += "..."

        agent_label = f"{msg.from_agent:10}"
        ts = datetime.now().strftime("%H:%M:%S")

        return (
            f"{DIM}{ts}{RESET} "
            f"{color}{icon}{RESET} "
            f"{BOLD}{color}{agent_label}{RESET} "
            f"{content}"
        )

    def render_task_progress(self) -> str:
        """Render task progress bars as text."""
        if not self.show_progress:
            return ""

        tasks = self.supervisor.get_task_summary()
        if not tasks:
            return ""

        lines = [f"{DIM}{'─'*60}{RESET}"]
        lines.append(f"{BOLD}📋 Active Tasks{RESET}")

        for t in tasks:
            status_icon = {
                "pending": "⏳",
                "assigned": "🎯",
                "in_progress": "🔄",
                "blocked": "🚫",
                "done": "✅",
                "failed": "❌",
                "cancelled": "⛔",
            }.get(t["status"], "⏳")

            bar_width = 20
            done = t["status"] == "done"
            filled = bar_width if done else 0
            bar = "█" * filled + "░" * (bar_width - filled)

            agent = t["agent"] or "—"
            desc = t["description"][:50]

            lines.append(
                f"  {status_icon} "
                f"{COLORS.get(t['role'], DIM)}{t['id']:4}{RESET} "
                f"{DIM}{t['role']:12}{RESET} "
                f"{bar} "
                f"{BOLD}{'100%' if done else f'{filled*5:3}%'}{RESET} "
                f"{DIM}{agent:8}{RESET} "
                f"{desc}"
            )

        lines.append(f"{DIM}{'─'*60}{RESET}")
        return "\n".join(lines)

    def render_agent_status(self) -> str:
        """Render connected agent indicators."""
        agents = self.bus.get_connected_agents()
        if not agents:
            return ""

        statuses = []
        for agent in agents:
            color = COLORS.get(agent, DIM)
            statuses.append(f"{color}●{RESET} {agent}")

        return f"{'  '.join(statuses)}"

    def render_footer(self) -> str:
        """Render footer with session info."""
        stats = self.supervisor.get_stats()
        elapsed = time.time() - self._start_time
        time_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"

        parts = [
            f"{DIM}Session: {stats['session_id'][:12]}{RESET}",
            f"{DIM}⏱ {time_str}{RESET}",
            f"{DIM}Messages: {stats['message_count']}{RESET}",
            f"{DIM}Tasks: {stats['done_tasks']}/{stats['total_tasks']}{RESET}",
        ]

        agents_str = self.render_agent_status()
        if agents_str:
            parts.append(agents_str)

        return "  │  ".join(parts)

    # ── Main Loop ─────────────────────────────────────────────────

    def run(self) -> None:
        """Run the TUI event loop. Blocks until done."""
        self._running = True
        pending_queue: list[tuple[str, AgentMessage]] = []

        print()
        self._print_header()
        print()

        try:
            while self._running:
                # Drain message queue
                while not self._message_queue.empty():
                    try:
                        event_type, msg = self._message_queue.get_nowait()
                        pending_queue.append((event_type, msg))
                    except queue.Empty:
                        break

                # Render new messages
                for event_type, msg in pending_queue:
                    line = self.render_message(event_type, msg)
                    print(line)

                # Show task progress periodically
                if pending_queue and self.show_progress:
                    progress = self.render_task_progress()
                    if progress:
                        print()
                        print(progress)
                        print()

                # Render footer
                if pending_queue:
                    footer = self.render_footer()
                    print(footer)

                # Clear pending queue
                pending_queue.clear()

                # Check if session is done
                stats = self.supervisor.get_stats()
                if (stats["total_tasks"] > 0
                        and stats["done_tasks"] == stats["total_tasks"]):
                    self._print_session_end(stats)
                    break

                # Sleep to avoid busy-waiting
                time.sleep(0.1)

        except KeyboardInterrupt:
            self._print_shutdown()

        self._running = False

    def _print_header(self) -> None:
        """Print the supervisor header."""
        print(f"{BOLD}{COLORS['Supervisor']}╔══════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{COLORS['Supervisor']}║     OMEGA SUPERVISOR — Multi-Agent System     ║{RESET}")
        print(f"{BOLD}{COLORS['Supervisor']}╚══════════════════════════════════════════════╝{RESET}")
        print(f"{DIM}  Hermes + Omega working together. You watch live.{RESET}")

    def _print_session_end(self, stats: dict[str, Any]) -> None:
        """Print session summary."""
        print()
        print(f"{COLORS['Success']}{'='*60}{RESET}")
        print(f"{BOLD}{COLORS['Success']}🏁 Session Complete{RESET}")
        print(f"  {DIM}Tasks: {stats['done_tasks']}/{stats['total_tasks']}{RESET}")
        print(f"  {DIM}Messages: {stats['message_count']}{RESET}")
        print(f"  {DIM}Time: {stats['elapsed']}s{RESET}")
        print(f"{COLORS['Success']}{'='*60}{RESET}")
        print()

    def _print_shutdown(self) -> None:
        """Print shutdown message."""
        print(f"\n{DIM}Supervisor shutting down...{RESET}")

    def stop(self) -> None:
        """Signal the TUI loop to stop."""
        self._running = False
