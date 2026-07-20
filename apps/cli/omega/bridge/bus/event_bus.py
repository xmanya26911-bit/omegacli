"""
EventBus — local pub/sub event bus with WebSocket broadcast.

Agents never talk directly. They subscribe to event types and emit events.
The bus routes events to all subscribers, logs everything, and broadcasts
to all connected WebSocket clients.

Architecture:
    Subscriber ──register()──→ EventBus ──emit()──→ All matching subscribers
                                  │
                              ┌──┴──┐
                              │ log │  WebSocket broadcast (all clients)
                              └─────┘
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from omega.bridge.protocol.message import AgentMessage
from omega.bridge.protocol.event_types import EventType

logger = logging.getLogger("omega.bridge.bus")

EventHandler = Callable[[str, AgentMessage], None]


class EventBus:
    """Thread-safe pub/sub event bus with logging and WebSocket broadcast.

    Usage:
        bus = EventBus(log_dir="omega/bridge/logs")
        bus.subscribe("task.created", my_handler)
        bus.emit("task.created", msg)
    """

    def __init__(self, log_dir: str | None = None, history_size: int = 200):
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._agent_subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._connected_agents: dict[str, float] = {}
        self._message_count = 0
        self._log_dir = log_dir
        self._event_history: list[tuple[str, AgentMessage]] = []
        self._history_size = history_size
        self._ws_clients: set[Any] = set()
        self._ws_loop: asyncio.AbstractEventLoop | None = None  # <-- fixed typo

        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    # ── Subscription ──────────────────────────────────────────────

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        with self._lock:
            self._subscribers[event_type].append(handler)

    def subscribe_to_agent(self, agent_name: str, handler: EventHandler) -> None:
        """Subscribe to all messages FROM a specific agent."""
        with self._lock:
            self._agent_subscribers[agent_name].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler subscription."""
        with self._lock:
            if handler in self._subscribers.get(event_type, []):
                self._subscribers[event_type].remove(handler)

    # ── Emitting ──────────────────────────────────────────────────

    def emit(self, event_type: str, message: AgentMessage) -> None:
        """Emit an event to all matching subscribers and WS clients."""
        with self._lock:
            self._message_count += 1
            handlers = list(self._subscribers.get(event_type, []))
            all_handlers = list(self._subscribers.get("*", []))
            agent_handlers = list(self._agent_subscribers.get(message.from_agent, []))

        # Log
        self._log_event(event_type, message)

        # Call local handlers
        for handler in handlers + all_handlers + agent_handlers:
            try:
                handler(event_type, message)
            except Exception:
                logger.exception(f"Handler failed for {event_type} from {message.from_agent}")

        # Broadcast to WebSocket clients
        self._broadcast_to_ws(event_type, message)

        # Store in event history for late-joining clients
        with self._lock:
            self._event_history.append((event_type, message))
            if len(self._event_history) > self._history_size:
                self._event_history = self._event_history[-self._history_size:]

    def emit_raw(self, event_type: str, from_agent: str = "Supervisor",
                 to_agent: str = "*", kind: str = "message",
                 content: str = "", task_id: str = "",
                 metadata: dict[str, Any] | None = None) -> AgentMessage:
        """Convenience: create and emit a message in one call."""
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            kind=kind,
            content=content,
            task_id=task_id,
            metadata=metadata or {},
        )
        self.emit(event_type, msg)
        return msg

    # ── Agent Registration ────────────────────────────────────────

    def register_agent(self, agent_name: str) -> None:
        """Register an agent as connected to the bus."""
        with self._lock:
            self._connected_agents[agent_name] = time.time()
        self.emit_raw(
            EventType.AGENT_CONNECTED,
            from_agent="Supervisor",
            content=f"{agent_name} connected to the bus",
            metadata={"agent": agent_name},
        )
        logger.info(f"Agent registered: {agent_name}")

    def unregister_agent(self, agent_name: str) -> None:
        """Remove an agent from the bus."""
        with self._lock:
            self._connected_agents.pop(agent_name, None)
        self.emit_raw(
            EventType.AGENT_DISCONNECTED,
            from_agent="Supervisor",
            content=f"{agent_name} disconnected",
            metadata={"agent": agent_name},
        )

    def get_connected_agents(self) -> list[str]:
        with self._lock:
            return list(self._connected_agents.keys())

    def get_message_count(self) -> int:
        with self._lock:
            return self._message_count

    # ── Logging ───────────────────────────────────────────────────

    def _log_event(self, event_type: str, message: AgentMessage) -> None:
        if not self._log_dir:
            return
        try:
            log_entry = json.dumps({
                "event": event_type,
                "message": {
                    "id": message.id,
                    "task_id": message.task_id,
                    "from": message.from_agent,
                    "to": message.to_agent,
                    "kind": message.kind,
                    "content_preview": message.content[:200],
                    "timestamp": message.timestamp,
                },
            })
            log_file = Path(self._log_dir) / f"bus_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception:
            pass

    # ── WebSocket Broadcasting ────────────────────────────────────

    def _broadcast_to_ws(self, event_type: str, message: AgentMessage) -> None:
        """Send an event to all connected WebSocket clients (fire-and-forget)."""
        if not self._ws_clients:
            return
        payload = json.dumps({
            "event": event_type,
            "message": {
                "id": message.id,
                "task_id": message.task_id,
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "kind": message.kind,
                "content": message.content,
                "timestamp": message.timestamp,
                "metadata": message.metadata,
            },
        }, default=str)
        for ws in list(self._ws_clients):
            try:
                loop = self._ws_loop
                if loop is None or not loop.is_running():
                    continue
                asyncio.run_coroutine_threadsafe(
                    ws.send(payload),
                    loop,
                )
            except Exception:
                pass

    # ── WebSocket Server ──────────────────────────────────────────

    async def run_websocket_server(self, host: str = "127.0.0.1", port: int = 9876) -> None:
        """Run an async WebSocket server.

        Agents connect and register with:
            {"type": "register", "agent": "Hermes"}

        Agents emit events with:
            {"type": "emit", "event": "code.finished", "message": {...}}

        All events on the bus are broadcast to every connected client.
        """
        try:
            import websockets
        except ImportError:
            logger.warning("websockets not installed. Run: pip install websockets")
            return

        # Store event loop for thread-safe broadcasting
        self._ws_loop = asyncio.get_running_loop()
        logger.info(f"WebSocket server starting on ws://{host}:{port}")

        async def _handle(websocket):
            agent_name = "unknown"
            self._ws_clients.add(websocket)
            try:
                async for raw in websocket:
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    if data.get("type") == "register":
                        agent_name = data["agent"]
                        self.register_agent(agent_name)
                        await websocket.send(json.dumps({
                            "type": "registered", "agent": agent_name,
                        }))
                        # Replay event history for late-joining clients
                        history_copy = list(self._event_history)
                        if history_copy:
                            await websocket.send(json.dumps({
                                "type": "history",
                                "count": len(history_copy),
                            }))
                            for hist_type, hist_msg in history_copy:
                                await websocket.send(json.dumps({
                                    "event": hist_type,
                                    "message": {
                                        "id": hist_msg.id,
                                        "task_id": hist_msg.task_id,
                                        "from_agent": hist_msg.from_agent,
                                        "to_agent": hist_msg.to_agent,
                                        "kind": hist_msg.kind,
                                        "content": hist_msg.content,
                                        "timestamp": hist_msg.timestamp,
                                        "metadata": hist_msg.metadata,
                                    },
                                }, default=str))
                    elif data.get("type") == "emit":
                        event_type = data.get("event", "agent.message")
                        msg_data = data.get("message", {})
                        msg = AgentMessage(**msg_data)
                        self.emit(event_type, msg)
            except Exception:
                pass
            finally:
                self._ws_clients.discard(websocket)
                self.unregister_agent(agent_name)

        logger.info(f"WebSocket server starting on ws://{host}:{port}")
        async with websockets.serve(_handle, host, port):
            await asyncio.Future()  # run forever

    def start_websocket_thread(self, host: str = "127.0.0.1", port: int = 9876,
                               daemon: bool = True) -> threading.Thread:
        """Start the WebSocket server in a background thread."""
        def _run():
            asyncio.run(self.run_websocket_server(host=host, port=port))

        t = threading.Thread(target=_run, daemon=daemon, name="ws-bridge")
        t.start()
        return t
