"""
Omega Launcher — Connects Omega to the Supervisor EventBus as a working agent.

When Omega runs in team mode, this module:
    1. Connects to the EventBus (in-process or via WebSocket)
    2. Registers as "Omega"
    3. Listens for tasks and questions from the bus
    4. Processes tasks using Omega's own LLM/tools pipeline
    5. Emits results, feedback, and proposals back to the bus

This makes Omega a full participant — not just a CLI, but an agent
that can collaborate with Hermes in real-time.

Usage:
    from omega.bridge.omega_launcher import run_omega_agent
    
    # In-process (same process as Supervisor):
    run_omega_agent(bus)
    
    # As subprocess (separate terminal):
    python -m omega.bridge.omega_launcher --connect ws://127.0.0.1:9876
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from typing import Any

from omega.bridge.protocol.message import AgentMessage
from omega.bridge.protocol.event_types import EventType
from omega.bridge.bus.event_bus import EventBus
from omega.bridge.agents import OmegaAgent

logger = logging.getLogger("omega.bridge.omega_launcher")


class OmegaBusAgent(OmegaAgent):
    """Full Omega agent that connects to the bus and processes tasks.

    Extends OmegaAgent with:
        - Automatic task processing (not just signaling)
        - Full Omega LLM + tools pipeline
        - Real-time status updates
        - Ability to ask Hermes questions and receive feedback
    """

    def __init__(self, bus: EventBus, use_full_agent: bool = True):
        super().__init__(bus, use_subprocess=False)
        self.use_full_agent = use_full_agent
        self._omega_llm = None
        self._omega_config = None
        self._task_threads: dict[str, threading.Thread] = {}

    def handle_event(self, event_type: str, message: AgentMessage) -> None:
        """Handle events — Omega actually processes tasks now."""
        if not message.is_for("Omega"):
            return

        logger.info(f"Omega received: {event_type} from {message.from_agent}: {message.content[:80]}")

        if event_type == EventType.TASK_ASSIGNED:
            task_id = message.task_id
            self._current_task = task_id
            self.status(f"Processing: {message.content[:50]}...")

            # Actually process the task in background thread
            self.process_task(message.content, task_id)

        elif event_type == EventType.AGENT_QUESTION:
            # Hermes is asking Omega something — process and respond
            self.status(f"Thinking about {message.from_agent}'s question...")
            self._handle_question(message)

        elif event_type == EventType.AGENT_FEEDBACK:
            # Feedback from another agent — log and consider
            self.status(f"Got feedback from {message.from_agent}")
            logger.info(f"Feedback: {message.content[:200]}")

    def process_task(self, task_description: str, task_id: str | None = None) -> None:
        """Process a task in background thread and emit result on completion."""
        def _execute():
            self._thinking = True
            try:
                result = self._run_omega(task_description)
                self.finished(result, task_id=task_id or self._current_task)
                self.status("Idle")
            except Exception as e:
                self.blocked(f"Task failed: {e}", task_id=task_id or self._current_task)
                self.status("Error")
            finally:
                self._thinking = False

        t = threading.Thread(target=_execute, daemon=True, name=f"omega-task-{task_id or 'unknown'}")
        self._task_threads[task_id or 'unknown'] = t
        t.start()

    def _handle_question(self, message: AgentMessage) -> None:
        """Handle a question from another agent (typically Hermes)."""
        def _answer():
            self._thinking = True
            try:
                result = self._run_omega(
                    f"Answer this question from another agent ({message.from_agent}):\n\n"
                    f"{message.content}\n\n"
                    f"Be concise and specific. This is a technical discussion."
                )
                self.respond(
                    to_agent=message.from_agent,
                    feedback=result,
                    task_id=message.task_id,
                    in_reply_to=message.id,
                )
                self.status("Idle")
            except Exception as e:
                self.blocked(f"Failed to answer: {e}", task_id=message.task_id)
                self.status("Error")
            finally:
                self._thinking = False

        t = threading.Thread(target=_answer, daemon=True, name="omega-answer")
        t.start()

    def _run_omega(self, prompt: str) -> str:
        """Run a prompt through Omega's actual agent pipeline.

        Uses Omega's Config + LLMClient for proper model access,
        system prompts, and tool definitions — not just a raw API call.
        """
        if self.use_full_agent:
            return self._run_full_agent(prompt)
        return super()._run_omega(prompt)

    def _run_full_agent(self, prompt: str) -> str:
        """Use Omega's full agent pipeline (Config + LLM + tools)."""
        try:
            # Add Omega's paths — root first, then subdirectories
            omega_root = r"D:\TERMINALCLI\omega"
            for p in [omega_root,
                      f"{omega_root}/OMEGABACKEND/core",
                      f"{omega_root}/OMEGATUI",
                      f"{omega_root}/OMEGADOCTOR",
                      f"{omega_root}/OMEGAAGENTIC"]:
                if p not in sys.path:
                    sys.path.insert(0, p)

            from config import Config as OmegaConfig
            from llm import LLMClient

            cfg = OmegaConfig()
            logger.info(f"Omega agent using model={cfg.model}")
            llm = LLMClient(cfg)

            # Build a proper system prompt for Omega's role
            system_prompt = (
                "You are Omega, an elite AI agent focused on architecture, planning, "
                "and reasoning. You are collaborating with another agent (Hermes) who "
                "handles coding, research, and implementation.\n\n"
                "Your role:\n"
                "  - Plan system architecture\n"
                "  - Make design decisions\n"
                "  - Review code and suggest improvements\n"
                "  - Reason about trade-offs\n"
                "  - Break down complex problems\n\n"
                "You are on a shared team. Hermes will implement what you design. "
                "Be clear, specific, and technical."
            )

            result = llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                stream=False,  # Non-streaming for bridge integration
            )

            # LLMClient.chat() returns dict when stream=False
            if isinstance(result, dict):
                # Handle various response shapes
                if "choices" in result:
                    choice = result["choices"][0]
                    if isinstance(choice, dict):
                        return choice.get("message", {}).get("content", "")
                    return str(choice)
                return result.get("content", result.get("text", str(result)))
            # Fallback for generators (if stream somehow still on)
            return str(result)

        except Exception as e:
            logger.error(f"Full Omega agent failed: {e}")
            # Fallback to simple LLM call
            return super()._run_omega(f"[Full agent unavailable, using fallback]\n\n{prompt}")


