"""
Hermes Bridge Client — connects Hermes to the Supervisor EventBus.

This script runs in a background terminal task. It:
    1. Connects to the Supervisor's WebSocket at ws://127.0.0.1:9876
    2. Registers as "Hermes"
    3. Listens for tasks and messages
    4. Prints received events to stdout (so I can see them)
    5. Can accept input from stdin to emit messages back

Usage:
    python hermes_client.py                          # Connect to default localhost:9876
    python hermes_client.py --port 9876               # Custom port
    python hermes_client.py --verbose                 # Full debug output

The Supervisor WebSocket must be running first:
    omega.bat --team                                 # From Omega's directory
    # or
    python -m omega.bridge --ws-only                 # WS server only
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime


# ── Styling ──────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[38;5;82m"
YELLOW = "\033[38;5;220m"
BLUE = "\033[38;5;75m"
GRAY = "\033[38;5;245m"
RED = "\033[38;5;196m"
CYAN = "\033[38;5;51m"

EVENT_ICONS = {
    "task.created": "📋",
    "task.assigned": "🎯",
    "plan.ready": "📐",
    "code.finished": "✅",
    "agent.question": "❓",
    "agent.feedback": "💬",
    "agent.proposal": "💡",
    "agent.blocked": "🚫",
    "approval.needed": "⚠️",
    "session.end": "🏁",
    "user.message": "👤",
    "agent.connected": "🔗",
    "agent.disconnected": "🔌",
    "system.log": "ℹ️",
}

_running = True


def _handle_signal(sig, frame):
    global _running
    _running = False
    print(f"\n{DIM}Hermes client shutting down...{RESET}")


def format_event(event_type: str, data: dict) -> str:
    """Format an event for display."""
    icon = EVENT_ICONS.get(event_type, "•")
    msg = data.get("message", data)
    from_agent = msg.get("from_agent", msg.get("from", "?"))
    content = msg.get("content", "")
    content = content.replace("\n", " | ")[:150]
    ts = datetime.now().strftime("%H:%M:%S")

    color = {
        "Hermes": GREEN,
        "Omega": BLUE,
        "Supervisor": YELLOW,
        "User": GRAY,
    }.get(from_agent, GRAY)

    return (
        f"{DIM}{ts}{RESET} "
        f"{icon} "
        f"{BOLD}{color}{from_agent:10}{RESET} "
        f"{content}"
    )


async def main():
    global _running

    parser = argparse.ArgumentParser(description="Hermes Bridge Client")
    parser.add_argument("--port", type=int, default=9876, help="WebSocket port")
    parser.add_argument("--host", default="127.0.0.1", help="WebSocket host")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    url = f"ws://{args.host}:{args.port}"

    print(f"\n{BOLD}{GREEN}╔══════════════════════════════════╗{RESET}")
    print(f"{BOLD}{GREEN}║     HERMES BRIDGE CLIENT        ║{RESET}")
    print(f"{BOLD}{GREEN}╚══════════════════════════════════╝{RESET}")
    print(f"{DIM}  Connecting to {url}{RESET}")
    print(f"{DIM}  Waiting for Supervisor to send tasks...{RESET}")
    print(f"{DIM}  Press Ctrl+C to disconnect{RESET}")
    print()

    try:
        import websockets
    except ImportError:
        print(f"{RED}Error: websockets not installed.{RESET}")
        print(f"{YELLOW}Run: pip install websockets{RESET}")
        sys.exit(1)

    retry_count = 0
    while _running:
        try:
            async with websockets.connect(url) as ws:
                print(f"{GREEN}✅ Connected as Hermes{RESET}\n")

                # Register
                await ws.send(json.dumps({
                    "type": "register",
                    "agent": "Hermes",
                }))
                retry_count = 0

                # Listen for messages
                async def listen():
                    global _running
                    async for raw in ws:
                        if not _running:
                            break
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        event_type = data.get("event", "unknown")
                        display = format_event(event_type, data)
                        print(display)

                        # If verbose, show full payload
                        if args.verbose and event_type in (
                            "task.assigned", "approval.needed"
                        ):
                            print(f"{DIM}  Full: {json.dumps(data, indent=2)[:500]}{RESET}")

                await listen()

        except (ConnectionRefusedError, OSError) as e:
            retry_count += 1
            if retry_count == 1:
                print(f"{YELLOW}⏳ Waiting for Supervisor to start...{RESET}")
            elif retry_count % 10 == 0:
                print(f"{YELLOW}⏳ Still waiting... (attempt {retry_count}){RESET}")
            await asyncio.sleep(2)
        except Exception as e:
            print(f"{RED}❌ Connection error: {e}{RESET}")
            await asyncio.sleep(3)

    print(f"\n{DIM}Hermes client disconnected.{RESET}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{DIM}Bye.{RESET}")
