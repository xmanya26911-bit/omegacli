"""
Supervisor — the boss.

Responsibilities:
    • Receives user prompt
    • Decomposes into structured tasks (LLM-powered)
    • Assigns tasks to agents based on role/capability
    • Routes messages between agents
    • Detects and breaks infinite loops
    • Manages parallel vs sequential flow
    • Handles human-in-the-loop approval gates
    • Logs everything for replay/debug
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from omega.bridge.protocol.message import AgentMessage
from omega.bridge.protocol.event_types import EventType, make_task_created
from omega.bridge.bus.event_bus import EventBus

logger = logging.getLogger("omega.bridge.supervisor")


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A single unit of work for an agent."""
    id: str
    description: str
    role: str  # "architect", "code", "research", "review", "security", etc.
    agent: str = ""  # assigned agent name
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    result: str = ""
    created_at: float = 0.0
    assigned_at: float = 0.0
    completed_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

    @property
    def elapsed(self) -> float:
        if self.completed_at:
            return self.completed_at - self.created_at
        return time.time() - self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "role": self.role,
            "agent": self.agent,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "result": self.result[:200] if self.result else "",
            "elapsed": round(self.elapsed, 1),
        }


# ── Role-to-Agent mapping ────────────────────────────────────────

ROLE_MAP: dict[str, str] = {
    "architect": "Omega",
    "plan": "Omega",
    "reason": "Omega",
    "research": "Hermes",
    "code": "Hermes",
    "implement": "Hermes",
    "debug": "Hermes",
    "shell": "Hermes",
    "web": "Hermes",
    "review": "Omega",
    "security": "Hermes",  # or "Reviewer" when added
    "test": "Hermes",
    "docs": "Hermes",
}

DEFAULT_AGENT = "Omega"


