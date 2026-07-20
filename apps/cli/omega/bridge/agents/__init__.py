"""Agent base class and adapters.

Each agent in the system subclasses BaseAgent and registers with the EventBus.
Agents NEVER communicate directly — they subscribe to events and emit events.

Currently implemented:
    - BaseAgent: Abstract base with subscribe/emit helpers
    - HermesAgent: Adapter for Hermes (me — connects via WebSocket)
    - OmegaAgent: Adapter for local Omega CLI
"""
from __future__ import annotations

import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from typing import Any

from omega.bridge.protocol.message import AgentMessage
from omega.bridge.protocol.event_types import EventType
from omega.bridge.bus.event_bus import EventBus

logger = logging.getLogger("omega.bridge.agents")


class BaseAgent(ABC):
    """Abstract base for all agents.

    Subclasses must implement:
        - name: Class-level agent identifier
        - handle_event(): Process incoming events

    Usage:
        class MyAgent(BaseAgent):
            name = "MyAgent"
            def handle_event(self, event_type, msg):
                print(f"Got: {msg.content}")
    """

    name: str = "unknown"

    def __init__(self, bus: EventBus):
        self.bus = bus
        self._connected = False
        self._message_count = 0

    @abstractmethod
    def handle_event(self, event_type: str, message: AgentMessage) -> None:
        """Process an incoming event. Subclasses must implement."""
        ...

    def connect(self) -> None:
        """Register with the event bus."""
        self.bus.register_agent(self.name)
        self._connected = True
        logger.info(f"{self.name} agent connected")

    def disconnect(self) -> None:
        """Unregister from the event bus."""
        self.bus.unregister_agent(self.name)
        self._connected = False
        logger.info(f"{self.name} agent disconnected")

    def emit(self, event_type: str, content: str, *,
             to_agent: str = "*", kind: str = "message",
             task_id: str = "", metadata: dict[str, Any] | None = None) -> AgentMessage:
        """Emit an event to the bus. Thread-safe shortcut."""
        self._message_count += 1
        return self.bus.emit_raw(
            event_type=event_type,
            from_agent=self.name,
            to_agent=to_agent,
            kind=kind,
            content=content,
            task_id=task_id,
            metadata=metadata,
        )

    def ask(self, to_agent: str, question: str,
            task_id: str = "") -> AgentMessage:
        """Ask another agent a question."""
        return self.emit(
            EventType.AGENT_QUESTION,
            question,
            to_agent=to_agent,
            kind="question",
            task_id=task_id,
        )

    def respond(self, to_agent: str, feedback: str,
                task_id: str = "", in_reply_to: str = "") -> AgentMessage:
        """Respond to another agent's question."""
        return self.emit(
            EventType.AGENT_FEEDBACK,
            feedback,
            to_agent=to_agent,
            kind="feedback",
            task_id=task_id,
            metadata={"in_reply_to": in_reply_to},
        )

    def propose(self, proposal: str, task_id: str = "") -> AgentMessage:
        """Propose an idea/decision to other agents."""
        return self.emit(
            EventType.AGENT_PROPOSAL,
            proposal,
            kind="proposal",
            task_id=task_id,
        )

    def finished(self, result: str, task_id: str = "") -> AgentMessage:
        """Signal that work is complete."""
        return self.emit(
            EventType.CODE_FINISHED,
            result,
            kind="result",
            task_id=task_id,
        )

    def blocked(self, reason: str, task_id: str = "") -> AgentMessage:
        """Signal that you're stuck and need help."""
        return self.emit(
            EventType.AGENT_BLOCKED,
            reason,
            kind="blocked",
            task_id=task_id,
        )

    def status(self, status_text: str) -> AgentMessage:
        """Update status (thinking, working, idle, etc.)."""
        return self.emit(
            EventType.AGENT_STATUS,
            status_text,
            kind="status",
        )


# ── Hermes Agent ────────────────────────────────────────────────

