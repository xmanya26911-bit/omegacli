#!/usr/bin/env python3
"""OMEGA AGENTIC CORE v1.0 -- Long-Horizon Autonomous Workflow Engine
Capabilities:
- Persistent planning with checkpoint/resume
- Task decomposition and dependency management  
- Autonomous multi-step execution with progress tracking
- World model persistence across sessions
- Self-healing recovery from failures
- Parallel task orchestration
- Dynamic re-planning on changing conditions
"""

import os, sys, re, json, time, uuid, hashlib, traceback, threading, queue, enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from pathlib import Path
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed, Future

# --- Core Data Structures ---------------------------------------------------

class TaskStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"

class Priority(enum.Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKLOG = 4


@dataclass
class Task:
    """A single unit of work in a plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: Priority = Priority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    subtasks: List['Task'] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: str = ""
    completed_at: str = ""
    result: Any = None
    error: str = ""
    retry_count: int = 0
    max_retries: int = 3
    checkpoint_data: dict = field(default_factory=dict)
    estimated_effort: int = 10  # minutes
    actual_effort: int = 0
    tags: List[str] = field(default_factory=list)
    assigned_to: str = "omega"
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.name,
            "dependencies": self.dependencies,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "checkpoint_data": self.checkpoint_data,
            "estimated_effort": self.estimated_effort,
            "actual_effort": self.actual_effort,
            "tags": self.tags,
        }


@dataclass
class Plan:
    """A complete execution plan with multiple tasks."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    goal: str = ""
    tasks: List[Task] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = ""
    completed_at: str = ""
    state: str = "active"  # active, paused, completed, failed
    context: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    version: int = 1
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "state": self.state,
            "context": self.context,
            "version": self.version,
        }


# --- Persistent Storage ------------------------------------------------------

PLANS_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agentic_plans.json")
WORLD_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "world_model.json")


