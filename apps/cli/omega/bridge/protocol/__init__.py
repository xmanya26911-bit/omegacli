"""Bridge protocol layer — shared message format and event types."""
from omega.bridge.protocol.message import AgentMessage
from omega.bridge.protocol.event_types import (
    EventType,
    make_task_created,
    make_plan_ready,
    make_approval_needed,
)

__all__ = [
    "AgentMessage",
    "EventType",
    "make_task_created",
    "make_plan_ready",
    "make_approval_needed",
]
