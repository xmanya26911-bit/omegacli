#!/usr/bin/env python3
"""
omega.bridge.__main__ — Entry point for the Supervisor multi-agent system.

Usage:
    python -m omega.bridge                           # Interactive supervisor mode
    python -m omega.bridge "Build a weather app"     # Single prompt mode
    python -m omega.bridge --all "Build a weather app"  # Supervisor + Omega + WS
    python -m omega.bridge --no-llm                  # Rule-based decomposition only
    python -m omega.bridge --headless                # No TUI, just log
    python -m omega.bridge --ws-only                 # WebSocket server only
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time


def main():
    parser = argparse.ArgumentParser(
        description="OMEGA Supervisor — Multi-Agent System",
    )
    parser.add_argument("prompt", nargs="*", help="User prompt (omit for interactive)")
    parser.add_argument("--all", action="store_true",
                        help="Start Supervisor + Omega agent + WebSocket in one process")
    parser.add_argument("--no-llm", action="store_true",
                        help="Use rule-based task decomposition (no LLM call)")
    parser.add_argument("--headless", action="store_true",
                        help="No TUI, just log events")
    parser.add_argument("--ws-only", action="store_true",
                        help="Start WebSocket server only (for Hermes to connect)")
    parser.add_argument("--port", type=int, default=9876,
                        help="WebSocket server port (default: 9876)")
    parser.add_argument("--log-dir", default="",
                        help="Log directory (default: omega/bridge/logs)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")

    args = parser.parse_args()

    # Logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s [%(name)s] %(message)s",
        stream=sys.stderr,
    )

    # Determine log directory
    log_dir = args.log_dir
    if not log_dir:
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # ── WS-only mode ──────────────────────────────────────────────
    if args.ws_only:
        _run_ws_only(args.port, log_dir)
        return

    # ── Full Supervisor mode ──────────────────────────────────────
    from omega.bridge.bus.event_bus import EventBus
    from omega.bridge.supervisor.core import Supervisor

    bus = EventBus(log_dir=log_dir)
    bus.register_agent("Supervisor")

    supervisor = Supervisor(
        event_bus=bus,
        llm_decompose=not args.no_llm,
        log_dir=log_dir,
    )

    # Start WebSocket server for Hermes to connect
    ws_thread = bus.start_websocket_thread(port=args.port)
    print(f"🔌 WebSocket bridge running on ws://127.0.0.1:{args.port}")
    time.sleep(0.5)

    # ── Start Omega in-process (--all mode) ───────────────────────
    if args.all:
        print(f"🔧 Starting Omega agent in-process...")
        try:
            from omega.bridge.omega_launcher import spawn_omega_agent_thread
            spawn_omega_agent_thread(bus)
            print(f"✅ Omega agent connected to the bus")
        except Exception as e:
            print(f"⚠️  Omega agent failed to start: {e}")
            print(f"   Hermes can still connect via WebSocket.")

    print(f"   Hermes connects to ws://127.0.0.1:{args.port}")
    print(f"   Omega is {'online (in-process)' if args.all else 'waiting (connect separately)'}")
    print()

    if args.headless:
        _run_headless(supervisor, bus, args.prompt, port=args.port)
    else:
        _run_tui(supervisor, bus, args.prompt)


def _run_ws_only(port: int, log_dir: str) -> None:
    """Run WebSocket server only — for agents to connect to."""
    from omega.bridge.bus.event_bus import EventBus

    bus = EventBus(log_dir=log_dir)
    bus.register_agent("Supervisor")

    print(f"🔌 WebSocket bridge running on ws://127.0.0.1:{port}")
    print(f"   Hermes and Omega connect here.")
    print(f"   Press Ctrl+C to stop.")

    import asyncio
    try:
        asyncio.run(bus.run_websocket_server(port=port))
    except KeyboardInterrupt:
        print("\nShutting down...")


def _run_headless(supervisor, bus, prompt_parts: list[str], port: int = 9876) -> None:
    """Run supervisor without TUI — process and keep alive for WS clients."""
    prompt = " ".join(prompt_parts) if prompt_parts else ""
    if prompt.strip():
        print(f"🎯 Prompt: {prompt}\n")
        supervisor.handle_user_prompt(prompt)
        print(f"📡 Bridge active on ws://127.0.0.1:{port}")
        print(f"   Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def _run_tui(supervisor, bus, prompt_parts: list[str]) -> None:
    """Run supervisor with TUI."""
    from omega.bridge.tui import SupervisorTUI

    tui = SupervisorTUI(supervisor, bus)
    prompt = " ".join(prompt_parts) if prompt_parts else ""

    if prompt.strip():
        print(f"\n🎯 Prompt: {prompt}\n")
        supervisor.handle_user_prompt(prompt)
        tui.run()
    else:
        try:
            while True:
                try:
                    prompt = input(f"\n{BOLD}🎯 supervisor> {RESET}")
                except (EOFError, KeyboardInterrupt):
                    print()
                    break

                prompt = prompt.strip()
                if not prompt:
                    continue
                if prompt.lower() in ("exit", "quit", "/exit"):
                    break
                if prompt.lower() == "/status":
                    stats = supervisor.get_stats()
                    print(f"  Tasks: {stats['done_tasks']}/{stats['total_tasks']}")
                    print(f"  Agents: {', '.join(bus.get_connected_agents())}")
                    print(f"  Messages: {stats['message_count']}")
                    continue

                supervisor.handle_user_prompt(prompt)
                tui.run()

        except KeyboardInterrupt:
            print("\nShutting down...")

    print(f"{DIM}Supervisor session ended.{RESET}")


# ── ANSI constants ──────────────────────────────────────────────
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
COLORS = {
    "Supervisor": "\033[38;5;220m",
    "Omega": "\033[38;5;75m",
    "Hermes": "\033[38;5;82m",
}


if __name__ == "__main__":
    main()