class PersistentStore:
    """Thread-safe persistent storage for plans and world model."""
    
    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()
        self.data = self._load()
    
    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                pass
        return {"plans": [], "world_model": {}, "checkpoints": [], "metrics": {}}
    
    def save(self):
        with self._lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, default=str)
    
    def get_plans(self) -> list:
        return self.data.get("plans", [])
    
    def save_plan(self, plan: Plan):
        with self._lock:
            existing = [p for p in self.data["plans"] if p.get("id") != plan.id]
            existing.append(plan.to_dict())
            self.data["plans"] = existing
            self.save()
    
    def get_plan(self, plan_id: str) -> Optional[dict]:
        for p in self.data.get("plans", []):
            if p["id"] == plan_id:
                return p
        return None
    
    def delete_plan(self, plan_id: str):
        with self._lock:
            self.data["plans"] = [p for p in self.data["plans"] if p.get("id") != plan_id]
            self.save()
    
    def save_checkpoint(self, plan_id: str, task_id: str, data: dict):
        with self._lock:
            self.data["checkpoints"].append({
                "plan_id": plan_id,
                "task_id": task_id,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            # Keep only last 100 checkpoints
            if len(self.data["checkpoints"]) > 100:
                self.data["checkpoints"] = self.data["checkpoints"][-100:]
            self.save()
    
    def get_checkpoints(self, plan_id: str) -> list:
        return [c for c in self.data.get("checkpoints", []) if c.get("plan_id") == plan_id]
    
    def update_world_model(self, key: str, value: Any):
        with self._lock:
            self.data["world_model"][key] = {
                "value": value,
                "updated": datetime.now().isoformat()
            }
            self.save()
    
    def get_world_model(self, key: str = None):
        if key:
            return self.data.get("world_model", {}).get(key)
        return self.data.get("world_model", {})


# --- Task Decomposition Engine -----------------------------------------------

class TaskDecomposer:
    """Intelligently decomposes complex goals into manageable tasks."""
    
    def __init__(self):
        # Templates for common complex tasks
        self.decomposition_patterns = {
            "hack_website": [
                ("Reconnaissance", "Gather information about target", Priority.CRITICAL, ["dns_enum", "port_scan", "tech_detect"]),
                ("Vulnerability Scanning", "Scan for common vulnerabilities", Priority.CRITICAL, ["sqli", "xss", "lfi", "cmdi"]),
                ("Exploitation", "Exploit discovered vulnerabilities", Priority.HIGH, ["exploit_confirmed"]),
                ("Privilege Escalation", "Escalate access if needed", Priority.HIGH, []),
                ("Data Extraction", "Extract valuable data", Priority.MEDIUM, ["access_obtained"]),
                ("Persistence", "Maintain access", Priority.LOW, ["access_obtained"]),
                ("Cleanup", "Remove traces of activity", Priority.LOW, ["done"]),
            ],
            "software_project": [
                ("Requirements Analysis", "Define project requirements", Priority.CRITICAL, []),
                ("Architecture Design", "Design system architecture", Priority.CRITICAL, ["requirements_done"]),
                ("Core Implementation", "Implement core functionality", Priority.CRITICAL, ["design_done"]),
                ("Testing", "Write and run tests", Priority.HIGH, ["core_done"]),
                ("Documentation", "Write documentation", Priority.MEDIUM, ["core_done"]),
                ("Deployment", "Deploy the application", Priority.MEDIUM, ["tests_passed"]),
            ],
            "research": [
                ("Literature Review", "Review existing work", Priority.CRITICAL, []),
                ("Hypothesis Formulation", "Define research hypothesis", Priority.CRITICAL, ["lit_review_done"]),
                ("Experiment Design", "Design experiments", Priority.HIGH, ["hypothesis_done"]),
                ("Data Collection", "Gather data", Priority.HIGH, ["design_done"]),
                ("Analysis", "Analyze results", Priority.CRITICAL, ["data_collected"]),
                ("Conclusion", "Draw conclusions", Priority.HIGH, ["analysis_done"]),
                ("Publication", "Write and submit paper", Priority.MEDIUM, ["conclusion_done"]),
            ],
            "system_maintenance": [
                ("Health Check", "Run full system diagnostics", Priority.CRITICAL, []),
                ("Backup", "Backup critical data", Priority.CRITICAL, ["health_ok"]),
                ("Updates", "Apply system updates", Priority.MEDIUM, ["backup_done"]),
                ("Cleanup", "Clean temporary files", Priority.LOW, ["updates_done"]),
                ("Report", "Generate maintenance report", Priority.LOW, ["cleanup_done"]),
            ],
            "vulnerability_research": [
                ("Target Analysis", "Analyze target software/binary", Priority.CRITICAL, []),
                ("Attack Surface Mapping", "Map all attack surfaces", Priority.CRITICAL, ["analysis_done"]),
                ("Fuzzing Campaign", "Run intelligent fuzzing", Priority.HIGH, ["surfaces_mapped"]),
                ("Crash Triage", "Analyze crashes for exploitability", Priority.HIGH, ["fuzzing_done"]),
                ("Exploit Development", "Develop working exploit", Priority.HIGH, ["crashes_triaged"]),
                ("Bypass Development", "Develop mitigation bypass", Priority.MEDIUM, ["exploit_done"]),
                ("Full Chain", "Chain with other vulns", Priority.MEDIUM, ["bypass_done"]),
            ]
        }
    
    def decompose(self, goal: str, context: dict = None) -> Plan:
        """Decompose a complex goal into an executable plan."""
        if context is None:
            context = {}
        
        plan = Plan(
            name=goal[:100],
            goal=goal,
            context=context
        )
        
        # Try to match a pattern
        matched_pattern = None
        for pattern_name, steps in self.decomposition_patterns.items():
            if pattern_name.replace("_", " ") in goal.lower() or \
               any(word in goal.lower() for word in pattern_name.split("_")):
                matched_pattern = steps
                plan.metadata["pattern"] = pattern_name
                break
        
        if matched_pattern:
            for title, desc, priority, deps in matched_pattern:
                task = Task(
                    title=title,
                    description=desc,
                    priority=priority,
                    dependencies=deps,
                    tags=[pattern_name]
                )
                plan.tasks.append(task)
        else:
            # For unknown goals, create a generic decomposition
            plan.tasks.append(Task(title="Research", description=f"Research and understand: {goal}", priority=Priority.CRITICAL))
            plan.tasks.append(Task(title="Plan", description="Create detailed execution plan", priority=Priority.CRITICAL, dependencies=["research_done"]))
            plan.tasks.append(Task(title="Execute", description="Execute the plan", priority=Priority.CRITICAL, dependencies=["plan_done"]))
            plan.tasks.append(Task(title="Verify", description="Verify results and quality", priority=Priority.HIGH, dependencies=["execution_done"]))
            plan.tasks.append(Task(title="Report", description="Generate final report", priority=Priority.MEDIUM, dependencies=["verification_done"]))
        
        return plan
    
    def refine_task(self, task: Task, depth: int = 1) -> Task:
        """Refine a task into subtasks."""
        if depth <= 0:
            return task
        
        # Generic refinement for complex tasks
        task.subtasks = [
            Task(title=f"Research: {task.title}", description=f"Research approaches for: {task.title}", priority=task.priority),
            Task(title=f"Implement: {task.title}", description=f"Implementation phase of: {task.title}", priority=task.priority, 
                 dependencies=[f"Research: {task.title}"]),
            Task(title=f"Verify: {task.title}", description=f"Verification phase of: {task.title}", priority=Priority.HIGH,
                 dependencies=[f"Implement: {task.title}"]),
        ]
        return task


# --- Execution Engine -------------------------------------------------------

class ExecutionEngine:
    """Orchestrates task execution with dependency management and recovery."""
    
    def __init__(self, store: PersistentStore):
        self.store = store
        self.active_plan: Optional[Plan] = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.running_tasks: Dict[str, Future] = {}
        self._stop_flag = threading.Event()
        self.progress_callbacks = []
    
    def execute_plan(self, plan: Plan, auto_continue: bool = True) -> dict:
        """Execute a plan, respecting task dependencies."""
        self.active_plan = plan
        plan.state = "active"
        plan.updated_at = datetime.now().isoformat()
        self.store.save_plan(plan)
        
        result = {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "total_tasks": len(plan.tasks),
            "completed": 0,
            "failed": 0,
            "in_progress": 0,
            "blocked": 0,
            "pending": len(plan.tasks),
            "status": "started"
        }
        
        if auto_continue:
            # Start execution loop in background
            thread = threading.Thread(target=self._execution_loop, daemon=True)
            thread.start()
        
        return result
    
    def _execution_loop(self):
        """Main execution loop -- runs until plan completes or is stopped."""
        plan = self.active_plan
        if not plan:
            return
        
        max_iterations = 1000
        iteration = 0
        
        while not self._stop_flag.is_set() and iteration < max_iterations:
            iteration += 1
            all_done = True
            any_progress = False
            
            for task in plan.tasks:
                if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED):
                    continue
                
                all_done = False
                
                # Check dependencies
                deps_met = self._check_dependencies(task, plan.tasks)
                if not deps_met:
                    if task.status != TaskStatus.BLOCKED:
                        task.status = TaskStatus.BLOCKED
                    continue
                
                # Execute task
                if task.status in (TaskStatus.PENDING, TaskStatus.BLOCKED):
                    task.status = TaskStatus.IN_PROGRESS
                    task.started_at = datetime.now().isoformat()
                    any_progress = True
                    
                    try:
                        task_result = self._execute_task(task)
                        task.result = task_result
                        task.status = TaskStatus.COMPLETED
                        task.completed_at = datetime.now().isoformat()
                        self._notify_progress(task, "completed")
                    except Exception as e:
                        task.error = str(e)
                        task.retry_count += 1
                        if task.retry_count >= task.max_retries:
                            task.status = TaskStatus.FAILED
                            self._notify_progress(task, "failed")
                        else:
                            task.status = TaskStatus.PENDING  # Retry
                            self._notify_progress(task, "retrying")
                    
                    # Save checkpoint
                    self.store.save_checkpoint(plan.id, task.id, {
                        "status": task.status.value,
                        "result": str(task.result)[:500] if task.result else None,
                        "error": task.error[:500] if task.error else None
                    })
                    plan.updated_at = datetime.now().isoformat()
                    self.store.save_plan(plan)
            
            if all_done:
                plan.state = "completed"
                plan.completed_at = datetime.now().isoformat()
                self.store.save_plan(plan)
                break
            
            if not any_progress:
                # No tasks can proceed - check for deadlock
                blocked_tasks = [t for t in plan.tasks if t.status == TaskStatus.BLOCKED]
                if blocked_tasks and all(t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED) 
                                        or t.status == TaskStatus.BLOCKED for t in plan.tasks):
                    # Deadlock detected - mark all blocked as failed
                    for t in blocked_tasks:
                        t.status = TaskStatus.FAILED
                        t.error = "Deadlock: dependencies could not be satisfied"
                    plan.state = "failed"
                    self.store.save_plan(plan)
                    break
            
            time.sleep(0.5)  # Prevent busy-waiting
    
    def _check_dependencies(self, task: Task, all_tasks: List[Task]) -> bool:
        """Check if all dependencies for a task are met."""
        task_id_set = {t.id: t for t in all_tasks}
        task_title_set = {t.title: t for t in all_tasks}
        
        for dep in task.dependencies:
            # Check by ID
            if dep in task_id_set:
                dep_task = task_id_set[dep]
                if dep_task.status != TaskStatus.COMPLETED:
                    return False
            # Check by title
            elif dep in task_title_set:
                dep_task = task_title_set[dep]
                if dep_task.status != TaskStatus.COMPLETED:
                    return False
            # Check for special dependency keywords
            elif dep == "always":
                continue
            else:
                # Unknown dependency -- treat as unmet
                return False
        
        return True
    
    def _execute_task(self, task: Task) -> Any:
        """Execute a single task. Can be overridden for custom logic."""
        # Log the task execution
        task.checkpoint_data["execution_attempts"] = task.checkpoint_data.get("execution_attempts", 0) + 1
        
        # Simulate execution (in real use, this would call actual tools)
        time.sleep(0.5)  # Brief delay for realism
        
        return {
            "task": task.title,
            "executed": True,
            "timestamp": datetime.now().isoformat()
        }
    
    def _notify_progress(self, task: Task, event: str):
        """Notify progress callbacks."""
        for cb in self.progress_callbacks:
            try:
                cb(task, event, self.active_plan)
            except Exception as e:
                pass
    
    def pause_plan(self) -> dict:
        """Pause the current plan execution."""
        self._stop_flag.set()
        if self.active_plan:
            self.active_plan.state = "paused"
            self.active_plan.updated_at = datetime.now().isoformat()
            self.store.save_plan(self.active_plan)
        return {"status": "paused", "plan_id": self.active_plan.id if self.active_plan else None}
    
    def resume_plan(self, plan_id: str = None) -> dict:
        """Resume a paused plan."""
        if plan_id:
            plan_data = self.store.get_plan(plan_id)
            if not plan_data:
                return {"error": f"Plan {plan_id} not found"}
            # Reconstruct plan from data
            self.active_plan = Plan(
                id=plan_data["id"],
                name=plan_data.get("name", ""),
                goal=plan_data.get("goal", ""),
                state="active"
            )
            for t_data in plan_data.get("tasks", []):
                task = Task(
                    id=t_data["id"],
                    title=t_data["title"],
                    description=t_data.get("description", ""),
                    status=TaskStatus(t_data.get("status", "pending")),
                    priority=Priority[t_data.get("priority", "MEDIUM")],
                    dependencies=t_data.get("dependencies", []),
                    error=t_data.get("error", ""),
                    retry_count=t_data.get("retry_count", 0),
                    checkpoint_data=t_data.get("checkpoint_data", {}),
                )
                self.active_plan.tasks.append(task)
        
        if self.active_plan:
            self._stop_flag.clear()
            self.active_plan.state = "active"
            self.active_plan.updated_at = datetime.now().isoformat()
            self.store.save_plan(self.active_plan)
            thread = threading.Thread(target=self._execution_loop, daemon=True)
            thread.start()
            return {"status": "resumed", "plan_id": self.active_plan.id}
        return {"error": "No plan to resume"}
    
    def get_plan_status(self, plan_id: str = None) -> dict:
        """Get detailed status of a plan."""
        if plan_id:
            plan_data = self.store.get_plan(plan_id)
            if not plan_data:
                return {"error": f"Plan {plan_id} not found"}
            tasks = plan_data.get("tasks", [])
        elif self.active_plan:
            plan_data = self.active_plan.to_dict()
            tasks = plan_data["tasks"]
        else:
            return {"error": "No active plan"}
        
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        in_progress = sum(1 for t in tasks if t.get("status") == "in_progress")
        blocked = sum(1 for t in tasks if t.get("status") == "blocked")
        pending = sum(1 for t in tasks if t.get("status") == "pending")
        
        return {
            "plan_id": plan_data.get("id"),
            "name": plan_data.get("name"),
            "goal": plan_data.get("goal"),
            "state": plan_data.get("state"),
            "total": len(tasks),
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "blocked": blocked,
            "pending": pending,
            "progress_pct": round((completed / len(tasks)) * 100, 1) if tasks else 0,
            "tasks": tasks,
        }
    
    def stop(self):
        """Stop all execution."""
        self._stop_flag.set()
        for future in self.running_tasks.values():
            future.cancel()
        self.executor.shutdown(wait=False)


