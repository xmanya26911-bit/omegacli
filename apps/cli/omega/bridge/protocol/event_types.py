"""
Event types for the supervisor system.

Each event maps to a specific lifecycle stage in task processing.
Agents subscribe to event types they care about.
The supervisor emits lifecycle events to control flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class EventType:
    """Canonical event type constants."""

    # ── Task Lifecycle ────────────────────────────────────────────
    TASK_CREATED = "task.created"            # Supervisor decomposed user prompt → task
    PLAN_READY = "plan.ready"                # Omega finished architecture plan
    TASK_ASSIGNED = "task.assigned"          # Supervisor assigned task to an agent
    TASK_IN_PROGRESS = "task.in_progress"    # Agent started working on task

    # ── Agent Communication ───────────────────────────────────────
    AGENT_QUESTION = "agent.question"        # Agent asks another agent something
    AGENT_FEEDBACK = "agent.feedback"        # Agent responds to a question
    AGENT_PROPOSAL = "agent.proposal"        # Agent proposes a decision/approach
    AGENT_BLOCKED = "agent.blocked"          # Agent stuck, needs help/unblock

    # ── Work Results ──────────────────────────────────────────────
    CODE_FINISHED = "code.finished"          # Agent completed implementation
    REVIEW_NEEDED = "review.needed"          # Agent requests code review
    REVIEW_PASSED = "review.passed"          # Review accepted
    REVIEW_FAILED = "review.failed"          # Review rejected, needs rework

    # ── Human in the Loop ─────────────────────────────────────────
    APPROVAL_NEEDED = "approval.needed"      # Destructive action needs human OK
    HUMAN_APPROVAL = "human.approval"        # User approved
    HUMAN_DENIED = "human.denied"            # User denied

    # ── Completion ────────────────────────────────────────────────
    TASK_DONE = "task.done"                  # Task completed successfully
    TASK_FAILED = "task.failed"              # Task failed
    SESSION_END = "session.end"              # All tasks done, session over

    # ── System Events ─────────────────────────────────────────────
    AGENT_CONNECTED = "agent.connected"      # Agent joined the bus
    AGENT_DISCONNECTED = "agent.disconnected"  # Agent left the bus
    AGENT_STATUS = "agent.status"            # Status update (thinking, working, idle)
    SYSTEM_LOG = "system.log"                # General log/info message
    USER_MESSAGE = "user.message"            # Raw user input

    @classmethod
    def all_types(cls) -> list[str]:
        """Return all event type strings."""
        return [
            v for k, v in cls.__dict__.items()
            if isinstance(v, str) and not k.startswith("_")
        ]

    @classmethod
    def agent_emittable(cls) -> list[str]:
        """Event types agents are allowed to emit (not supervisor-only)."""
        return [
            cls.PLAN_READY,
            cls.AGENT_QUESTION,
            cls.AGENT_FEEDBACK,
            cls.AGENT_PROPOSAL,
            cls.AGENT_BLOCKED,
            cls.CODE_FINISHED,
            cls.REVIEW_NEEDED,
            cls.AGENT_STATUS,
        ]


# ── Helper to create structured event payloads ───────────────────

def make_task_created(task_id: str, description: str, role: str = "",
                      dependencies: list[str] | None = None,
                      metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create payload for a TASK_CREATED event."""
    return {
        "task_id": task_id,
        "description": description,
        "role": role,
        "dependencies": dependencies or [],
        "metadata": metadata or {},
    }


def make_plan_ready(task_id: str, plan: str, suggestions: list[str] | None = None) -> dict[str, Any]:
    """Create payload for a PLAN_READY event."""
    return {
        "task_id": task_id,
        "plan": plan,
        "suggestions": suggestions or [],
    }


def make_approval_needed(task_id: str, action_description: str,
                         details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create payload for an APPROVAL_NEEDED event."""
    return {
        "task_id": task_id,
        "action": action_description,
        "details": details or {},
    }