class HermesAgent(BaseAgent):
    """Adapter for Hermes agent.

    Hermes (me) connects via WebSocket to the EventBus.
    This class runs as a background client that:
        - Connects to ws://localhost:9876
        - Registers as "Hermes"
        - Receives events and processes them
        - Emits results back
    """

    name = "Hermes"

    def __init__(self, bus: EventBus, ws_url: str = "ws://127.0.0.1:9876"):
        super().__init__(bus)
        self.ws_url = ws_url
        self._thread: threading.Thread | None = None
        self._running = False
        self._message_handler: Any = None

    def set_message_handler(self, handler: Any) -> None:
        """Set a callback for incoming messages (used by TUI)."""
        self._message_handler = handler

    def handle_event(self, event_type: str, message: AgentMessage) -> None:
        """Handle events meant for Hermes."""
        if message.is_for("Hermes"):
            logger.debug(f"Hermes received: {event_type} → {message.content[:80]}")
            if self._message_handler:
                self._message_handler(event_type, message)

    def connect_websocket(self) -> threading.Thread:
        """Start Hermes WebSocket client in background thread."""
        def _run():
            import asyncio
            asyncio.run(self._ws_client())

        self._running = True
        self._thread = threading.Thread(target=_run, daemon=True, name="hermes-ws")
        self._thread.start()
        return self._thread

    async def _ws_client(self) -> None:
        """WebSocket client loop — connects, registers, relays messages."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets not installed. pip install websockets")
            return

        while self._running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    # Register
                    await ws.send(json.dumps({"type": "register", "agent": "Hermes"}))
                    self.connect()

                    # Listen loop
                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        event_type = data.get("event", EventType.AGENT_FEEDBACK)
                        msg_data = data.get("message", {})
                        msg = AgentMessage(**msg_data)
                        self.handle_event(event_type, msg)

            except Exception as e:
                logger.warning(f"Hermes WS disconnected ({e}), reconnecting in 3s...")
                self._connected = False
                await asyncio.sleep(3)

    def stop(self) -> None:
        """Stop the WebSocket client."""
        self._running = False
        self.disconnect()


# ── Omega Agent ─────────────────────────────────────────────────

class OmegaAgent(BaseAgent):
    """Adapter for the local Omega CLI agent.

    Omega runs locally at D:\\TERMINALCLI\\omega\\.
    This adapter wraps Omega's own agent/LLM capabilities and
    connects them to the event bus so Omega participates as a peer.

    For direct Omega CLI invocation, this can shell out to Omega's
    own process. For in-process use, it imports Omega's agent module.
    """

    name = "Omega"

    def __init__(self, bus: EventBus, use_subprocess: bool = False):
        super().__init__(bus)
        self.use_subprocess = use_subprocess
        self._current_task: str = ""
        self._thinking = False
        self._omega_agent = None  # lazy import

    def handle_event(self, event_type: str, message: AgentMessage) -> None:
        """Handle events meant for Omega."""
        if not message.is_for("Omega"):
            return

        logger.debug(f"Omega received: {event_type} → {message.content[:80]}")

        if event_type == EventType.TASK_ASSIGNED:
            self._current_task = message.task_id
            self.status(f"Working on: {message.content[:60]}...")
            # Omega would process this in its own loop
            # For now, we signal via the handler
            if self._message_handler:
                self._message_handler(event_type, message)

        elif event_type == EventType.AGENT_QUESTION:
            if self._message_handler:
                self._message_handler(event_type, message)

    def set_message_handler(self, handler: Any) -> None:
        """Set a callback for incoming messages (used by TUI)."""
        self._message_handler = handler

    def process_task(self, task_description: str, task_id: str) -> None:
        """Process a task using Omega's agent. Runs in a thread."""
        def _run():
            self._thinking = True
            self.status(f"Thinking: {task_description[:50]}...")
            try:
                # Try in-process Omega agent
                result = self._run_omega(task_description)
                self.finished(result, task_id=task_id)
                self.status("Idle")
            except Exception as e:
                self.blocked(f"Error: {e}", task_id=task_id)
                self.status("Error")
            finally:
                self._thinking = False

        t = threading.Thread(target=_run, daemon=True, name="omega-worker")
        t.start()

    def _run_omega(self, prompt: str) -> str:
        """Execute a prompt via Omega's agent (in-process) or subprocess."""
        if self.use_subprocess:
            return self._run_subprocess(prompt)

        # In-process: try to use Omega's agent directly
        try:
            import sys
            # Add Omega's paths
            omega_root = r"D:\TERMINALCLI\omega"
            for p in [f"{omega_root}/OMEGABACKEND/core",
                      f"{omega_root}/OMEGATUI",
                      f"{omega_root}/OMEGADOCTOR",
                      f"{omega_root}/OMEGAAGENTIC"]:
                if p not in sys.path:
                    sys.path.insert(0, p)

            from config import Config
            cfg = Config()

            # Simple LLM call through Omega's provider
            import requests
            resp = requests.post(
                f"{cfg.base_url}/chat/completions",
                json={
                    "model": cfg.model,
                    "messages": [
                        {"role": "system", "content": "You are Omega, an elite AI agent."},
                        {"role": "user", "content": prompt},
                    ],
                },
                headers={"Authorization": f"Bearer {cfg.api_key}"},
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Omega agent error: {e}"

    def _run_subprocess(self, prompt: str) -> str:
        """Run Omega CLI as subprocess."""
        import subprocess
        try:
            result = subprocess.run(
                ["python", r"D:\TERMINALCLI\omega\main.py"] + prompt.split(),
                capture_output=True, text=True, timeout=120,
                cwd=r"D:\TERMINALCLI\omega",
            )
            return result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            return "Omega subprocess timed out"
        except Exception as e:
            return f"Omega subprocess error: {e}"