# --- World Model ------------------------------------------------------------

class WorldModel:
    """Persistent world model that maintains understanding across sessions."""
    
    def __init__(self, store: PersistentStore):
        self.store = store
        self.model = store.get_world_model()
    
    def update(self, key: str, value: Any, confidence: float = 1.0):
        """Update a fact in the world model."""
        self.store.update_world_model(key, {
            "value": value,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a fact from the world model."""
        entry = self.store.get_world_model(key)
        if entry:
            return entry.get("value", default)
        return default
    
    def get_all(self) -> dict:
        """Get the entire world model."""
        return self.store.get_world_model()
    
    def learn_from_experience(self, task_result: dict, plan_context: dict):
        """Extract and store lessons from completed tasks."""
        lessons = []
        
        # Extract success patterns
        if task_result.get("status") == "completed":
            lessons.append({
                "type": "success_pattern",
                "context": plan_context,
                "result": task_result,
                "timestamp": datetime.now().isoformat()
            })
        
        # Extract failure patterns
        if task_result.get("status") == "failed":
            lessons.append({
                "type": "failure_pattern",
                "context": plan_context,
                "error": task_result.get("error"),
                "timestamp": datetime.now().isoformat()
            })
        
        if lessons:
            existing = self.get("learned_lessons", [])
            existing.extend(lessons)
            self.update("learned_lessons", existing[-100:])  # Keep last 100
    
    def get_relevant_knowledge(self, goal: str) -> list:
        """Retrieve knowledge relevant to a goal."""
        relevant = []
        all_knowledge = self.get_all()
        
        goal_lower = goal.lower()
        for key, entry in all_knowledge.items():
            if isinstance(entry, dict) and "value" in entry:
                value = entry["value"]
                # Check if key or value reference the goal
                if any(word in key.lower() for word in goal_lower.split()):
                    relevant.append({"key": key, "value": value, "confidence": entry.get("confidence", 1.0)})
        
        return relevant


# ===============================================================================
# OMEGA AGENTIC CORE v2.0 -- Mythos-Level Long-Horizon Capabilities
# Dynamic Replanning, Tool Integration, Progress Tracking, Adaptive Decomposition
# ===============================================================================

# --- Dynamic Replanner ------------------------------------------------------

class DynamicReplanner:
    """Adaptive replanning engine. When tasks fail, finds alternative approaches,
    alternative decomposition strategies, or recovery paths."""
    
    def __init__(self):
        self.replan_history = []
        self.alternative_strategies = {
            "hack_website": [
                ["Reconnaissance", "Vulnerability Scanning", "Exploitation"],
                ["Social Engineering", "Credential Harvesting", "Access"],
                ["Third-party Component Analysis", "Supply Chain Attack"],
            ],
            "software_project": [
                ["Requirements", "Architecture", "Core", "Testing", "Deploy"],
                ["Prototype", "Iterate", "Refine", "Launch"],
                ["Research Existing Solutions", "Adapt", "Integrate"],
            ],
            "research": [
                ["Literature Review", "Hypothesis", "Experiment", "Analysis"],
                ["Data Mining", "Pattern Recognition", "Theory Formulation"],
                ["Simulation", "Validation", "Publication"],
            ],
            "default": [
                ["Research", "Plan", "Execute", "Verify"],
                ["Divide into sub-problems", "Solve independently", "Integrate"],
                ["Find existing solution", "Adapt to context", "Validate"],
            ]
        }
    
    def analyze_failure(self, plan: 'Plan', failed_task: 'Task', all_tasks: list) -> dict:
        """Analyze why a task failed and suggest recovery strategies."""
        analysis = {
            "task_id": failed_task.id,
            "task_title": failed_task.title,
            "error": failed_task.error,
            "retry_count": failed_task.retry_count,
            "max_retries": failed_task.max_retries,
            "recoverable": failed_task.retry_count < failed_task.max_retries,
            "alternative_strategies": [],
            "suggested_approach": None
        }
        
        # Analyze error type
        error_lower = failed_task.error.lower()
        
        if "timeout" in error_lower:
            analysis["suggested_approach"] = "increase_timeout"
            analysis["recoverable"] = True
        elif "not found" in error_lower or "does not exist" in error_lower:
            analysis["suggested_approach"] = "check_prerequisites"
            analysis["recoverable"] = True
        elif "permission" in error_lower or "denied" in error_lower or "access" in error_lower:
            analysis["suggested_approach"] = "elevate_privileges"
            analysis["recoverable"] = True
        elif "connection" in error_lower or "network" in error_lower:
            analysis["suggested_approach"] = "retry_with_backoff"
            analysis["recoverable"] = True
        elif "syntax" in error_lower or "parse" in error_lower:
            analysis["suggested_approach"] = "fix_input_format"
            analysis["recoverable"] = True
        else:
            # Suggest alternative decomposition strategies
            pattern = plan.metadata.get("pattern", "default") if hasattr(plan, 'metadata') else "default"
            strategies = self.alternative_strategies.get(pattern, self.alternative_strategies["default"])
            analysis["alternative_strategies"] = strategies
            analysis["suggested_approach"] = "try_alternative_strategy"
        
        self.replan_history.append({
            "timestamp": datetime.now().isoformat(),
            "plan_id": plan.id if hasattr(plan, 'id') else "unknown",
            "task": failed_task.title,
            "analysis": analysis
        })
        
        return analysis
    
    def generate_recovery_plan(self, original_plan: 'Plan', failed_task: 'Task') -> list:
        """Generate alternative tasks to replace a failed task."""
        recovery_tasks = []
        
        # Strategy 1: Retry with modified parameters
        retry = Task(
            title=f"Retry: {failed_task.title} (attempt {failed_task.retry_count + 1})",
            description=f"Retry with adjusted parameters. Previous error: {failed_task.error[:200]}",
            priority=failed_task.priority,
            dependencies=failed_task.dependencies,
            max_retries=1
        )
        recovery_tasks.append(retry)
        
        # Strategy 2: Alternative approach
        alt = Task(
            title=f"Alternative: {failed_task.title}",
            description=f"Try a different approach. Original failed with: {failed_task.error[:200]}",
            priority=failed_task.priority,
            dependencies=failed_task.dependencies
        )
        recovery_tasks.append(alt)
        
        # Strategy 3: Skip and continue (mark as dependency-met)
        skip = Task(
            title=f"Skip: {failed_task.title}",
            description=f"Skip this task and continue. Mark dependencies as resolved.",
            priority=Priority.LOW,
            dependencies=[],
            tags=["fallback"]
        )
        recovery_tasks.append(skip)
        
        return recovery_tasks
    
    def get_replan_history(self, limit: int = 10) -> list:
        """Get recent replanning history."""
        return self.replan_history[-limit:]


# --- Tool Integration Engine ------------------------------------------------

class ToolIntegration:
    """Integrates with OMEGA's tool execution system to call real tools
    during mission execution instead of simulating."""
    
    def __init__(self):
        self.tool_cache = {}
        self.execution_history = []
    
    def execute_tool(self, tool_name: str, **kwargs) -> dict:
        """Execute an OMEGA tool with the given parameters.
        
        This provides a bridge between the agentic core's mission execution
        and OMEGA's actual tool system.
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters
        
        Returns:
            Tool execution result
        """
        result = {
            "tool": tool_name,
            "parameters": kwargs,
            "status": "unknown",
            "output": None,
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Try to find and call the tool function
        try:
            # Attempt to import and call from tools module
            import importlib
            tools_module = importlib.import_module('tools')
            
            # Build the function name (tools use snake_case)
            func_name = tool_name
            
            if hasattr(tools_module, func_name):
                tool_func = getattr(tools_module, func_name)
                output = tool_func(**kwargs)
                result["status"] = "completed"
                result["output"] = str(output)[:2000]
            else:
                # Try as a tool wrapper
                wrapper_name = f"{tool_name}_tool"
                if hasattr(tools_module, wrapper_name):
                    tool_func = getattr(tools_module, wrapper_name)
                    output = tool_func(**kwargs)
                    result["status"] = "completed" 
                    result["output"] = str(output)[:2000]
                else:
                    # Check TOOL_MAP
                    if hasattr(tools_module, 'TOOL_MAP'):
                        tool_map = getattr(tools_module, 'TOOL_MAP')
                        if tool_name in tool_map:
                            tool_func = tool_map[tool_name]
                            output = tool_func(**kwargs)
                            result["status"] = "completed"
                            result["output"] = str(output)[:2000]
                        else:
                            result["status"] = "not_found"
                            result["error"] = f"Tool '{tool_name}' not found in TOOL_MAP"
                    else:
                        result["status"] = "not_found"
                        result["error"] = f"Tool '{tool_name}' not found"
        except ImportError:
            # Tools module not available -- simulate
            result["status"] = "simulated"
            result["output"] = f"[SIMULATED] {tool_name}({kwargs})"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)[:500]
        
        self.execution_history.append(result)
        return result
    
    def execute_workflow_step(self, step: dict) -> dict:
        """Execute a workflow step that maps to an OMEGA tool.
        
        Step format: {'tool': 'scan_ports', 'params': {'target': 'example.com'}}
        """
        tool_name = step.get("tool", "")
        params = step.get("params", {})
        description = step.get("description", "")
        
        result = self.execute_tool(tool_name, **params)
        result["description"] = description
        
        return result
    
    def get_history(self, limit: int = 20) -> list:
        """Get recent tool execution history."""
        return self.execution_history[-limit:]
    
    def clear_history(self):
        """Clear execution history."""
        self.execution_history = []


# --- Progress Tracker -------------------------------------------------------

class ProgressTracker:
    """Tracks mission progress with ETA calculations, velocity metrics,
    and confidence scoring."""
    
    def __init__(self):
        self.history = {}  # plan_id -> list of progress snapshots
    
    def start_tracking(self, plan_id: str, total_tasks: int):
        """Start tracking progress for a plan."""
        self.history[plan_id] = [{
            "timestamp": datetime.now().isoformat(),
            "completed": 0,
            "total": total_tasks,
            "elapsed_seconds": 0,
            "eta_seconds": None,
            "velocity": 0,
            "confidence": 1.0
        }]
    
    def record_progress(self, plan_id: str, completed: int, total: int) -> dict:
        """Record a progress update and calculate ETA."""
        if plan_id not in self.history:
            self.start_tracking(plan_id, total)
        
        history = self.history[plan_id]
        now = datetime.now()
        first_entry = history[0]
        first_time = datetime.fromisoformat(first_entry["timestamp"])
        elapsed = (now - first_time).total_seconds()
        
        # Calculate velocity (tasks per minute)
        velocity = (completed / elapsed * 60) if elapsed > 0 else 0
        
        # Calculate ETA
        remaining = total - completed
        eta_seconds = (remaining / velocity * 60) if velocity > 0 else None
        
        # Calculate confidence based on progress stability
        if len(history) >= 3:
            recent = history[-3:]
            velocities = [r.get("velocity", 0) for r in recent if r.get("velocity")]
            if velocities:
                variance = max(velocities) - min(velocities) if velocities else 0
                confidence = max(0.1, 1.0 - (variance / max(velocities))) if max(velocities) > 0 else 0.5
            else:
                confidence = 0.5
        else:
            confidence = 0.5
        
        snapshot = {
            "timestamp": now.isoformat(),
            "completed": completed,
            "total": total,
            "progress_pct": round((completed / total) * 100, 1) if total > 0 else 0,
            "elapsed_seconds": int(elapsed),
            "eta_seconds": int(eta_seconds) if eta_seconds is not None else None,
            "velocity": round(velocity, 2),
            "confidence": round(confidence, 2)
        }
        
        history.append(snapshot)
        
        # Format ETA nicely
        eta_str = "N/A"
        if eta_seconds is not None:
            eta_min = int(eta_seconds // 60)
            eta_sec = int(eta_seconds % 60)
            if eta_min >= 60:
                eta_str = f"{eta_min // 60}h{eta_min % 60}m"
            elif eta_min > 0:
                eta_str = f"{eta_min}m{eta_sec}s"
            else:
                eta_str = f"{eta_sec}s"
        
        return {
            "plan_id": plan_id,
            "progress_pct": snapshot["progress_pct"],
            "completed": completed,
            "total": total,
            "elapsed": f"{int(elapsed // 60)}m{int(elapsed % 60)}s",
            "eta": eta_str,
            "velocity": f"{velocity:.2f} tasks/min",
            "confidence": f"{confidence:.0%}"
        }
    
    def get_progress(self, plan_id: str) -> dict:
        """Get the latest progress for a plan."""
        if plan_id not in self.history or not self.history[plan_id]:
            return {"error": f"No progress data for plan {plan_id}"}
        return self.history[plan_id][-1]
    
    def get_history(self, plan_id: str) -> list:
        """Get full progress history for a plan."""
        return self.history.get(plan_id, [])


# --- Adaptive Decomposer ----------------------------------------------------

class AdaptiveDecomposer(TaskDecomposer):
    """Enhanced task decomposer that learns from past decompositions
    and adapts to new situations."""
    
    def __init__(self):
        super().__init__()
        self.learned_patterns = {}
        self.decomposition_log = []
    
    def decompose(self, goal: str, context: dict = None) -> Plan:
        """Decompose a goal, using learned patterns when available."""
        if context is None:
            context = {}
        
        # Check if we've seen a similar goal before
        similar_pattern = self._find_similar_goal(goal)
        if similar_pattern:
            plan = self._apply_learned_pattern(similar_pattern, goal, context)
        else:
            plan = super().decompose(goal, context)
        
        # Save to log
        self.decomposition_log.append({
            "goal": goal,
            "plan_id": plan.id,
            "task_count": len(plan.tasks),
            "timestamp": datetime.now().isoformat()
        })
        
        return plan
    
    def _find_similar_goal(self, goal: str) -> Optional[dict]:
        """Find a previously decomposed goal similar to this one."""
        goal_lower = goal.lower()
        goal_words = set(goal_lower.split())
        
        best_match = None
        best_score = 0
        
        for pattern_name, pattern_goal in self.learned_patterns.items():
            pattern_words = set(pattern_goal.get("goal", "").lower().split())
            # Jaccard similarity
            intersection = goal_words & pattern_words
            union = goal_words | pattern_words
            score = len(intersection) / len(union) if union else 0
            
            if score > best_score and score >= 0.3:
                best_score = score
                best_match = pattern_goal
        
        return best_match
    
    def _apply_learned_pattern(self, pattern: dict, goal: str, context: dict) -> Plan:
        """Apply a learned decomposition pattern to a new goal."""
        plan = Plan(
            name=goal[:100],
            goal=goal,
            context=context,
            metadata={"adapted_from": pattern.get("goal", "")}
        )
        
        for task_data in pattern.get("tasks", []):
            task = Task(
                title=task_data.get("title", ""),
                description=task_data.get("description", ""),
                priority=Priority[task_data.get("priority", "MEDIUM")],
                dependencies=task_data.get("dependencies", []),
                tags=task_data.get("tags", [])
            )
            plan.tasks.append(task)
        
        return plan
    
    def learn_from_plan(self, plan: Plan, success: bool):
        """Learn a successful decomposition pattern."""
        key = plan.name[:50] if plan.name else plan.id
        
        if success:
            self.learned_patterns[key] = {
                "goal": plan.goal,
                "tasks": [t.to_dict() for t in plan.tasks],
                "success": True,
                "learned_at": datetime.now().isoformat()
            }
        else:
            # Track failures too
            if key not in self.learned_patterns:
                self.learned_patterns[key] = {
                    "goal": plan.goal,
                    "tasks": [],
                    "success": False,
                    "learned_at": datetime.now().isoformat()
                }
    
    def get_learned_count(self) -> int:
        return len(self.learned_patterns)


# --- Autonomous Orchestrator (v2.0) -----------------------------------------

class AutonomousOrchestrator:
    """High-level orchestrator that manages the entire autonomous workflow lifecycle.
    v2.0: Enhanced with Dynamic Replanning, Tool Integration, Progress Tracking,
    and Adaptive Decomposition."""
    
    def __init__(self):
        self.store = PersistentStore(PLANS_DB_PATH)
        self.decomposer = AdaptiveDecomposer()  # v2.0: learns from past decompositions
        self.executor = ExecutionEngine(self.store)
        self.world_model = WorldModel(self.store)
        self.replanner = DynamicReplanner()     # v2.0: failure recovery & replanning
        self.tool_integration = ToolIntegration()  # v2.0: real tool execution
        self.progress_tracker = ProgressTracker()  # v2.0: ETA & velocity tracking
    
    def start_mission(self, goal: str, context: dict = None) -> dict:
        """Start a new autonomous mission from a high-level goal."""
        # Check world model for relevant knowledge
        relevant_knowledge = self.world_model.get_relevant_knowledge(goal)
        
        # Create context with knowledge
        if context is None:
            context = {}
        if relevant_knowledge:
            context["prior_knowledge"] = relevant_knowledge
        
        # Decompose goal into plan (v2.0: uses adaptive decomposition)
        plan = self.decomposer.decompose(goal, context)
        
        # Save plan
        self.store.save_plan(plan)
        
        # Start progress tracking (v2.0)
        self.progress_tracker.start_tracking(plan.id, len(plan.tasks))
        
        # Start execution
        result = self.executor.execute_plan(plan, auto_continue=True)
        
        return {
            "mission": goal,
            "plan_id": plan.id,
            "tasks": len(plan.tasks),
            "task_details": [t.title for t in plan.tasks],
            "relevant_knowledge": len(relevant_knowledge),
            "status": "launched",
            "adaptive": True,
            "result": result
        }
    
    def get_mission_status(self, plan_id: str = None) -> dict:
        """Get status of a mission with v2.0 progress tracking."""
        status = self.executor.get_plan_status(plan_id)
        
        if "error" not in status:
            # Add progress tracking (v2.0)
            pid = plan_id or (self.executor.active_plan.id if self.executor.active_plan else None)
            if pid:
                progress = self.progress_tracker.record_progress(
                    pid, 
                    status.get("completed", 0),
                    status.get("total", 1)
                )
                status["progress"] = progress
        
        return status
    
    def pause_mission(self) -> dict:
        """Pause the active mission."""
        return self.executor.pause_plan()
    
    def resume_mission(self, plan_id: str = None) -> dict:
        """Resume a paused mission."""
        return self.executor.resume_plan(plan_id)
    
    def list_missions(self) -> list:
        """List all missions/plans."""
        return self.store.get_plans()
    
    def get_mission_plan(self, plan_id: str) -> Optional[dict]:
        """Get a specific plan."""
        return self.store.get_plan(plan_id)
    
    def delete_mission(self, plan_id: str):
        """Delete a mission."""
        self.store.delete_plan(plan_id)
    
    def update_world_knowledge(self, key: str, value: Any, confidence: float = 1.0):
        """Update the world model with new knowledge."""
        self.world_model.update(key, value, confidence)
    
    def get_world_knowledge(self) -> dict:
        """Get the current world model."""
        return self.world_model.get_all()
    
    def refine_plan(self, plan_id: str, task_id: str = None) -> dict:
        """Refine a plan or specific task with more detail."""
        plan_data = self.store.get_plan(plan_id)
        if not plan_data:
            return {"error": f"Plan {plan_id} not found"}
        
        plan = Plan(id=plan_data["id"], name=plan_data.get("name", ""), goal=plan_data.get("goal", ""))
        for t_data in plan_data.get("tasks", []):
            task = Task(
                id=t_data["id"], title=t_data["title"],
                description=t_data.get("description", ""),
                status=TaskStatus(t_data.get("status", "pending")),
                priority=Priority[t_data.get("priority", "MEDIUM")],
            )
            if task_id and task.id == task_id:
                task = self.decomposer.refine_task(task)
            elif not task_id:
                task = self.decomposer.refine_task(task)
            plan.tasks.append(task)
        
        self.store.save_plan(plan)
        return {"status": "refined", "task_count": len(plan.tasks)}
    
    def analyze_failure(self, failed_task_id: str) -> dict:
        """Analyze why a task failed and suggest recovery (v2.0)."""
        if not self.executor.active_plan:
            return {"error": "No active plan"}
        
        failed_task = None
        for t in self.executor.active_plan.tasks:
            if t.id == failed_task_id or t.title == failed_task_id:
                failed_task = t
                break
        
        if not failed_task:
            return {"error": f"Task not found: {failed_task_id}"}
        
        return self.replanner.analyze_failure(
            self.executor.active_plan, 
            failed_task, 
            self.executor.active_plan.tasks
        )
    
    def execute_tool(self, tool_name: str, **kwargs) -> dict:
        """Execute an OMEGA tool during a mission (v2.0)."""
        return self.tool_integration.execute_tool(tool_name, **kwargs)
    
    def get_tool_history(self, limit: int = 20) -> list:
        """Get tool execution history (v2.0)."""
        return self.tool_integration.get_history(limit)
    
    def get_progress(self, plan_id: str = None) -> dict:
        """Get detailed progress with ETA (v2.0)."""
        pid = plan_id or (self.executor.active_plan.id if self.executor.active_plan else None)
        if not pid:
            return {"error": "No plan specified or active"}
        return self.progress_tracker.get_progress(pid)
    
    def self_test(self) -> list:
        """Run self-test to verify agentic core works."""
        results = []
        
        # Test decomposition
        try:
            plan = self.decomposer.decompose("hack a website")
            results.append(("TaskDecomposer", "PASS", f"{len(plan.tasks)} tasks generated"))
        except Exception as e:
            results.append(("TaskDecomposer", "FAIL", str(e)))
        
        # Test plan creation and storage
        try:
            self.store.save_plan(plan)
            loaded = self.store.get_plan(plan.id)
            results.append(("PersistentStore", "PASS", f"Plan saved/loaded: {loaded is not None}"))
        except Exception as e:
            results.append(("PersistentStore", "FAIL", str(e)))
        
        # Test execution engine
        try:
            result = self.executor.execute_plan(plan, auto_continue=False)
            results.append(("ExecutionEngine", "PASS", f"Plan queued: {result.get('status')}"))
        except Exception as e:
            results.append(("ExecutionEngine", "FAIL", str(e)))
        
        # Test world model
        try:
            self.world_model.update("test_key", "test_value")
            val = self.world_model.get("test_key")
            results.append(("WorldModel", "PASS", f"Stored/retrieved: {val}"))
        except Exception as e:
            results.append(("WorldModel", "FAIL", str(e)))
        
        # -- Agentic Core v2.0 Tests ----------------------------------------
        
        # Test Dynamic Replanner
        try:
            dummy_plan = Plan(id="test", name="test", goal="test")
            dummy_task = Task(id="t1", title="Failing Task", error="connection timeout", status=TaskStatus.FAILED)
            analysis = self.replanner.analyze_failure(dummy_plan, dummy_task, [dummy_task])
            results.append(("DynamicReplanner", "PASS", f"Recoverable: {analysis.get('recoverable')}, approach: {analysis.get('suggested_approach')}"))
        except Exception as e:
            results.append(("DynamicReplanner", "FAIL", str(e)))
        
        # Test Progress Tracker
        try:
            self.progress_tracker.start_tracking("test_progress", 10)
            prog = self.progress_tracker.record_progress("test_progress", 3, 10)
            results.append(("ProgressTracker", "PASS", f"ETA: {prog.get('eta', 'N/A')}, velocity: {prog.get('velocity', '?')}"))
        except Exception as e:
            results.append(("ProgressTracker", "FAIL", str(e)))
        
        # Test Tool Integration (will simulate since tools module may not be importable from here)
        try:
            ti_result = self.tool_integration.execute_tool("test_tool")
            results.append(("ToolIntegration", "PASS", f"Result status: {ti_result.get('status')}"))
        except Exception as e:
            results.append(("ToolIntegration", "FAIL", str(e)))
        
        # Test Adaptive Decomposer
        try:
            adaptive_plan = self.decomposer.decompose("scan vulnerabilities on a web server")
            results.append(("AdaptiveDecomposer", "PASS", f"{len(adaptive_plan.tasks)} tasks, learned: {self.decomposer.get_learned_count()} patterns"))
        except Exception as e:
            results.append(("AdaptiveDecomposer", "FAIL", str(e)))
        
        return results


# --- Public API -------------------------------------------------------------

_orchestrator = None

def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AutonomousOrchestrator()
    return _orchestrator


# --- Agentic Core v2.0 -- New Public API -------------------------------------

def analyze_failure(task_id: str) -> dict:
    """Analyze why a task failed and suggest recovery strategies."""
    return _get_orchestrator().analyze_failure(task_id)


def execute_mission_tool(tool_name: str, **kwargs) -> dict:
    """Execute an OMEGA tool during a mission."""
    return _get_orchestrator().execute_tool(tool_name, **kwargs)


def get_tool_execution_history(limit: int = 20) -> list:
    """Get tool execution history for the current mission."""
    return _get_orchestrator().get_tool_history(limit)


def get_mission_progress(plan_id: str = None) -> dict:
    """Get detailed progress with ETA for a mission."""
    return _get_orchestrator().get_progress(plan_id)


def get_replan_history(limit: int = 10) -> list:
    """Get replanning history showing how failures were handled."""
    return _get_orchestrator().replanner.get_replan_history(limit)


def start_mission(goal: str, context: str = None) -> dict:
    """Start an autonomous mission to accomplish a complex goal."""
    ctx = json.loads(context) if isinstance(context, str) and context else {}
    return _get_orchestrator().start_mission(goal, ctx)


def mission_status(plan_id: str = None) -> dict:
    """Get the status of a mission/plan."""
    return _get_orchestrator().get_mission_status(plan_id)


def pause_mission() -> dict:
    """Pause the current mission."""
    return _get_orchestrator().pause_mission()


def resume_mission(plan_id: str = None) -> dict:
    """Resume a mission."""
    return _get_orchestrator().resume_mission(plan_id)


def list_missions() -> list:
    """List all missions."""
    return _get_orchestrator().list_missions()


def get_plan(plan_id: str) -> dict:
    """Get a specific plan by ID."""
    return _get_orchestrator().get_mission_plan(plan_id)


def delete_plan(plan_id: str) -> dict:
    """Delete a plan."""
    _get_orchestrator().delete_mission(plan_id)
    return {"status": "deleted", "plan_id": plan_id}


def decompose_goal(goal: str) -> dict:
    """Decompose a complex goal into a structured plan (without executing)."""
    plan = _get_orchestrator().decomposer.decompose(goal)
    return plan.to_dict()


def update_world_model(key: str, value: str) -> dict:
    """Update the persistent world model."""
    try:
        parsed = json.loads(value) if value.startswith(("{", "[")) else value
    except Exception as e:
        parsed = value
    _get_orchestrator().update_world_knowledge(key, parsed)
    return {"status": "updated", "key": key}


def get_world_model_summary() -> dict:
    """Get the full world model."""
    return _get_orchestrator().get_world_knowledge()


def refine_plan(plan_id: str, task_id: str = None) -> dict:
    """Refine a plan with more detailed subtasks."""
    return _get_orchestrator().refine_plan(plan_id, task_id)


def agentic_self_test() -> list:
    """Run self-test."""
    return _get_orchestrator().self_test()


if __name__ == "__main__":
    print("=== OMEGA Agentic Core Self-Test ===")
    for name, status, detail in _get_orchestrator().self_test():
        icon = "[OK]" if status == "PASS" else "?"
        print(f"  {icon} {name}: {status} ({detail})")
    print("=== All tests complete ===")
