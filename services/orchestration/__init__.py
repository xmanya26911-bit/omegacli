"""
Ω OMEGA Orchestration Service — Task queue, workflow engine, multi-agent coordination (§384).

Manages asynchronous task execution, DAG-based workflows,
and agent orchestration graphs.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional


# ── Types ──────────────────────────────────────────────────────────────────

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """A unit of work in the orchestration system."""
    id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    payload: dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    depends_on: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return None


# ── Task Queue ─────────────────────────────────────────────────────────────

class TaskQueue:
    """Priority-based async task queue."""

    def __init__(self):
        self._queues: dict[TaskPriority, deque[Task]] = {
            p: deque() for p in TaskPriority
        }
        self._tasks: dict[str, Task] = {}

    def enqueue(self, task: Task) -> str:
        """Add a task to the queue. Returns task ID."""
        task.created_at = time.time()
        self._tasks[task.id] = task
        self._queues[task.priority].append(task)
        return task.id

    def dequeue(self) -> Optional[Task]:
        """Pop the highest-priority ready task."""
        for priority in sorted(TaskPriority, key=lambda p: p.value, reverse=True):
            for task in list(self._queues[priority]):
                # Check dependencies met
                if all(
                    dep in self._tasks and self._tasks[dep].status == TaskStatus.COMPLETED
                    for dep in task.depends_on
                ):
                    self._queues[priority].remove(task)
                    task.status = TaskStatus.RUNNING
                    task.started_at = time.time()
                    return task
        return None

    def complete(self, task_id: str, result: Any = None) -> None:
        """Mark task as completed."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()

    def fail(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = time.time()

    def cancel(self, task_id: str) -> None:
        """Cancel a pending task."""
        task = self._tasks.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            # Remove from queue if present
            for q in self._queues.values():
                if task in q:
                    q.remove(task)

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def pending_count(self) -> int:
        return sum(len(q) for q in self._queues.values())

    @property
    def tasks(self) -> dict[str, Task]:
        return dict(self._tasks)


# ── Worker ─────────────────────────────────────────────────────────────────

class Worker:
    """Processes tasks from the queue using registered handlers."""

    def __init__(self, queue: TaskQueue, concurrency: int = 4):
        self.queue = queue
        self.concurrency = concurrency
        self._handlers: dict[str, Callable] = {}
        self._running = False

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """Register a handler for a task type."""
        self._handlers[task_type] = handler

    async def _process(self, task: Task) -> None:
        """Process a single task."""
        try:
            handler = self._handlers.get(task.name)
            if handler:
                result = await handler(task)
            else:
                result = f"No handler for {task.name}"
            self.queue.complete(task.id, result)
        except Exception as e:
            self.queue.fail(task.id, str(e))

    async def run(self) -> None:
        """Main worker loop."""
        self._running = True
        semaphore = asyncio.Semaphore(self.concurrency)

        async def worker_loop():
            while self._running:
                task = self.queue.dequeue()
                if task:
                    async with semaphore:
                        await self._process(task)
                else:
                    await asyncio.sleep(0.1)

        workers = [asyncio.create_task(worker_loop()) for _ in range(self.concurrency)]
        await asyncio.gather(*workers)

    def stop(self):
        self._running = False


# ── Workflow Engine ────────────────────────────────────────────────────────

class WorkflowNode:
    """A node in a workflow DAG."""

    def __init__(self, name: str, task_type: str,
                 depends_on: Optional[list[str]] = None,
                 payload: Optional[dict] = None):
        self.name = name
        self.task_type = task_type
        self.depends_on = depends_on or []
        self.payload = payload or {}


class Workflow:
    """A DAG-based workflow definition."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.nodes: dict[str, WorkflowNode] = {}

    def add_node(self, node: WorkflowNode) -> str:
        """Add a node. Returns node name."""
        self.nodes[node.name] = node
        return node.name

    def execute(self, queue: TaskQueue) -> list[str]:
        """Enqueue all tasks in the workflow. Returns task IDs."""
        task_ids = []
        for node_name, node in self.nodes.items():
            task = Task(
                id=f"{self.name}-{node_name}-{uuid.uuid4().hex[:8]}",
                name=node.task_type,
                payload=node.payload,
                depends_on=[
                    f"{self.name}-{dep}-{uid}"
                    for dep in node.depends_on
                    for uid in queue.tasks  # Inefficient — simplified for now
                ],
                metadata={
                    "workflow": self.name,
                    "node": node.name,
                },
            )
            queue.enqueue(task)
            task_ids.append(task.id)
        return task_ids


# ── Default Queue ──────────────────────────────────────────────────────────

_default_queue: Optional[TaskQueue] = None


def get_default_queue() -> TaskQueue:
    global _default_queue
    if _default_queue is None:
        _default_queue = TaskQueue()
    return _default_queue


def create_task(name: str, payload: Optional[dict] = None,
                priority: TaskPriority = TaskPriority.NORMAL,
                depends_on: Optional[list[str]] = None) -> Task:
    """Create a task with a generated ID."""
    return Task(
        id=f"task-{uuid.uuid4().hex[:12]}",
        name=name,
        priority=priority,
        payload=payload or {},
        depends_on=depends_on or [],
    )