class Supervisor:
    """Orchestrates the multi-agent system."""

    def __init__(self, event_bus: EventBus, llm_decompose: bool = True,
                 max_parallel: int = 3, log_dir: str | None = None):
        self.bus = event_bus
        self.llm_decompose = llm_decompose
        self.max_parallel = max_parallel
        self.tasks: dict[str, Task] = {}
        self.session_id = f"session_{uuid.uuid4().hex[:8]}"
        self._message_count = 0
        self._start_time = time.time()
        self._loop_counters: dict[str, int] = defaultdict(int)
        self._loop_threshold = 15  # max back-and-forth before flagging
        self._on_approval: dict[str, Callable] = {}

        # Subscribe to agent events
        self.bus.subscribe(EventType.PLAN_READY, self._on_plan_ready)
        self.bus.subscribe(EventType.CODE_FINISHED, self._on_code_finished)
        self.bus.subscribe(EventType.AGENT_BLOCKED, self._on_agent_blocked)
        self.bus.subscribe(EventType.AGENT_QUESTION, self._on_agent_question)
        self.bus.subscribe(EventType.AGENT_FEEDBACK, self._on_agent_feedback)
        self.bus.subscribe(EventType.HUMAN_APPROVAL, self._on_human_approval)
        self.bus.subscribe(EventType.HUMAN_DENIED, self._on_human_denied)
        self.bus.subscribe(EventType.AGENT_STATUS, self._on_agent_status)
        self.bus.subscribe(EventType.TASK_DONE, self._on_task_done)

        # Log directory
        self._log_dir = log_dir
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        logger.info(f"Supervisor initialized: session={self.session_id}")

    # ── User Input ────────────────────────────────────────────────

    def handle_user_prompt(self, prompt: str) -> None:
        """Main entry point. Takes user prompt, decomposes, assigns."""
        logger.info(f"User prompt: {prompt[:100]}...")

        # Broadcast user message
        self.bus.emit_raw(
            EventType.USER_MESSAGE,
            from_agent="User",
            content=prompt,
        )

        # Decompose into tasks
        tasks = self._decompose(prompt)

        # Create task events
        for task_data in tasks:
            task = Task(
                id=task_data["id"],
                description=task_data["description"],
                role=task_data.get("role", "code"),
                dependencies=task_data.get("dependencies", []),
                metadata=task_data.get("metadata", {}),
            )
            self.tasks[task.id] = task

            self.bus.emit_raw(
                EventType.TASK_CREATED,
                content=task.description,
                task_id=task.id,
                metadata={"role": task.role, "deps": task.dependencies},
            )

        # Assign tasks respecting dependencies
        self._assign_ready_tasks()

    # ── Task Decomposition ────────────────────────────────────────

    def _decompose(self, prompt: str) -> list[dict[str, Any]]:
        """Break user prompt into structured tasks.

        If llm_decompose is True, uses an LLM call.
        Otherwise, falls back to a simple rule-based split.
        """
        if self.llm_decompose:
            try:
                return self._llm_decompose(prompt)
            except Exception as e:
                logger.warning(f"LLM decomposition failed ({e}), using fallback")

        # Fallback: simple task creation
        return self._fallback_decompose(prompt)

    def _llm_decompose(self, prompt: str) -> list[dict[str, Any]]:
        """Use an LLM to intelligently break down the prompt."""
        # Try to use Omega's provider if available
        try:
            import requests
            from config import Config
            cfg = Config()

            system = (
                "You are a task decomposition engine. Break the user's request into "
                "structured tasks. Each task has: id (t1, t2...), description, role "
                "(architect, research, code, review, test, docs), and dependencies "
                "(list of task ids that must complete first). "
                "Respond ONLY with a JSON array. No explanation.\n\n"
                "Roles:\n"
                "  architect — planning, architecture decisions (→ Omega)\n"
                "  research — web searches, API research (→ Hermes)\n"
                "  code — implementation (→ Hermes)\n"
                "  review — code review, QA (→ Omega)\n"
                "  test — write and run tests (→ Hermes)\n"
                "  docs — documentation (→ Hermes)\n"
                "  security — security audit (→ Hermes)\n\n"
                "Example:\n"
                "Input: Build a weather app with React and FastAPI\n"
                "Output: [\n"
                '  {"id":"t1","description":"Plan architecture for weather app",'
                '"role":"architect","dependencies":[]},\n'
                '  {"id":"t2","description":"Research free weather APIs",'
                '"role":"research","dependencies":["t1"]},\n'
                '  {"id":"t3","description":"Build FastAPI backend with weather endpoint",'
                '"role":"code","dependencies":["t1","t2"]},\n'
                '  {"id":"t4","description":"Build React frontend with weather display",'
                '"role":"code","dependencies":["t3"]}\n'
                "]"
            )

            resp = requests.post(
                f"{cfg.base_url}/chat/completions",
                json={
                    "model": cfg.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
                headers={"Authorization": f"Bearer {cfg.api_key}"},
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]

            # Extract JSON array from response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0]
            tasks = json.loads(content.strip())
            if isinstance(tasks, list):
                return tasks
        except Exception as e:
            logger.debug(f"LLM decompose failed: {e}")

        return self._fallback_decompose(prompt)

    def _fallback_decompose(self, prompt: str) -> list[dict[str, Any]]:
        """Simple fallback: create architect + code tasks."""
        prompt_lower = prompt.lower()
        tasks = []

        # Always start with an architect task
        tasks.append({
            "id": "t1",
            "description": f"Plan architecture for: {prompt[:200]}",
            "role": "architect",
            "dependencies": [],
        })

        # Check for research needs
        research_keywords = ["api", "library", "framework", "search", "find", "what is"]
        if any(kw in prompt_lower for kw in research_keywords):
            tasks.append({
                "id": "t2",
                "description": f"Research requirements and best tools for: {prompt[:200]}",
                "role": "research",
                "dependencies": ["t1"],
            })
            code_deps = ["t1", "t2"]
        else:
            code_deps = ["t1"]

        # Implementation task
        tasks.append({
            "id": "t3",
            "description": f"Implement: {prompt[:200]}",
            "role": "code",
            "dependencies": code_deps,
        })

        # Review task
        tasks.append({
            "id": "t4",
            "description": f"Review and suggest improvements for: {prompt[:200]}",
            "role": "review",
            "dependencies": ["t3"],
        })

        return tasks

    # ── Task Assignment ───────────────────────────────────────────

    def _assign_ready_tasks(self) -> None:
        """Assign all tasks whose dependencies are met."""
        ready = self._get_ready_tasks()

        # Limit parallel
        running = sum(1 for t in self.tasks.values()
                      if t.status in (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS))
        available = self.max_parallel - running
        ready = ready[:max(0, available)]

        for task in ready:
            agent = ROLE_MAP.get(task.role, DEFAULT_AGENT)
            task.agent = agent
            task.status = TaskStatus.ASSIGNED
            task.assigned_at = time.time()

            self.bus.emit_raw(
                EventType.TASK_ASSIGNED,
                from_agent="Supervisor",
                to_agent=agent,
                content=f"{task.description}",
                task_id=task.id,
                metadata={"role": task.role},
            )

            logger.info(f"Assigned {task.id} ({task.role}) → {agent}")

    def _get_ready_tasks(self) -> list[Task]:
        """Return tasks that are pending and have all deps satisfied."""
        done_ids = {t.id for t in self.tasks.values() if t.status == TaskStatus.DONE}
        ready = [
            t for t in self.tasks.values()
            if t.status == TaskStatus.PENDING
            and all(dep in done_ids for dep in t.dependencies)
        ]
        # Sort by dependency depth (tasks with fewer deps first)
        ready.sort(key=lambda t: len(t.dependencies))
        return ready

    def select_agent(self, task: Task) -> str:
        """Determine which agent should handle a task based on its role."""
        return ROLE_MAP.get(task.role, DEFAULT_AGENT)

    # ── Event Handlers ────────────────────────────────────────────

    def _on_plan_ready(self, event_type: str, msg: AgentMessage) -> None:
        """Handle a plan from Omega (or any architect agent)."""
        if msg.task_id and msg.task_id in self.tasks:
            task = self.tasks[msg.task_id]
            task.status = TaskStatus.DONE
            task.result = msg.content
            task.completed_at = time.time()
            self._check_session_done()

    def _on_code_finished(self, event_type: str, msg: AgentMessage) -> None:
        """Handle code completion from an agent."""
        if msg.task_id and msg.task_id in self.tasks:
            task = self.tasks[msg.task_id]
            task.status = TaskStatus.DONE
            task.result = msg.content
            task.completed_at = time.time()
            self._assign_ready_tasks()
            self._check_session_done()

    def _on_task_done(self, event_type: str, msg: AgentMessage) -> None:
        """Handle explicit task done signal."""
        if msg.task_id and msg.task_id in self.tasks:
            task = self.tasks[msg.task_id]
            task.status = TaskStatus.DONE
            task.result = msg.content
            task.completed_at = time.time()
            self._assign_ready_tasks()
            self._check_session_done()

    def _on_agent_blocked(self, event_type: str, msg: AgentMessage) -> None:
        """Handle an agent getting stuck."""
        if msg.task_id and msg.task_id in self.tasks:
            self.tasks[msg.task_id].status = TaskStatus.BLOCKED
        logger.warning(f"Agent {msg.from_agent} blocked: {msg.content[:100]}")

    def _on_agent_question(self, event_type: str, msg: AgentMessage) -> None:
        """Log agent-to-agent questions. The TUI displays these."""
        # Track back-and-forth loops
        key = f"{msg.from_agent}↔{msg.to_agent}"
        self._loop_counters[key] += 1
        if self._loop_counters[key] >= self._loop_threshold:
            logger.warning(f"Potential loop detected: {key} ({self._loop_counters[key]} exchanges)")
            self.bus.emit_raw(
                EventType.SYSTEM_LOG,
                content=f"⚠️ Possible loop detected between {msg.from_agent} and {msg.to_agent} "
                        f"({self._loop_counters[key]} messages)",
            )

    def _on_agent_feedback(self, event_type: str, msg: AgentMessage) -> None:
        """Agent feedback received — just log it."""
        pass

    def _on_agent_status(self, event_type: str, msg: AgentMessage) -> None:
        """Agent status update — used by TUI for indicators."""
        pass

    def _on_human_approval(self, event_type: str, msg: AgentMessage) -> None:
        """User approved an action."""
        key = msg.task_id or msg.metadata.get("approval_key", "")
        if key in self._on_approval:
            self._on_approval[key](True)

    def _on_human_denied(self, event_type: str, msg: AgentMessage) -> None:
        """User denied an action."""
        key = msg.task_id or msg.metadata.get("approval_key", "")
        if key in self._on_approval:
            self._on_approval[key](False)

    # ── Approval Gate ─────────────────────────────────────────────

    def request_approval(self, action: str, task_id: str = "",
                         callback: Callable[[bool], None] | None = None) -> str:
        """Request human approval for a potentially destructive action.

        Returns an approval key. The callback is called with True (approved)
        or False (denied) when the user responds.
        """
        key = f"approval_{uuid.uuid4().hex[:8]}"
        if callback:
            self._on_approval[key] = callback

        self.bus.emit_raw(
            EventType.APPROVAL_NEEDED,
            from_agent="Supervisor",
            kind="request_approval",
            content=action,
            task_id=task_id,
            metadata={"approval_key": key},
        )
        return key

    # ── Session Management ────────────────────────────────────────

    def _check_session_done(self) -> None:
        """Check if all tasks are done and emit session end."""
        all_tasks = list(self.tasks.values())
        if not all_tasks:
            return
        done_count = sum(1 for t in all_tasks if t.status == TaskStatus.DONE)
        total = len(all_tasks)

        if done_count == total:
            elapsed = time.time() - self._start_time
            self.bus.emit_raw(
                EventType.SESSION_END,
                content=f"All {total} tasks completed in {elapsed:.1f}s",
                metadata={
                    "total_tasks": total,
                    "elapsed": round(elapsed, 1),
                    "message_count": self.bus.get_message_count(),
                },
            )
            logger.info(f"Session complete: {total} tasks in {elapsed:.1f}s")

    def get_task_summary(self) -> list[dict[str, Any]]:
        """Return a list of task dicts for TUI display."""
        return [t.to_dict() for t in self.tasks.values()]

    def get_stats(self) -> dict[str, Any]:
        """Return session statistics."""
        all_tasks = list(self.tasks.values())
        return {
            "session_id": self.session_id,
            "elapsed": round(time.time() - self._start_time, 1),
            "total_tasks": len(all_tasks),
            "done_tasks": sum(1 for t in all_tasks if t.status == TaskStatus.DONE),
            "pending_tasks": sum(1 for t in all_tasks if t.status == TaskStatus.PENDING),
            "blocked_tasks": sum(1 for t in all_tasks if t.status == TaskStatus.BLOCKED),
            "message_count": self.bus.get_message_count(),
            "connected_agents": self.bus.get_connected_agents(),
        }
