"""
omega.bridge — Multi-Agent Supervisor System

Connects Hermes + Omega + future agents through a shared event bus
with a live TUI dashboard. All local, no cloud.

Architecture:
    Supervisor TUI ──→ EventBus ──→ Hermes Agent
                         │            Omega Agent
                         │            (future agents)
                    Shared Message Log
"""
from omega.bridge.protocol.message import AgentMessage
from omega.bridge.protocol.event_types import EventType
from omega.bridge.bus.event_bus import EventBus
from omega.bridge.supervisor.core import Supervisor

__version__ = "0.1.0"

__all__ = [
    "AgentMessage",
    "EventType",
    "EventBus",
    "Supervisor",
]
