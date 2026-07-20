"""
AgentMessage — the shared language between agents.

Every piece of communication in the system is an AgentMessage.
Messages are emitted to the EventBus and logged for replay.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class AgentMessage:
    """Universal message format for all agent communication.

    Fields:
        id: Unique message ID (auto-generated if empty).
        task_id: The task this message relates to.
        from_agent: Name of the sender ("Hermes", "Omega", "Supervisor").
        to_agent: Name of the recipient ("Hermes", "Omega", "Supervisor", "*" for broadcast).
        kind: Message kind — proposal, question, feedback, result, request_approval, etc.
        content: The actual text content.
        timestamp: ISO-8601 timestamp (auto-set if empty).
        metadata: Extra structured data (file refs, confidence, error codes, etc.).
    """
    id: str = ""
    task_id: str = ""
    from_agent: str = ""
    to_agent: str = "*"
    kind: str = "message"
    content: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = f"msg_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self, indent: int | None = None) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), indent=indent, default=str)

    @classmethod
    def from_json(cls, raw: str) -> AgentMessage:
        """Deserialize from JSON string."""
        data = json.loads(raw)
        return cls(**data)

    def is_broadcast(self) -> bool:
        """True if this message is addressed to all agents."""
        return self.to_agent == "*"

    def is_for(self, agent_name: str) -> bool:
        """True if this message is addressed to the given agent (or broadcast)."""
        return self.to_agent == "*" or self.to_agent == agent_name

    def short_str(self, max_len: int = 80) -> str:
        """Short one-line representation for TUI display."""
        preview = self.content.replace("\n", " ")[:max_len]
        if len(self.content) > max_len:
            preview += "..."
        return f"[{self.kind}] {self.from_agent} → {self.to_agent}: {preview}"

    def __repr__(self) -> str:
        return (
            f"AgentMessage(id={self.id}, task={self.task_id}, "
            f"{self.from_agent}→{self.to_agent}, kind={self.kind})"
        )