# ── Launcher Functions ──────────────────────────────────────────

def run_omega_agent(bus: EventBus) -> OmegaBusAgent:
    """Create and connect Omega as a bus agent (in-process).

    Call this from the Supervisor process to start Omega as a
    local agent that participates in the team.

    Returns the Omega agent instance.
    """
    agent = OmegaBusAgent(bus, use_full_agent=True)
    agent.connect()

    # Subscribe to relevant events
    bus.subscribe(EventType.TASK_ASSIGNED, agent.handle_event)
    bus.subscribe(EventType.AGENT_QUESTION, agent.handle_event)
    bus.subscribe(EventType.AGENT_FEEDBACK, agent.handle_event)

    logger.info("Omega agent connected and listening on the bus")
    return agent


def spawn_omega_agent_thread(bus: EventBus) -> threading.Thread:
    """Start Omega agent in a background thread. Returns the thread."""
    def _run():
        agent = run_omega_agent(bus)
        # Keep alive
        while True:
            time.sleep(1)

    t = threading.Thread(target=_run, daemon=True, name="omega-agent")
    t.start()
    return t


# ── CLI Entry (for subprocess mode) ─────────────────────────────

def main():
    """CLI entry: connect Omega to a running Supervisor via WebSocket.

    Usage:
        python -m omega.bridge.omega_launcher --connect ws://127.0.0.1:9876
    """
    import argparse

    parser = argparse.ArgumentParser(description="Omega Bridge Agent")
    parser.add_argument("--connect", default="ws://127.0.0.1:9876",
                        help="WebSocket URL of the Supervisor bus")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )

    print(f"\n{'='*50}")
    print(f"  OMEGA BRIDGE AGENT")
    print(f"  Connecting to {args.connect}")
    print(f"{'='*50}\n")

    # Create a local EventBus and connect it to the WebSocket
    bus = EventBus()

    import asyncio
    async def _run():
        try:
            import websockets
        except ImportError:
            print("Error: websockets not installed")
            return

        print("Omega agent starting...")

        async with websockets.connect(args.connect) as ws:
            # Register
            await ws.send(json.dumps({"type": "register", "agent": "Omega"}))
            resp_raw = await asyncio.wait_for(ws.recv(), timeout=5)
            resp = json.loads(resp_raw)
            print(f"  Registered as: {resp.get('agent')}")

            # Connect to local bus
            agent = OmegaBusAgent(bus, use_full_agent=True)
            agent.connect()
            print(f"  ✅ Omega is online. Waiting for tasks...")
            print(f"  Press Ctrl+C to disconnect.\n")

            # Listen for events from the WebSocket and forward to local bus
            async for raw in ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                event_type = data.get("event", "")
                msg_data = data.get("message", {})
                if event_type and msg_data:
                    msg = AgentMessage(**msg_data)
                    if msg.is_for("Omega"):
                        agent.handle_event(event_type, msg)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\nOmega agent disconnected.")


if __name__ == "__main__":
    main()
