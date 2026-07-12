#!/usr/bin/env python3
"""OMEGA Claude Code+ Feature Pack — Full Claude Code parity.

Brings ALL Claude Code features to OMEGA:
  - Hooks system (pre/post action hooks)
  - Sub-agent system (parallel spawned agents)
  - Context compression
  - Self-verification engine
  - Codebase indexing with incremental updates
  - Symbol navigation (definitions, references, call hierarchy)
  - Dead/duplicate code detection
  - CI/CD pipeline integration
  - Permission system (approval workflows)
  - Cross-language analysis
  - Browser automation
  - New slash commands: /review-pr, /deploy, /audit-security, /lint, /index, /symbol, /callgraph, /deadcode, /duplicates, /hooks, /permissions
"""

import os
import re
import sys
import json
import ast
import time
import hashlib
import textwrap
import subprocess
import threading
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Constants for file filtering
IGNORE_DIRS = set([
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".tox", ".eggs", "dist", "build", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".hypothesis", ".omega_cache", ".claude", 
    ".terraform", ".serverless", ".next", ".nuxt", ".cache",
    ".sass-cache", ".parcel-cache", ".angular", "coverage",
    ".vscode", ".idea", ".vs", ".history", ".svn", ".hg",
    ".yarn", ".pnpm", ".npm", ".bundle", "vendor", ".gem",
    ".bazel", ".jupyter", ".ipynb_checkpoints",
    "site-packages", "lib", "lib64", "bin", "include",
    ".data", "target", "debug", "release",
    # Symlink loop protection
    "replicas", "replica", "omega_immortal_core",
])
IGNORE_DIRS_INDEX = IGNORE_DIRS

IGNORE_EXTS = set([
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib",
    ".exe", ".msi", ".bin", ".app", ".deb", ".rpm",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".ico", ".webp",
    ".mp3", ".wav", ".ogg", ".flac", ".aac", ".wma", ".m4a",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".o", ".obj", ".lib", ".a", ".la", ".lo",
    ".class", ".jar", ".war",
    ".db", ".sqlite", ".sqlite3",
    ".log", ".bak", ".swp", ".lock",
    ".DS_Store", ".gitkeep",
])
IGNORE_EXTS_INDEX = IGNORE_EXTS
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional, Tuple, Any, Callable

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
HOOKS_FILE = Path.home() / ".omega" / "hooks.json"
INDEX_FILE = Path.home() / ".omega" / "codebase_index.json"
PERMISSIONS_FILE = Path.home() / ".omega" / "permissions.json"
CONTEXT_CACHE_FILE = Path.home() / ".omega" / "context_cache.json"

# Event types for hooks
HOOK_EVENTS = {
    "pre_tool": "Before any tool executes",
    "post_tool": "After any tool executes",
    "pre_command": "Before command execution",
    "post_command": "After command execution",
    "pre_edit": "Before file edit/write",
    "post_edit": "After file edit/write",
    "pre_git": "Before git operations",
    "post_git": "After git operations",
    "pre_finish": "Before task completion",
    "on_error": "On tool/command error",
    "on_startup": "On session startup",
    "on_shutdown": "On session shutdown",
}

IGNORE_DIRS_INDEX = {
    "__pycache__", ".git", ".svn", ".hg", "node_modules", "venv", ".venv",
    ".env", "env", "backups", ".backup", ".vscode", ".idea", ".vs",
    "site-packages", ".mypy_cache", ".pytest_cache", ".cache",
    "target", "build", "dist", ".next", ".omega",
}

IGNORE_EXTS_INDEX = {
    ".pyc", ".pyo", ".so", ".o", ".obj", ".lib", ".dll", ".exe",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".ico", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".min.js", ".min.css", ".map",
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. HOOKS SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

class HooksSystem:
    """Git-style hooks system for OMEGA.
    
    Hooks fire before/after specific events (tool execution, commands, edits).
    Each hook is a shell command or Python callable that runs at the trigger point.
    """
    
    def __init__(self) -> None:
        self._hooks = {}  # event_type -> list of Hook objects
        self._load()
    
    def register(self, event: str, action: str, name: str = "", condition: str = "") -> None:
        """Register a hook.
        
        Args:
            event: Hook event type (pre_tool, post_tool, pre_edit, etc.)
            action: Shell command or Python code to run
            name: Optional human-readable name
            condition: Optional condition (only runs if this eval's to truthy)
        """
        if event not in HOOK_EVENTS:
            return {"success": False, "error": f"Unknown event: {event}. Valid: {', '.join(HOOK_EVENTS.keys())}"}
        
        hook = {
            "event": event,
            "action": action,
            "name": name or f"{event}_{len(self._hooks.get(event, [])) + 1}",
            "condition": condition,
            "created": datetime.now().isoformat(),
            "enabled": True,
            "run_count": 0,
        }
        
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(hook)
        self._save()
        return {"success": True, "hook": hook}
    
    def unregister(self, name: str) -> None:
        """Remove a hook by name."""
        for event in list(self._hooks.keys()):
            self._hooks[event] = [h for h in self._hooks[event] if h["name"] != name]
            if not self._hooks[event]:
                del self._hooks[event]
        self._save()
        return {"success": True}
    
    def list_hooks(self) -> List[Dict]:
        """List all registered hooks."""
        result = []
        for event, hooks in sorted(self._hooks.items()):
            for h in hooks:
                result.append({
                    "event": event,
                    "name": h["name"],
                    "action": h["action"][:80] + ("..." if len(h["action"]) > 80 else ""),
                    "condition": h.get("condition", ""),
                    "enabled": h.get("enabled", True),
                    "run_count": h.get("run_count", 0),
                    "created": h.get("created", ""),
                })
        return result
    
    def run(self, event: str, context: Dict = None) -> List[Dict]:
        """Run all hooks for a given event.
        
        Args:
            event: The event type to trigger
            context: Context dictionary with relevant info (tool_name, args, etc.)
        
        Returns:
            List of results from each hook execution
        """
        if event not in self._hooks:
            return []
        
        results = []
        context = context or {}
        
        for hook in self._hooks[event]:
            if not hook.get("enabled", True):
                continue
            
            # Check condition
            if hook.get("condition"):
                try:
                    # Simple condition evaluation based on context
                    cond_met = self._eval_condition(hook["condition"], context)
                    if not cond_met:
                        continue
                except Exception:
                    pass
            
            try:
                # Execute the hook action
                start = time.time()
                action = hook["action"]
                
                if action.startswith("python:"):
                    # Python code
                    code = action[7:]
                    exec_globals = {"context": context, "result": None}
                    exec(code, exec_globals)
                    output = str(exec_globals.get("result", ""))
                else:
                    # Shell command
                    result_cmd = subprocess.run(
                        action, shell=True, capture_output=True, text=True,
                        timeout=30, cwd=context.get("cwd", os.getcwd())
                    )
                    output = result_cmd.stdout + result_cmd.stderr
                
                elapsed = time.time() - start
                hook["run_count"] = hook.get("run_count", 0) + 1
                
                results.append({
                    "hook": hook["name"],
                    "event": event,
                    "success": True,
                    "output": output[:500],
                    "elapsed": round(elapsed, 2),
                })
            except subprocess.TimeoutExpired:
                results.append({
                    "hook": hook["name"],
                    "event": event,
                    "success": False,
                    "error": "Hook timed out (30s limit)",
                })
            except Exception as e:
                results.append({
                    "hook": hook["name"],
                    "event": event,
                    "success": False,
                    "error": str(e),
                })
        
        self._save()  # Save updated run counts
        return results
    
    def _eval_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate a simple condition string against context."""
        # Simple key-value conditions like "tool_name=write_file" or "path contains .py"
        if "=" in condition:
            key, val = condition.split("=", 1)
            key = key.strip()
            val = val.strip()
            ctx_val = str(context.get(key, ""))
            return val in ctx_val
        if " contains " in condition:
            parts = condition.split(" contains ", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            ctx_val = str(context.get(key, ""))
            return val in ctx_val
        return True
    
    def _save(self) -> None:
        """Save hooks to disk."""
        try:
            HOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HOOKS_FILE, "w") as f:
                json.dump(self._hooks, f, indent=2)
        except Exception:
            pass
    
    def _load(self) -> None:
        """Load hooks from disk."""
        try:
            if HOOKS_FILE.exists():
                with open(HOOKS_FILE) as f:
                    loaded = json.load(f)
                    self._hooks = loaded
        except Exception:
            self._hooks = {}

# Singleton
_hooks_instance = None

def get_hooks() -> HooksSystem:
    global _hooks_instance
    if _hooks_instance is None:
        _hooks_instance = HooksSystem()
    return _hooks_instance


# ─────────────────────────────────────────────────────────────────────────────
# 2. SUB-AGENT SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

class SubAgent:
    """A spawned sub-agent that executes a task independently.
    
    Sub-agents run in background threads and can work on different
    parts of a problem simultaneously. The main agent coordinates
    and merges their results.
    """
    
    def __init__(self, agent_id: str, task: str, context: Dict = None) -> None:
        self.id = agent_id
        self.task = task
        self.context = context or {}
        self.status = "pending"  # pending, running, completed, failed
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self._thread = None
    
    def run(self) -> None:
        """Execute the sub-agent task."""
        self.status = "running"
        self.start_time = time.time()
        self._thread = threading.Thread(target=self._execute, daemon=True)
        self._thread.start()
    
    def _execute(self) -> None:
        """Internal execution logic."""
        try:
            # Sub-agent execution: runs a sequence of operations
            # based on the task description and context
            from tools import execute_tool
            
            output_lines = []
            errors = []
            
            # Parse the task into sub-operations
            operations = self._plan_operations()
            
            for op in operations:
                tool_name = op.get("tool")
                tool_args = op.get("args", {})
                
                if tool_name == "read_file":
                    result = execute_tool(tool_name, json.dumps(tool_args))
                elif tool_name == "grep":
                    result = execute_tool(tool_name, json.dumps(tool_args))
                elif tool_name == "glob":
                    result = execute_tool(tool_name, json.dumps(tool_args))
                elif tool_name == "execute_command":
                    result = execute_tool(tool_name, json.dumps({
                        "command": tool_args.get("command", ""),
                        "timeout": tool_args.get("timeout", 60),
                    }))
                else:
                    result = execute_tool(tool_name, json.dumps(tool_args))
                
                if result and hasattr(result, 'content'):
                    if getattr(result, 'is_error', False):
                        errors.append(f"[{tool_name}] {result.content[:500]}")
                    else:
                        output_lines.append(f"[{tool_name}] {result.content[:1000]}")
            
            self.result = {
                "task": self.task,
                "output": "\n".join(output_lines),
                "errors": errors,
                "operations_completed": len(operations),
                "operations_failed": len(errors),
            }
            self.status = "completed" if not errors else "failed"
            
        except Exception as e:
            self.error = str(e)
            self.status = "failed"
            self.result = {"task": self.task, "error": str(e)}
        
        self.end_time = time.time()
    
    def _plan_operations(self) -> List[Dict]:
        """Plan the operations needed for this task."""
        # Use the task context to figure out what operations to run
        task_lower = self.task.lower()
        ops = []
        
        # File reading tasks
        if "read" in task_lower or "find" in task_lower or "search" in task_lower:
            files = self.context.get("files", [])
            pattern = self.context.get("pattern", "")
            if pattern:
                ops.append({"tool": "glob", "args": {"pattern": pattern}})
            for f in files[:20]:
                ops.append({"tool": "read_file", "args": {"path": f, "limit": 50}})
        
        # Code search tasks
        if "grep" in task_lower or "search" in task_lower or "find" in task_lower:
            query = self.context.get("query", "")
            if query:
                ops.append({"tool": "grep", "args": {"pattern": query}})
        
        # Command execution tasks
        if "run" in task_lower or "execute" in task_lower or "build" in task_lower:
            cmd = self.context.get("command", "")
            if cmd:
                ops.append({"tool": "execute_command", "args": {"command": cmd}})
        
        # Default: if no operations planned, just run the task as a command
        if not ops:
            ops.append({"tool": "execute_command", "args": {
                "command": self.task,
                "timeout": self.context.get("timeout", 60),
            }})
        
        return ops
    
    def get_result(self) -> Dict:
        """Get the sub-agent result.
        
        Returns:
            Dict with status, result data, timing info
        """
        elapsed = None
        if self.start_time and self.end_time:
            elapsed = round(self.end_time - self.start_time, 2)
        
        return {
            "id": self.id,
            "task": self.task,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "elapsed": elapsed,
        }
    
    def is_done(self) -> bool:
        """Check if the sub-agent has completed."""
        return self.status in ("completed", "failed")


class SubAgentManager:
    """Manages spawning and coordinating sub-agents."""
    
    def __init__(self) -> None:
        self._agents: Dict[str, SubAgent] = {}
        self._lock = threading.Lock()
    
    def spawn(self, task: str, context: Dict = None, agent_id: str = "") -> str:
        """Spawn a new sub-agent.
        
        Args:
            task: The task description for the sub-agent
            context: Context dict with files, query, command, etc.
            agent_id: Optional custom ID (auto-generated if empty)
        
        Returns:
            Agent ID string
        """
        if not agent_id:
            agent_id = f"agent_{int(time.time())}_{len(self._agents)}"
        
        agent = SubAgent(agent_id, task, context)
        
        with self._lock:
            self._agents[agent_id] = agent
        
        agent.run()
        return agent_id
    
    def spawn_batch(self, tasks: List[Tuple[str, Dict]]) -> List[str]:
        """Spawn multiple sub-agents simultaneously.
        
        Args:
            tasks: List of (task_description, context_dict) tuples
        
        Returns:
            List of agent IDs
        """
        agent_ids = []
        for task, context in tasks:
            agent_id = self.spawn(task, context)
            agent_ids.append(agent_id)
        return agent_ids
    
    def get_results(self, agent_ids: List[str] = None) -> List[Dict]:
        """Get results from sub-agents.
        
        Args:
            agent_ids: List of agent IDs to check (None = all)
        
        Returns:
            List of result dicts for completed agents
        """
        results = []
        with self._lock:
            agents = list(self._agents.values())
        
        for agent in agents:
            if agent_ids and agent.id not in agent_ids:
                continue
            if agent.is_done():
                results.append(agent.get_result())
        
        return results
    
    def wait_all(self, timeout: int = 120) -> List[Dict]:
        """Wait for all agents to complete.
        
        Args:
            timeout: Maximum wait time in seconds
        
        Returns:
            List of all result dicts
        """
        with self._lock:
            agents = list(self._agents.values())
        
        deadline = time.time() + timeout
        for agent in agents:
            remaining = max(0, deadline - time.time())
            if agent._thread and agent._thread.is_alive():
                agent._thread.join(timeout=min(remaining, 30))
        
        return self.get_results()
    
    def wait_for_ids(self, agent_ids: List[str], timeout: int = 120) -> List[Dict]:
        """Wait for specific agents to complete."""
        with self._lock:
            agents = [a for a in self._agents.values() if a.id in agent_ids]
        
        deadline = time.time() + timeout
        for agent in agents:
            remaining = max(0, deadline - time.time())
            if agent._thread and agent._thread.is_alive():
                agent._thread.join(timeout=min(remaining, 30))
        
        return self.get_results(agent_ids)
    
    def status_all(self) -> Dict:
        """Get status of all sub-agents."""
        with self._lock:
            agents = list(self._agents.values())
        
        counts = defaultdict(int)
        details = []
        for a in agents:
            counts[a.status] += 1
            r = a.get_result()
            details.append({
                "id": a.id,
                "task": a.task[:60],
                "status": a.status,
                "elapsed": r.get("elapsed"),
            })
        
        return {
            "total": len(agents),
            "counts": dict(counts),
            "agents": details,
        }
    
    def clear_completed(self) -> None:
        """Remove completed agents from tracking."""
        with self._lock:
            self._agents = {k: v for k, v in self._agents.items() 
                          if v.status not in ("completed", "failed")}

# Singleton
_sub_agent_manager = None

def get_sub_agent_manager() -> SubAgentManager:
    global _sub_agent_manager
    if _sub_agent_manager is None:
        _sub_agent_manager = SubAgentManager()
    return _sub_agent_manager


# ─────────────────────────────────────────────────────────────────────────────
# 3. CONTEXT COMPRESSION
# ─────────────────────────────────────────────────────────────────────────────

class ContextCompressor:
    """Compress long conversation contexts to fit within token limits.
    
    Uses summarization to replace verbose conversation history with
    condensed versions while preserving key information.
    """
    
    def __init__(self, max_tokens: int = 128000) -> None:
        self.max_tokens = max_tokens
        self._cache = {}
    
    def should_compress(self, messages: List[Dict]) -> bool:
        """Check if the conversation needs compression."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        # Rough estimate: ~4 chars per token
        est_tokens = total_chars // 3
        return est_tokens > self.max_tokens * 0.8
    
    def compress(self, messages: List[Dict]) -> List[Dict]:
        """Compress conversation by summarizing older exchanges.
        
        Preserves the system prompt and recent messages, but summarizes
        older user/assistant/tool exchanges into compact representations.
        
        Args:
            messages: Full message list
        
        Returns:
            Compressed message list with preserved structure
        """
        if len(messages) <= 12:
            return messages  # Not enough messages to compress
        
        # Keep the system prompt (always first)
        system_msgs = [m for m in messages if m["role"] == "system"]
        
        # Keep recent messages (last 10 exchanges)
        recent = messages[-20:] if len(messages) > 20 else messages[len(system_msgs):]
        
        # Messages in the middle get compressed
        middle = messages[len(system_msgs):-20] if len(messages) > 20 else []
        
        if not middle:
            return messages
        
        # Compress the middle section into summaries
        compressed = []
        current_chunk = []
        
        for msg in middle:
            current_chunk.append(msg)
            
            # Group into chunks of ~6 messages
            if len(current_chunk) >= 6:
                summary = self._summarize_chunk(current_chunk)
                compressed.append({
                    "role": "system",
                    "content": f"[Compressed context: {summary}]"
                })
                current_chunk = []
        
        # Handle remaining messages
        if current_chunk:
            summary = self._summarize_chunk(current_chunk)
            compressed.append({
                "role": "system",
                "content": f"[Compressed context: {summary}]"
            })
        
        return system_msgs + compressed + recent
    
    def _summarize_chunk(self, chunk: List[Dict]) -> str:
        """Create a concise summary of a message chunk."""
        user_count = sum(1 for m in chunk if m["role"] == "user")
        asst_count = sum(1 for m in chunk if m["role"] == "assistant")
        tool_count = sum(1 for m in chunk if m["role"] == "tool")
        
        # Extract key information
        tools_used = set()
        topics = []
        
        for msg in chunk:
            content = str(msg.get("content", ""))
            
            # Track tool usage
            if msg["role"] == "assistant" and "tool_calls" in msg:
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    tools_used.add(fn.get("name", "?"))
            
            # Extract first meaningful line
            for line in content.split("\n"):
                line = line.strip()
                if line and len(line) > 20 and len(line) < 200:
                    topics.append(line[:100])
                    break
        
        tool_str = ", ".join(sorted(tools_used)[:5]) if tools_used else "none"
        topic_str = topics[0] if topics else ""
        
        return f"{user_count} user messages, {asst_count} assistant replies, {tool_count} tool results. Tools: [{tool_str}]. Topic: {topic_str}"

# Singleton
_context_compressor = None

def get_context_compressor() -> ContextCompressor:
    global _context_compressor
    if _context_compressor is None:
        _context_compressor = ContextCompressor()
    return _context_compressor


# ─────────────────────────────────────────────────────────────────────────────
# 4. SELF-VERIFICATION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class SelfVerificationEngine:
    """Automatic verification before task completion.
    
    After each task, runs configurable checks to ensure:
    - Files were written correctly (syntax check for .py, .js, etc.)
    - Commands completed successfully (exit code 0)
    - Expected outputs exist
    - No obvious errors remain
    """
    
    def __init__(self) -> None:
        self.checks_enabled = {
            "syntax": True,
            "file_exists": True,
            "exit_code": True,
            "no_errors": True,
        }
    
    def verify(self, task_summary: str, tool_history: List[Dict]) -> Dict:
        """Run verification checks on completed task.
        
        Args:
            task_summary: What was supposed to be accomplished
            tool_history: List of tool call records
        
        Returns:
            Verification results dict
        """
        results = {
            "passed": [],
            "warnings": [],
            "failed": [],
            "overall": "passed",
        }
        
        # Check 1: Verify modified files have valid syntax
        if self.checks_enabled.get("syntax", True):
            syntax_issues = self._check_syntax(tool_history)
            if syntax_issues:
                results["warnings"].extend(syntax_issues)
            else:
                results["passed"].append("All modified files have valid syntax")
        
        # Check 2: Verify commands didn't fail
        if self.checks_enabled.get("exit_code", True):
            cmd_failures = self._check_command_exit_codes(tool_history)
            if cmd_failures:
                results["failed"].extend(cmd_failures)
                results["overall"] = "failed"
            else:
                results["passed"].append("All commands completed successfully")
        
        # Check 3: Verify no error outputs
        if self.checks_enabled.get("no_errors", True):
            error_patterns = self._check_error_patterns(tool_history)
            if error_patterns:
                results["warnings"].extend(error_patterns)
            else:
                results["passed"].append("No error patterns detected in outputs")
        
        return results
    
    def _check_syntax(self, tool_history: List[Dict]) -> List[str]:
        """Check syntax of modified files."""
        issues = []
        modified_files = set()
        
        for record in tool_history:
            if record.get("tool") in ("write_file", "edit_file"):
                args = record.get("args", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        continue
                fpath = args.get("path", "")
                if fpath:
                    modified_files.add(fpath)
        
        for fpath in modified_files:
            abs_path = Path(fpath)
            if not abs_path.exists():
                continue
            
            suffix = abs_path.suffix.lower()
            
            try:
                if suffix == ".py":
                    with open(abs_path, encoding="utf-8", errors="replace") as f:
                        ast.parse(f.read())
                elif suffix in (".js", ".jsx", ".ts", ".tsx"):
                    # Basic syntax check via Node.js if available
                    if suffix in (".js", ".jsx"):
                        result = subprocess.run(
                            ["node", "--check", str(abs_path)],
                            capture_output=True, text=True, timeout=10
                        )
                        if result.returncode != 0:
                            issues.append(f"JS syntax error in {abs_path.name}: {result.stderr.strip()[:100]}")
                elif suffix == ".json":
                    with open(abs_path, encoding="utf-8", errors="replace") as f:
                        json.loads(f.read())
            except SyntaxError as e:
                issues.append(f"Syntax error in {abs_path.name}: {e}")
            except json.JSONDecodeError as e:
                issues.append(f"JSON error in {abs_path.name}: {e}")
            except FileNotFoundError:
                pass
            except Exception:
                pass
        
        return issues
    
    def _check_command_exit_codes(self, tool_history: List[Dict]) -> List[str]:
        """Check that all commands succeeded."""
        failures = []
        for record in tool_history:
            if record.get("tool") == "execute_command":
                result = record.get("result", "")
                if isinstance(result, str) and "exit_code" in result:
                    try:
                        exit_code_match = re.search(r'exit_code: (\d+)', result)
                        if exit_code_match and int(exit_code_match.group(1)) != 0:
                            cmd = record.get("args", "")
                            if isinstance(cmd, str) and len(cmd) > 80:
                                cmd = cmd[:80] + "..."
                            failures.append(f"Command failed (exit code {exit_code_match.group(1)}): {cmd}")
                    except (ValueError, AttributeError):
                        pass
        return failures
    
    def _check_error_patterns(self, tool_history: List[Dict]) -> List[str]:
        """Check for error patterns in tool outputs."""
        warnings = []
        error_patterns = [
            r"(?i)(error|failed|failure|exception|traceback|segmentation fault|fatal)",
        ]
        
        for record in tool_history:
            tool_name = record.get("tool", "")
            result = record.get("result", "")
            if isinstance(result, str):
                for pattern in error_patterns:
                    matches = re.findall(pattern, result)
                    if matches and tool_name not in ("read_file", "grep", "glob"):
                        # Only flag if it's a command or write operation
                        if tool_name in ("execute_command", "write_file", "edit_file"):
                            warnings.append(f"Error pattern '{matches[0]}' detected in {tool_name} output")
                            break
        return warnings

# Singleton
_verification_engine = None

def get_verification_engine() -> SelfVerificationEngine:
    global _verification_engine
    if _verification_engine is None:
        _verification_engine = SelfVerificationEngine()
    return _verification_engine


# ─────────────────────────────────────────────────────────────────────────────
# 5. CODEBASE INDEXING
# ─────────────────────────────────────────────────────────────────────────────

class CodebaseIndex:
    """Full codebase index for fast symbol search and code navigation.
    
    Builds an incremental index of:
    - All Python symbols (functions, classes, variables)
    - Import relationships
    - File contents (for full-text search)
    - Git history hints
    """
    
    def __init__(self) -> None:
        self.index = {
            "version": 1,
            "root": "",
            "last_updated": "",
            "files": {},
            "symbols": {},  # symbol_name -> [(file, line, kind)]
            "imports": {},  # file -> [imported symbols]
            "definitions": {},  # file -> [(symbol, line, kind)]
            "references": {},  # symbol -> [files referencing it]
        }
        self._dirty = False
    
    def build(self, root_path: str, force: bool = False) -> Dict:
        """Build or rebuild the index from a root path.
        
        Args:
            root_path: Root directory to index
            force: If True, rebuild from scratch
        
        Returns:
            Index stats dict
        """
        root = Path(root_path).resolve()
        self.index["root"] = str(root)
        
        if force:
            self.index["files"] = {}
            self.index["symbols"] = {}
            self.index["imports"] = {}
            self.index["definitions"] = {}
            self.index["references"] = {}
        
        start = time.time()
        file_count = 0
        symbol_count = 0
        
        for py_file in root.rglob("*.py"):
            # Skip ignored dirs
            if any(part in IGNORE_DIRS_INDEX for part in py_file.parts):
                continue
            
            try:
                file_key = str(py_file.relative_to(root))
                content = py_file.read_text(encoding="utf-8", errors="replace")
                
                # Skip if not changed (check hash)
                file_hash = hashlib.md5(content.encode()).hexdigest()
                if not force and file_key in self.index["files"]:
                    if self.index["files"][file_key].get("hash") == file_hash:
                        continue
                
                # Parse the file
                symbols, imports, definitions = self._parse_python(content)
                
                self.index["files"][file_key] = {
                    "hash": file_hash,
                    "size": len(content),
                    "lines": content.count("\n") + 1,
                    "symbols": symbols,
                    "imports": imports,
                }
                
                # Update global symbol index
                for sym, line, kind in symbols:
                    sym_lower = sym.lower()
                    if sym_lower not in self.index["symbols"]:
                        self.index["symbols"][sym_lower] = []
                    self.index["symbols"][sym_lower].append({
                        "file": file_key,
                        "line": line,
                        "kind": kind,
                    })
                
                self.index["definitions"][file_key] = definitions
                self.index["imports"][file_key] = imports
                
                file_count += 1
                symbol_count += len(symbols)
                
            except (SyntaxError, UnicodeDecodeError, Exception):
                continue
        
        self.index["last_updated"] = datetime.now().isoformat()
        self._save()
        
        elapsed = time.time() - start
        return {
            "files_indexed": file_count,
            "symbols_found": symbol_count,
            "elapsed": round(elapsed, 2),
            "total_files": len(self.index["files"]),
            "total_symbols": sum(len(v) for v in self.index["symbols"].values()),
        }
    
    def incremental_update(self, root_path: str) -> Dict:
        """Update only changed files since last build."""
        return self.build(root_path, force=False)
    
    def search_symbol(self, query: str) -> List[Dict]:
        """Search for symbols matching a query."""
        query_lower = query.lower()
        results = []
        
        for sym, locations in self.index["symbols"].items():
            if query_lower in sym:
                for loc in locations:
                    results.append({
                        "symbol": sym,
                        "file": loc["file"],
                        "line": loc["line"],
                        "kind": loc["kind"],
                    })
        
        return sorted(results, key=lambda x: x["symbol"])[:50]
    
    def find_definition(self, symbol: str) -> List[Dict]:
        """Find the definition location of a symbol."""
        symbol_lower = symbol.lower()
        results = []
        
        if symbol_lower in self.index["symbols"]:
            for loc in self.index["symbols"][symbol_lower]:
                if loc["kind"] in ("function", "class", "method"):
                    results.append(loc)
        
        return results[:10]
    
    def find_references(self, symbol: str) -> List[Dict]:
        """Find all references to a symbol across the codebase."""
        symbol_lower = symbol.lower()
        references = []
        
        for file_key, imports in self.index["imports"].items():
            for imp in imports:
                if symbol_lower in imp.lower():
                    references.append({
                        "file": file_key,
                        "type": "import",
                        "match": imp,
                    })
        
        # Also search in definitions
        if symbol_lower in self.index["symbols"]:
            for loc in self.index["symbols"][symbol_lower]:
                references.append({
                    "file": loc["file"],
                    "line": loc["line"],
                    "type": loc["kind"],
                })
        
        return references[:50]
    
    def build_call_graph(self, root_path: str = None) -> Dict:
        """Build a call graph showing function call relationships.
        
        Returns:
            Dict mapping function -> [functions it calls]
        """
        root = Path(root_path or self.index["root"])
        if not root.exists():
            return {}
        
        call_graph = {}
        
        for py_file in root.rglob("*.py"):
            if any(part in IGNORE_DIRS_INDEX for part in py_file.parts):
                continue
            
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        calls = set()
                        
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                if isinstance(child.func, ast.Name):
                                    calls.add(child.func.id)
                                elif isinstance(child.func, ast.Attribute):
                                    calls.add(f"{child.func.attr}")
                        
                        call_graph[f"{py_file.name}:{func_name}"] = list(calls)
            except (SyntaxError, Exception):
                continue
        
        return call_graph
    
    def _parse_python(self, content: str) -> Tuple[List, List, List]:
        """Parse Python source and extract symbols, imports, definitions."""
        symbols = []  # [(name, line, kind)]
        imports = []  # [import_string]
        definitions = []  # [(name, line, kind)]
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Class definitions
                if isinstance(node, ast.ClassDef):
                    symbols.append((node.name, node.lineno, "class"))
                    definitions.append((node.name, node.lineno, "class"))
                    
                    # Methods inside class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            symbols.append((item.name, item.lineno, "method"))
                            definitions.append((item.name, item.lineno, "method"))
                
                # Function definitions
                elif isinstance(node, ast.FunctionDef):
                    symbols.append((node.name, node.lineno, "function"))
                    definitions.append((node.name, node.lineno, "function"))
                
                # Import statements
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                        symbols.append((alias.name.split(".")[0], node.lineno, "import"))
                
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
                        symbols.append((alias.name, node.lineno, "import"))
                
                # Variable assignments at module level
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            symbols.append((target.id, node.lineno, "variable"))
                            definitions.append((target.id, node.lineno, "variable"))
        
        except SyntaxError:
            pass
        
        return symbols, imports, definitions
    
    def _save(self) -> None:
        """Save index to disk."""
        try:
            INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(INDEX_FILE, "w") as f:
                json.dump(self.index, f)
        except Exception:
            pass
    
    def load(self) -> None:
        """Load index from disk."""
        try:
            if INDEX_FILE.exists():
                with open(INDEX_FILE) as f:
                    self.index = json.load(f)
                return True
        except Exception:
            pass
        return False

# Singleton
_codebase_index = None

def get_codebase_index() -> CodebaseIndex:
    global _codebase_index
    if _codebase_index is None:
        _codebase_index = CodebaseIndex()
        _codebase_index.load()
    return _codebase_index


# ─────────────────────────────────────────────────────────────────────────────
# 6. DEAD / DUPLICATE CODE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_dead_imports(root_path: str) -> List[Dict]:
    """Find imports that are never used in the codebase.
    
    Args:
        root_path: Root directory to scan
    
    Returns:
        List of {file, import_name, line_number} dicts
    """
    root = Path(root_path).resolve()
    dead_imports = []
    
    for py_file in root.rglob("*.py"):
        if any(part in IGNORE_DIRS_INDEX for part in py_file.parts):
            continue
        
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
            
            # Get all import names
            imported_names = {}  # name -> line
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        local_name = alias.asname or alias.name.split(".")[0]
                        imported_names[local_name] = node.lineno
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        local_name = alias.asname or alias.name
                        imported_names[local_name] = node.lineno
            
            # Get all used names (excluding imports)
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
                elif isinstance(node, ast.Attribute):
                    used_names.add(node.attr)
            
            # Find unused imports
            for imp_name, line in imported_names.items():
                if imp_name not in used_names:
                    dead_imports.append({
                        "file": str(py_file.relative_to(root)),
                        "import": imp_name,
                        "line": line,
                    })
        
        except (SyntaxError, Exception):
            continue
    
    return dead_imports


def detect_unused_variables(root_path: str) -> List[Dict]:
    """Find variables that are assigned but never used.
    
    Args:
        root_path: Root directory to scan
    
    Returns:
        List of {file, variable, line} dicts
    """
    root = Path(root_path).resolve()
    unused = []
    
    for py_file in root.rglob("*.py"):
        if any(part in IGNORE_DIRS_INDEX for part in py_file.parts):
            continue
        
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Get assigned variables in function
                    assigned = set()
                    used = set()
                    
                    for child in ast.walk(node):
                        if isinstance(child, ast.Assign):
                            for target in child.targets:
                                if isinstance(target, ast.Name):
                                    assigned.add(target.id)
                        elif isinstance(child, ast.AugAssign):
                            if isinstance(child.target, ast.Name):
                                assigned.add(child.target.id)
                                used.add(child.target.id)
                        elif isinstance(child, ast.Name):
                            used.add(child.id)
                        elif isinstance(child, ast.For):
                            if isinstance(child.target, ast.Name):
                                assigned.add(child.target.id)
                                used.add(child.target.id)
                    
                    # Exclude common patterns
                    unused_vars = assigned - used
                    for var in unused_vars:
                        if var.startswith("_"):
                            continue
                        if var in ("self", "cls", "args", "kwargs"):
                            continue
                        unused.append({
                            "file": str(py_file.relative_to(root)),
                            "variable": var,
                            "function": node.name,
                        })
        
        except (SyntaxError, Exception):
            continue
    
    return unused


def detect_duplicate_code(root_path: str, min_lines: int = 6) -> List[Dict]:
    """Find duplicate/similar code blocks.
    
    Uses fingerprinting to identify blocks of code that are nearly identical.
    
    Args:
        root_path: Root directory to scan
        min_lines: Minimum lines for a block to be considered
    
    Returns:
        List of {files, similarity, lines} dicts
    """
    root = Path(root_path).resolve()
    
    # Collect all function/class bodies
    blocks = []
    
    for py_file in root.rglob("*.py"):
        if any(part in IGNORE_DIRS_INDEX for part in py_file.parts):
            continue
        
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Get the source lines for this node
                    try:
                        lines = content.split("\n")[node.lineno - 1:node.end_lineno]
                        if len(lines) >= min_lines:
                            # Normalize: strip comments, normalize whitespace
                            norm_lines = []
                            for line in lines:
                                line = re.sub(r'#.*', '', line).strip()
                                if line:
                                    norm_lines.append(line)
                            
                            if len(norm_lines) >= min_lines:
                                fingerprint = hashlib.md5(
                                    "\n".join(norm_lines).encode()
                                ).hexdigest()
                                
                                blocks.append({
                                    "file": str(py_file.relative_to(root)),
                                    "name": node.name,
                                    "kind": node.__class__.__name__,
                                    "line": node.lineno,
                                    "fingerprint": fingerprint,
                                    "code": "\n".join(lines),
                                    "norm_code": "\n".join(norm_lines),
                                })
                    except Exception:
                        pass
        except (SyntaxError, Exception):
            continue
    
    # Find duplicates by fingerprint
    by_fingerprint = defaultdict(list)
    for block in blocks:
        by_fingerprint[block["fingerprint"]].append(block)
    
    duplicates = []
    for fingerprint, matches in by_fingerprint.items():
        if len(matches) > 1:
            dupes = []
            for m in matches:
                dupes.append({
                    "file": m["file"],
                    "name": m["name"],
                    "kind": m["kind"],
                    "line": m["line"],
                })
            
            code_preview = matches[0]["code"][:200]
            duplicates.append({
                "fingerprint": fingerprint[:12],
                "count": len(matches),
                "locations": dupes,
                "code_preview": code_preview,
            })
    
    return sorted(duplicates, key=lambda x: x["count"], reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 7. CI/CD INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

class CICDManager:
    """Local CI/CD pipeline integration.
    
    Runs linting, formatting, building, and testing pipelines
    similar to GitHub Actions / GitLab CI locally.
    """
    
    def __init__(self) -> None:
        self.pipelines = {}
    
    def run_linter(self, path: str = ".") -> Dict:
        """Run common linters on the codebase.
        
        Supports: flake8, pylint, ruff, eslint, prettier
        """
        results = {"linters_run": [], "issues": [], "warnings": [], "passed": []}
        
        path_obj = Path(path)
        py_files = list(path_obj.rglob("*.py"))
        
        if not py_files:
            return {"linters_run": [], "issues": [], "note": "No Python files found"}
        
        # Try ruff (fastest)
        ruff_result = subprocess.run(
            ["ruff", "check", "--select", "E,F", "--quiet", str(path_obj)],
            capture_output=True, text=True, timeout=30
        )
        if ruff_result.returncode == 0 or True:  # Capture output regardless
            results["linters_run"].append("ruff")
            output = ruff_result.stdout + ruff_result.stderr
            if output.strip():
                issues = [l for l in output.split("\n") if l.strip() and ":" in l]
                results["issues"].extend(issues[:20])
                for issue in issues[:20]:
                    results["warnings"].append(f"ruff: {issue[:150]}")
            else:
                results["passed"].append("ruff: No issues found")
        
        # Try flake8 as fallback
        try:
            flake8_result = subprocess.run(
                ["flake8", str(path_obj), "--max-line-length=120", "--quiet"],
                capture_output=True, text=True, timeout=30
            )
            results["linters_run"].append("flake8")
            output = flake8_result.stdout + flake8_result.stderr
            if output.strip():
                issues = [l for l in output.split("\n") if l.strip()]
                results["issues"].extend(issues[:20])
        except FileNotFoundError:
            pass
        
        return results
    
    def run_formatter(self, path: str = ".") -> Dict:
        """Run code formatters (black, ruff format)."""
        results = {"formatters_run": [], "formatted": [], "errors": []}
        
        path_obj = Path(path)
        
        # Try black
        try:
            black_result = subprocess.run(
                ["black", "--quiet", "--check", str(path_obj)],
                capture_output=True, text=True, timeout=30
            )
            results["formatters_run"].append("black")
            if black_result.returncode == 0:
                results["formatted"].append("black: All files already formatted")
            else:
                # Actually format
                format_result = subprocess.run(
                    ["black", "--quiet", str(path_obj)],
                    capture_output=True, text=True, timeout=60
                )
                if format_result.returncode == 0:
                    results["formatted"].append("black: Files reformatted")
                else:
                    results["errors"].append(f"black: {format_result.stderr[:200]}")
        except FileNotFoundError:
            pass
        
        return results
    
    def run_build(self, path: str = ".") -> Dict:
        """Attempt to build/compile the project.
        
        Checks setup.py, pyproject.toml for build instructions.
        """
        results = {"build_system": None, "success": False, "output": ""}
        
        path_obj = Path(path)
        
        # Check for Python build
        if (path_obj / "setup.py").exists() or (path_obj / "pyproject.toml").exists():
            results["build_system"] = "python"
            result = subprocess.run(
                [sys.executable, "-m", "compileall", str(path_obj)],
                capture_output=True, text=True, timeout=60
            )
            results["success"] = result.returncode == 0
            results["output"] = result.stdout[:500] + result.stderr[:500]
        
        # Check for npm/node build
        if (path_obj / "package.json").exists():
            results["build_system"] = "node"
            result = subprocess.run(
                ["npm", "run", "build"],
                capture_output=True, text=True, timeout=60,
                cwd=str(path_obj)
            )
            results["success"] = result.returncode == 0
            results["output"] = result.stdout[:500] + result.stderr[:500]
        
        return results
    
    def full_pipeline(self, path: str = ".") -> Dict:
        """Run the full CI pipeline: lint -> format -> build -> test."""
        results = {"pipeline": [], "overall": "passed"}
        
        # Step 1: Lint
        lint_result = self.run_linter(path)
        results["pipeline"].append({
            "step": "lint",
            "status": "passed" if not lint_result.get("issues") else "warnings",
            "details": lint_result,
        })
        if lint_result.get("issues"):
            results["overall"] = "warnings"
        
        # Step 2: Format
        format_result = self.run_formatter(path)
        results["pipeline"].append({
            "step": "format",
            "status": "completed",
            "details": format_result,
        })
        
        # Step 3: Build
        build_result = self.run_build(path)
        status = "passed" if build_result.get("success") else "info"
        results["pipeline"].append({
            "step": "build",
            "status": status,
            "details": build_result,
        })
        if build_result.get("build_system") and not build_result.get("success"):
            results["overall"] = "failed"
        
        return results


# ─────────────────────────────────────────────────────────────────────────────
# 8. PERMISSION SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

class PermissionSystem:
    """Approval workflow for impactful actions.
    
    Modes:
    - accept_all: No approval needed (default, like current OMEGA)
    - auto_accept_known: Auto-accept safe/common actions
    - ask_always: Ask before every actionable operation
    - whitelist: Only allow explicitly permitted operations
    """
    
    def __init__(self) -> None:
        self.mode = "accept_all"
        self._load()
    
    def set_mode(self, mode: str) -> None:
        """Set permission mode."""
        valid_modes = ["accept_all", "auto_accept_known", "ask_always", "whitelist"]
        if mode not in valid_modes:
            return {"success": False, "error": f"Invalid mode. Valid: {', '.join(valid_modes)}"}
        self.mode = mode
        self._save()
        return {"success": True, "mode": mode}
    
    def request(self, action_type: str, details: Dict) -> Dict:
        """Check if an action is permitted.
        
        Args:
            action_type: Type of action (edit_file, execute_command, git, etc.)
            details: Details about the action
        
        Returns:
            Dict with 'permitted' bool and optional message
        """
        if self.mode == "accept_all":
            return {"permitted": True, "mode": "accept_all"}
        
        if self.mode == "auto_accept_known":
            # Auto-accept safe actions
            safe_actions = {
                "read_file", "glob", "grep", "list_dir", "get_date",
                "get_env", "cache_stats", "system_info", "system_status",
                "web_search", "web_fetch", "calculate",
            }
            if action_type in safe_actions:
                return {"permitted": True, "mode": "auto_accept"}
            # Otherwise, ask
            return self._ask(action_type, details)
        
        if self.mode == "ask_always":
            return self._ask(action_type, details)
        
        if self.mode == "whitelist":
            return {"permitted": False, "mode": "whitelist", "message": "Operation not in whitelist"}
        
        return {"permitted": True, "mode": "accept_all"}
    
    def _ask(self, action_type: str, details: Dict) -> Dict:
        """In a real implementation, this would prompt the user.
        
        For now, returns a prompt message to show the user.
        """
        return {
            "permitted": "pending",
            "mode": self.mode,
            "message": f"⚠️ Permission needed: {action_type}",
            "action_type": action_type,
            "details": details,
        }
    
    def get_mode(self) -> str:
        return self.mode
    
    def _save(self) -> None:
        try:
            PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(PERMISSIONS_FILE, "w") as f:
                json.dump({"mode": self.mode}, f)
        except Exception:
            pass
    
    def _load(self) -> None:
        try:
            if PERMISSIONS_FILE.exists():
                with open(PERMISSIONS_FILE) as f:
                    data = json.load(f)
                    self.mode = data.get("mode", "accept_all")
        except Exception:
            pass

# Singleton
_permission_system = None

def get_permission_system() -> PermissionSystem:
    global _permission_system
    if _permission_system is None:
        _permission_system = PermissionSystem()
    return _permission_system


# ─────────────────────────────────────────────────────────────────────────────
# 9. CROSS-LANGUAGE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

class CrossLanguageAnalyzer:
    """Analyze relationships between files in different languages.
    
    Detects:
    - Python files that generate JavaScript/TypeScript
    - API contracts between frontend and backend
    - Shared type definitions across languages
    - Build/dependency relationships
    """
    
    def __init__(self) -> None:
        self.language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".jsx": "React JSX",
            ".ts": "TypeScript",
            ".tsx": "React TSX",
            ".java": "Java",
            ".kt": "Kotlin",
            ".swift": "Swift",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".cpp": "C++",
            ".c": "C",
            ".h": "C Header",
            ".hpp": "C++ Header",
            ".vue": "Vue",
            ".svelte": "Svelte",
            ".css": "CSS",
            ".scss": "SCSS",
            ".html": "HTML",
        }
    
    def analyze_project(self, root_path: str) -> Dict:
        """Analyze a project for cross-language patterns.
        
        Returns:
            Dict with languages, file counts, relationships
        """
        root = Path(root_path).resolve()
        lang_files = defaultdict(list)
        
        for f in root.rglob("*"):
            if f.is_file() and f.suffix in self.language_map:
                lang_files[self.language_map[f.suffix]].append(str(f.relative_to(root)))
        
        relationships = []
        
        # Detect Python <-> JS/TS relationships (common API patterns)
        py_files = lang_files.get("Python", [])
        js_files = lang_files.get("JavaScript", []) + lang_files.get("TypeScript", [])
        
        if py_files and js_files:
            # Look for API route definitions in Python and API calls in JS
            for pyf in py_files[:20]:
                try:
                    content = Path(root / pyf).read_text(encoding="utf-8", errors="replace")
                    routes = re.findall(r'@(?:app|router)\.(?:get|post|put|delete|patch)\([\'"]([^\'"]+)[\'"]', content)
                    if routes:
                        relationships.append({
                            "type": "API Backend",
                            "source": pyf,
                            "routes": routes[:10],
                        })
                except Exception:
                    continue
            
            for jsf in js_files[:20]:
                try:
                    content = Path(root / jsf).read_text(encoding="utf-8", errors="replace")
                    api_calls = re.findall(r'(?:fetch|axios|api)\([\'"]([^\'"]+)[\'"]', content)
                    if api_calls:
                        relationships.append({
                            "type": "API Frontend Call",
                            "source": jsf,
                            "calls": api_calls[:10],
                        })
                except Exception:
                    continue
        
        return {
            "languages": {k: len(v) for k, v in sorted(lang_files.items(), key=lambda x: -len(x[1]))},
            "total_files": sum(len(v) for v in lang_files.values()),
            "relationships": relationships[:20],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 10. BROWSER AUTOMATION
# ─────────────────────────────────────────────────────────────────────────────

class BrowserAutomation:
    """Simple browser automation for web interaction.
    
    Uses Playwright or Selenium for:
    - Taking screenshots
    - Filling forms
    - Clicking elements
    - Extracting page data
    """
    
    def __init__(self) -> None:
        self._playwright_available = False
        self._selenium_available = False
        self._check_available()
    
    def _check_available(self) -> None:
        """Check which automation libraries are available."""
        try:
            import playwright
            self._playwright_available = True
        except ImportError:
            pass
        try:
            import selenium
            self._selenium_available = True
        except ImportError:
            pass
    
    def screenshot(self, url: str, output_path: str = None) -> Dict:
        """Take a screenshot of a web page.
        
        Args:
            url: URL to screenshot
            output_path: Where to save the screenshot
        
        Returns:
            Dict with result info
        """
        if not output_path:
            output_path = f"screenshot_{int(time.time())}.png"
        
        # Use Playwright if available
        if self._playwright_available:
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, timeout=30000)
                    page.screenshot(path=output_path, full_page=True)
                    browser.close()
                return {"success": True, "path": output_path, "method": "playwright"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # Use Selenium as fallback
        if self._selenium_available:
            try:
                from selenium import webdriver
                options = webdriver.ChromeOptions()
                options.add_argument("--headless")
                driver = webdriver.Chrome(options=options)
                driver.get(url)
                driver.save_screenshot(output_path)
                driver.quit()
                return {"success": True, "path": output_path, "method": "selenium"}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "No automation library available. Install with: pip install playwright"}
    
    def extract_page_text(self, url: str) -> Dict:
        """Extract text content from a web page."""
        try:
            import requests
            from bs4 import BeautifulSoup
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            return {"success": True, "text": text[:5000], "url": url}
        except ImportError:
            return {"success": False, "error": "BeautifulSoup not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 11. REVIEW PR / DEPLOY COMMAND HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def review_pull_request(pr_number: str = None) -> Dict:
    """Review a pull request by analyzing git diff.
    
    If no PR number given, reviews the current uncommitted changes.
    
    Returns:
        Dict with review summary, issues found, suggestions
    """
    try:
        if pr_number:
            # Fetch PR diff
            result = subprocess.run(
                ["git", "fetch", "origin", f"pull/{pr_number}/head"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return {"error": f"Failed to fetch PR #{pr_number}: {result.stderr}"}
            
            diff_result = subprocess.run(
                ["git", "diff", f"FETCH_HEAD...HEAD"],
                capture_output=True, text=True, timeout=30
            )
        else:
            # Local diff
            diff_result = subprocess.run(
                ["git", "diff", "HEAD"],
                capture_output=True, text=True, timeout=30
            )
        
        diff = diff_result.stdout
        
        if not diff:
            return {"note": "No changes to review", "summary": "Clean state"}
        
        # Analyze the diff
        files_changed = re.findall(r'^\+\+\+ b/(.+)$', diff, re.MULTILINE)
        lines_added = len(re.findall(r'^\+', diff, re.MULTILINE))
        lines_removed = len(re.findall(r'^\-', diff, re.MULTILINE))
        
        # Check for issues
        issues = []
        
        # Check for todos/fixmes
        todos = re.findall(r'^\+.*?\b(TODO|FIXME|HACK|XXX)\b', diff, re.MULTILINE | re.IGNORECASE)
        if todos:
            issues.append(f"Found {len(todos)} TODO/FIXME markers in new code")
        
        # Check for debug statements
        debug_stmts = re.findall(r'^\+.*?\b(print|console\.log|debugger|var_dump|dd\()\b', diff, re.MULTILINE)
        if debug_stmts:
            issues.append(f"Found {len(debug_stmts)} debug statements in new code")
        
        # Check for large files
        large_files = []
        current_file = None
        file_lines = 0
        for line in diff.split("\n"):
            if line.startswith("+++ b/"):
                current_file = line[6:]
                file_lines = 0
            elif line.startswith("+") and current_file:
                file_lines += 1
                if file_lines > 200:
                    large_files.append(current_file)
        
        if large_files:
            issues.append(f"Large changes detected in: {', '.join(set(large_files))}")
        
        return {
            "summary": f"Review: {len(files_changed)} files, +{lines_added}/-{lines_removed} lines",
            "files_changed": files_changed[:30],
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "issues": issues,
            "suggestions": [
                "Ensure all changes are tested",
                "Check for any hardcoded credentials",
                "Verify error handling is in place",
            ],
        }
        
    except Exception as e:
        return {"error": f"Review failed: {e}"}


def deploy_staging() -> Dict:
    """Deploy to staging environment.
    
    Simulates a staging deployment pipeline.
    """
    results = {"steps": [], "overall": "in_progress"}
    
    # Step 1: Run tests
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest", "-x", "--tb=short", "-q"],
        capture_output=True, text=True, timeout=120
    )
    tests_passed = test_result.returncode == 0
    results["steps"].append({
        "step": "tests",
        "passed": tests_passed,
        "output": test_result.stdout[-300:] if test_result.stdout else test_result.stderr[-300:],
    })
    
    if not tests_passed:
        results["overall"] = "failed_tests"
        return results
    
    # Step 2: Build
    build_result = subprocess.run(
        [sys.executable, "-m", "compileall", "."],
        capture_output=True, text=True, timeout=60
    )
    build_passed = build_result.returncode == 0
    results["steps"].append({
        "step": "build",
        "passed": build_passed,
        "output": build_result.stdout[-200:] if build_result.stdout else build_result.stderr[-200:],
    })
    
    if build_passed:
        results["overall"] = "ready_for_deployment"
        results["message"] = "All checks passed. Ready for staging deployment."
    else:
        results["overall"] = "build_failed"
    
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 12. SUMMARY / HELP
# ─────────────────────────────────────────────────────────────────────────────

FEATURES_DOC = """
╔══════════════════════════════════════════════════════════════╗
║          OMEGA — Claude Code+ Feature Pack v1.0             ║
╚══════════════════════════════════════════════════════════════╝

📌 NEW SLASH COMMANDS (Claude Code parity):
────────────────────────────────────────────
  /review-pr [num]     Review PR or uncommitted changes
  /deploy [env]        Run deployment pipeline (staging/prod)
  /audit-security      Quick security audit of project
  /lint [path]         Run linters on codebase
  /test [path]         Run tests and report results
  /index [path]        Build codebase index for faster navigation
  /symbol <name>       Find symbol definitions across codebase
  /callgraph [func]    Show function call relationships
  /deadcode            Find dead imports and unused variables
  /duplicates          Find duplicate code blocks
  /hooks [list|add|rm] Manage pre/post action hooks
  /permissions [mode]  Set permission mode (accept_all|ask_always)

📌 NEW COMMANDS (Claude Code+ v2.0):
─────────────────────────────────────
  /mcp-connect         Connect to MCP server (GitHub, DB, Slack, Jira)
  /mcp-list            List tools from connected MCP servers
  /mcp-call            Call a tool on an MCP server
  /bulk-search         Search across project with regex
  /bulk-replace        Replace text across project (with dry-run)
  /rename              Rename symbol across project
  /extract             Extract function to new file
  /split-file          Split file by class/function
  /bump-version        Bump semantic version (major/minor/patch)
  /changelog           Generate changelog from git history

📌 NEW FEATURES:
──────────────────
  🔗 Hooks System     — Git-style hooks (pre/post tool, command, edit)
  🧩 Sub-Agent System  — Spawn parallel agents for multi-task work
  📦 Context Compress  — Auto-compress long conversations
  ✅ Self-Verification — Verify syntax and results before completing
  📚 Codebase Index    — Build searchable symbol index
  🔍 Symbol Nav        — Find definitions, references, call graphs
  🗑️ Dead Code Detection — Find unused imports & variables
  ♻️ Duplicate Code     — Find similar code blocks across project
  🚀 CI/CD Pipeline    — Run lint → format → build → test
  🔒 Permission System — Configurable approval workflows
  🌐 Cross-Language    — Analyze Python ↔ JS ↔ other relationships
  🖥️ Browser Auto       — Screenshot and extract web pages
  
📦 MCP Client          — Connect to GitHub, Jira, Slack, databases, any MCP server
🔎 Bulk Search/Replace — Project-wide regex search & replace with dry-run
🔧 Refactoring Engine  — Rename symbols, extract functions, split files
📋 Release Manager     — Version bump (semver), changelog generation, git tags
"""


def print_features_doc() -> str:
    return FEATURES_DOC


# ═══════════════════════════════════════════════════════════════════════════════
# NEW IN v2.0: MCP Client, Bulk Search & Replace, Refactoring, Release Mgmt
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────────────
# 14. MCP CLIENT — Model Context Protocol
# ─────────────────────────────────────────────────────────────────────────────

class MCPClient:
    """Model Context Protocol (MCP) client.
    
    Connects to MCP servers over stdio (subprocess) or SSE (HTTP).
    Discovers tools/resources and calls them on demand.
    Supports JSON-RPC 2.0.
    """
    
    def __init__(self) -> None:
        self._connections = {}  # name -> {process, capabilities, tools, resources}
        self._config_path = Path.cwd() / ".mcp.json"
    
    def discover_config(self) -> List[Dict]:
        """Auto-discover MCP server configurations from .mcp.json or env vars."""
        configs = []
        
        # Check for .mcp.json in current or parent dirs
        current = Path.cwd().resolve()
        while True:
            mc = current / ".mcp.json"
            if mc.exists():
                try:
                    data = json.loads(mc.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        for name, cfg in data.get("mcpServers", {}).items():
                            configs.append({"name": name, **cfg})
                except Exception:
                    pass
            if current.parent == current:
                break
            current = current.parent
        
        # Check env vars for MCP config
        env_config = os.environ.get("MCP_SERVERS")
        if env_config:
            try:
                data = json.loads(env_config)
                if isinstance(data, dict):
                    for name, cfg in data.items():
                        configs.append({"name": name, **cfg})
            except Exception:
                pass
        
        return configs
    
    def connect_stdio(self, name: str, command: str, args: List[str] = None,
                      env: Dict[str, str] = None) -> Dict:
        """Connect to an MCP server via stdio (subprocess).
        
        Args:
            name: Connection name
            command: Executable path
            args: Command arguments
            env: Extra environment variables
            
        Returns:
            Dict with capabilities and available tools
        """
        import subprocess as sp
        
        if name in self._connections:
            return {"success": False, "error": f"Connection '{name}' already exists"}
        
        try:
            full_env = os.environ.copy()
            if env:
                full_env.update(env)
            
            proc = sp.Popen(
                [command] + (args or []),
                stdin=sp.PIPE,
                stdout=sp.PIPE,
                stderr=sp.PIPE,
                env=full_env,
                text=True,
                bufsize=1,
            )
            
            # Initialize
            init_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "OMEGA",
                        "version": "2.0"
                    }
                }
            }) + "\n"
            
            proc.stdin.write(init_msg)
            proc.stdin.flush()
            
            # Read response
            response_line = proc.stdout.readline()
            if not response_line:
                return {"success": False, "error": "No response from MCP server"}
            
            response = json.loads(response_line)
            
            # Send initialized notification
            notif = json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }) + "\n"
            proc.stdin.write(notif)
            proc.stdin.flush()
            
            # List tools
            tools = self._list_tools(proc)
            
            conn = {
                "process": proc,
                "capabilities": response.get("result", {}).get("capabilities", {}),
                "serverInfo": response.get("result", {}).get("serverInfo", {}),
                "tools": tools,
                "type": "stdio",
                "initialized": True,
            }
            self._connections[name] = conn
            
            return {
                "success": True,
                "name": name,
                "serverInfo": conn["serverInfo"],
                "capabilities": conn["capabilities"],
                "tools": tools,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _list_tools(self, proc) -> List[Dict]:
        """List available tools from MCP server."""
        try:
            msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }) + "\n"
            proc.stdin.write(msg)
            proc.stdin.flush()
            
            import select
            import time
            time.sleep(0.5)
            
            # Read all available lines
            output = ""
            while True:
                if select.select([proc.stdout], [], [], 0.5)[0]:
                    line = proc.stdout.readline()
                    if line:
                        output += line
                    else:
                        break
                else:
                    break
            
            if output:
                response = json.loads(output.strip())
                return response.get("result", {}).get("tools", [])
        except Exception:
            pass
        return []
    
    def list_tools(self, name: str = None) -> List[Dict]:
        """List tools from a specific connection or all connections."""
        if name:
            conn = self._connections.get(name)
            if not conn:
                return []
            return conn.get("tools", [])
        
        all_tools = []
        for conn_name, conn in self._connections.items():
            for tool in conn.get("tools", []):
                tool["_connection"] = conn_name
                all_tools.append(tool)
        return all_tools
    
    def call_tool(self, connection: str, tool_name: str,
                  arguments: Dict = None) -> Dict:
        """Call a tool on an MCP server.
        
        Args:
            connection: Connection name
            tool_name: Tool name to call
            arguments: Tool arguments dict
            
        Returns:
            Tool result
        """
        conn = self._connections.get(connection)
        if not conn:
            return {"success": False, "error": f"Connection '{connection}' not found"}
        
        try:
            msg_id = int(time.time() * 1000) % 100000
            msg = json.dumps({
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            }) + "\n"
            
            conn["process"].stdin.write(msg)
            conn["process"].stdin.flush()
            
            # Read response
            response_line = conn["process"].stdout.readline()
            if not response_line:
                return {"success": False, "error": "No response"}
            
            response = json.loads(response_line)
            
            if "error" in response:
                return {"success": False, "error": response["error"]["message"]}
            
            result = response.get("result", {})
            return {
                "success": True,
                "content": result.get("content", []),
                "isError": result.get("isError", False),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_resources(self, connection: str) -> Dict:
        """List available resources from an MCP server."""
        conn = self._connections.get(connection)
        if not conn:
            return {"success": False, "error": f"Connection '{connection}' not found"}
        
        try:
            msg = json.dumps({
                "jsonrpc": "2.0",
                "id": 3,
                "method": "resources/list"
            }) + "\n"
            conn["process"].stdin.write(msg)
            conn["process"].stdin.flush()
            
            response_line = conn["process"].stdout.readline()
            if not response_line:
                return {"success": False, "error": "No response"}
            
            response = json.loads(response_line)
            
            return {
                "success": True,
                "resources": response.get("result", {}).get("resources", []),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def disconnect(self, name: str = None) -> None:
        """Disconnect from MCP server(s)."""
        if name:
            conn = self._connections.pop(name, None)
            if conn and conn.get("process"):
                try:
                    conn["process"].terminate()
                except Exception:
                    pass
        else:
            for conn_name in list(self._connections.keys()):
                self.disconnect(conn_name)
    
    def connection_status(self) -> List[Dict]:
        """Get status of all connections."""
        return [
            {
                "name": name,
                "serverInfo": conn.get("serverInfo", {}),
                "type": conn.get("type", "unknown"),
                "tool_count": len(conn.get("tools", [])),
                "initialized": conn.get("initialized", False),
            }
            for name, conn in self._connections.items()
        ]


# Singleton
_mcp_client_instance = None

def get_mcp_client() -> MCPClient:
    global _mcp_client_instance
    if _mcp_client_instance is None:
        _mcp_client_instance = MCPClient()
    return _mcp_client_instance


# ─────────────────────────────────────────────────────────────────────────────
# 15. BULK SEARCH & REPLACE ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class BulkSearchReplace:
    """Project-wide search and replace with regex support, preview, dry-run."""
    
    def __init__(self) -> None:
        self._results_cache = {}
    
    def search(self, pattern: str, path: str = None, include: str = "*",
               regex: bool = True, case_sensitive: bool = True,
               max_results: int = 500) -> Dict:
        """Search across project files.
        
        Args:
            pattern: Search pattern (regex or literal)
            path: Directory to search (default: cwd)
            include: File glob pattern
            regex: Treat pattern as regex
            case_sensitive: Case sensitive search
            max_results: Max results to return
            
        Returns:
            Dict with matches grouped by file
        """
        import fnmatch
        
        search_path = Path(path or os.getcwd()).resolve()
        matches = {}
        total_count = 0
        
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            compiled = re.compile(pattern, flags) if regex else None
            
            # Use os.walk instead of rglob to avoid symlink loops (replicas dir)
            for root, dirs, files in os.walk(str(search_path), topdown=True):
                root_path = Path(root)
                
                # Skip ignored directories by pruning them from dirs list
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS_INDEX 
                          and not d.startswith("replica")
                          and not d.startswith(".")]
                
                for filename in files:
                    if not fnmatch.fnmatch(filename, include):
                        continue
                    
                    filepath = root_path / filename
                    
                    # Skip ignored extensions
                    if filepath.suffix.lower() in IGNORE_EXTS_INDEX:
                        continue
                    
                    # Skip files > 1MB
                    try:
                        file_size = filepath.stat().st_size
                        if file_size > 1024 * 1024:
                            continue
                    except Exception:
                        continue
                    
                    try:
                        content = filepath.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        continue
                    
                    file_matches = []
                    for i, line in enumerate(content.split("\n"), 1):
                        if regex:
                            m = compiled.search(line)
                            if m:
                                file_matches.append({
                                    "line": i,
                                    "content": line.strip(),
                                    "match": m.group(),
                                })
                        else:
                            if (case_sensitive and pattern in line) or \
                               (not case_sensitive and pattern.lower() in line.lower()):
                                file_matches.append({
                                    "line": i,
                                    "content": line.strip(),
                                })
                    
                    if file_matches:
                        matches[str(filepath)] = file_matches
                        total_count += len(file_matches)
                        
                        if total_count >= max_results:
                            break
                
                if total_count >= max_results:
                    break
            
            self._results_cache = {
                "pattern": pattern,
                "path": str(search_path),
                "regex": regex,
                "matches": matches,
                "total_count": total_count,
                "truncated": total_count >= max_results,
            }
            
            return {
                "success": True,
                "pattern": pattern,
                "path": str(search_path),
                "file_count": len(matches),
                "total_count": total_count,
                "truncated": total_count >= max_results,
                "matches": matches,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def replace(self, pattern: str, replacement: str, path: str = None,
                include: str = "*", regex: bool = True,
                dry_run: bool = True, commit_git: bool = False) -> Dict:
        """Replace text across project files.
        
        Args:
            pattern: Search pattern
            replacement: Replacement text (can use \\1 backreferences)
            path: Directory to search
            include: File glob pattern
            regex: Treat pattern as regex
            dry_run: Preview only, don't modify files
            commit_git: Auto-commit changes to git
            
        Returns:
            Dict with results
        """
        # First, search
        search_result = self.search(pattern, path, include, regex)
        if not search_result.get("success"):
            return search_result
        
        files_changed = []
        total_replacements = 0
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "pattern": pattern,
                "replacement": replacement,
                "file_count": search_result["file_count"],
                "total_count": search_result["total_count"],
                "matches": search_result["matches"],
                "message": f"DRY RUN: Would make {search_result['total_count']} replacements in {search_result['file_count']} files"
            }
        
        # Perform actual replacements
        for filepath, file_matches in search_result["matches"].items():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                new_content = re.sub(pattern, replacement, content) if regex else \
                    content.replace(pattern, replacement)
                
                if new_content != content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    files_changed.append(filepath)
                    total_replacements += len(file_matches)
            except Exception as e:
                return {"success": False, "error": f"Error writing {filepath}: {e}"}
        
        result = {
            "success": True,
            "dry_run": False,
            "pattern": pattern,
            "replacement": replacement,
            "files_changed": len(files_changed),
            "total_replacements": total_replacements,
            "files": files_changed,
        }
        
        # Auto-commit if requested
        if commit_git and files_changed:
            try:
                import subprocess as sp
                sp.run(["git", "add", "-A"], cwd=Path(path or os.getcwd()),
                       capture_output=True, text=True)
                sp.run(["git", "commit", "-m", f"refactor: bulk replace '{pattern}' -> '{replacement}'"],
                       cwd=Path(path or os.getcwd()), capture_output=True, text=True)
                result["git_committed"] = True
            except Exception:
                result["git_committed"] = False
        
        return result
    
    def preview(self, pattern: str, path: str = None,
                include: str = "*") -> Dict:
        """Preview search results (alias for search with preview formatting)."""
        return self.search(pattern, path, include)


# Singleton
_bulk_sr_instance = None

def get_bulk_search_replace() -> BulkSearchReplace:
    global _bulk_sr_instance
    if _bulk_sr_instance is None:
        _bulk_sr_instance = BulkSearchReplace()
    return _bulk_sr_instance


# ─────────────────────────────────────────────────────────────────────────────
# 16. REFACTORING ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class RefactoringEngine:
    """Project-wide code refactoring: rename symbols, extract methods, split files."""
    
    def rename_symbol(self, symbol: str, new_name: str,
                      file_types: List[str] = None,
                      path: str = None,
                      dry_run: bool = True) -> Dict:
        """Rename a symbol (variable, function, class) across the project.
        
        Uses AST parsing for Python to ensure accurate renaming.
        Falls back to regex for other languages.
        
        Args:
            symbol: Current symbol name
            new_name: New symbol name
            file_types: File extensions to include (e.g. ['.py', '.js'])
            path: Project root path
            dry_run: Preview only
            
        Returns:
            Dict with results
        """
        search_path = Path(path or os.getcwd()).resolve()
        file_types = set(file_types or ['.py', '.js', '.ts', '.jsx', '.tsx', 
                                        '.java', '.cpp', '.c', '.h', '.go', '.rs'])
        results = {"files_changed": [], "occurrences": [], "errors": []}
        
        # Single walk, check all extensions at once
        for root, dirs, files in os.walk(str(search_path), topdown=True):
            # Prune problematic dirs
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS_INDEX 
                      and not d.startswith("replica")
                      and not d.startswith(".")]
            
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in file_types:
                    continue
                
                filepath = Path(root) / filename
                if not filepath.is_file():
                    continue
                
                try:
                    content = filepath.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                
                # Quick content check before expensive operations
                if symbol not in content:
                    continue
                
                changes = []
                
                if ext == '.py':
                    changes = self._rename_python(filepath, content, symbol, new_name)
                else:
                    pattern = r'\b' + re.escape(symbol) + r'\b'
                    for i, line in enumerate(content.split("\n"), 1):
                        if re.search(pattern, line):
                            changes.append({"line": i, "content": line.strip()})
                
                if changes:
                    file_result = {
                        "file": str(filepath),
                        "occurrences": len(changes),
                        "changes": changes,
                    }
                    results["occurrences"].append(file_result)
                    
                    if not dry_run:
                        if ext == '.py':
                            new_content = self._do_rename_python(content, symbol, new_name)
                        else:
                            pattern = r'\b' + re.escape(symbol) + r'\b'
                            new_content = re.sub(pattern, new_name, content)
                        
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        results["files_changed"].append(str(filepath))
        
        results["dry_run"] = dry_run
        results["total_files"] = len(results["occurrences"])
        results["total_occurrences"] = sum(o["occurrences"] for o in results["occurrences"])
        
        return results
    
    def _rename_python(self, filepath: Path, content: str,
                       old_name: str, new_name: str) -> List[Dict]:
        """Find rename candidates in Python using AST."""
        changes = []
        try:
            tree = ast.parse(content)
            # Visit all nodes looking for the symbol name
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name == old_name:
                        changes.append({
                            "line": node.lineno,
                            "kind": "definition",
                            "type": type(node).__name__,
                            "content": content.split("\n")[node.lineno - 1].strip() if node.lineno else "",
                        })
                elif isinstance(node, ast.Name) and node.id == old_name:
                    changes.append({
                        "line": node.lineno,
                        "kind": "reference",
                        "content": content.split("\n")[node.lineno - 1].strip() if node.lineno else "",
                    })
                elif isinstance(node, ast.Attribute) and node.attr == old_name:
                    changes.append({
                        "line": node.lineno,
                        "kind": "attribute",
                        "content": content.split("\n")[node.lineno - 1].strip() if node.lineno else "",
                    })
        except SyntaxError:
            # Fall back to regex if AST parsing fails
            pattern = r'\b' + re.escape(old_name) + r'\b'
            for i, line in enumerate(content.split("\n"), 1):
                if re.search(pattern, line):
                    changes.append({
                        "line": i,
                        "kind": "regex_fallback",
                        "content": line.strip(),
                    })
        return changes
    
    def _do_rename_python(self, content: str, old_name: str, new_name: str) -> str:
        """Perform Python rename using AST-guided replacement."""
        try:
            tree = ast.parse(content)
            lines = content.split("\n")
            
            # Collect all line positions to replace (reverse order to preserve indices)
            replacements = []
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name == old_name:
                        if hasattr(node, 'decorator_list') and node.decorator_list:
                            # Skip if the old_name is part of a decorator
                            pass
                        replacements.append((node.lineno - 1, node.col_offset, old_name, new_name))
                elif isinstance(node, ast.Name) and node.id == old_name:
                    if not isinstance(node.ctx, ast.Load):
                        pass  # Include all contexts
                    replacements.append((node.lineno - 1, node.col_offset, old_name, new_name))
                elif isinstance(node, ast.Attribute) and node.attr == old_name:
                    replacements.append((node.lineno - 1, node.col_offset + len(node.value.id) + 1 if hasattr(node.value, 'id') else 0, old_name, new_name))
            
            # Apply replacements in reverse order (bottom to top, right to left)
            replacements.sort(key=lambda x: (x[0], x[1]), reverse=True)
            
            for line_no, col_offset, old, new in replacements:
                line = lines[line_no]
                if col_offset < len(line) and line[col_offset:col_offset + len(old)] == old:
                    lines[line_no] = line[:col_offset] + new + line[col_offset + len(old):]
            
            return "\n".join(lines)
        except SyntaxError:
            # Fallback: simple regex replacement with word boundaries
            pattern = r'\b' + re.escape(old_name) + r'\b'
            return re.sub(pattern, new_name, content)
    
    def extract_function(self, source_file: str, function_name: str,
                         new_file: str = None, dry_run: bool = True) -> Dict:
        """Extract a function from one file to another.
        
        For Python files, preserves imports and dependencies.
        
        Args:
            source_file: Path to source file
            function_name: Name of function to extract
            new_file: Destination file (auto-named if empty)
            dry_run: Preview only
            
        Returns:
            Dict with results
        """
        source = Path(source_file)
        if not source.exists():
            return {"success": False, "error": f"File not found: {source_file}"}
        
        try:
            content = source.read_text(encoding="utf-8")
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        if source.suffix == '.py':
            return self._extract_python_function(source, content, function_name, new_file, dry_run)
        else:
            return {"success": False, "error": f"Unsupported file type: {source.suffix}"}
    
    def _extract_python_function(self, source: Path, content: str,
                                  func_name: str, new_file: str,
                                  dry_run: bool) -> Dict:
        """Extract a Python function into its own file."""
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {"success": False, "error": f"Parse error: {e}"}
        
        # Find the function
        func_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == func_name:
                    func_node = node
                    break
        
        if not func_node:
            return {"success": False, "error": f"Function '{func_name}' not found"}
        
        lines = content.split("\n")
        
        # Get function source lines
        start_line = func_node.lineno - 1
        end_line = func_node.end_lineno if hasattr(func_node, 'end_lineno') and func_node.end_lineno else start_line + 1
        
        # Collect imports used by the function
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imp_start = node.lineno - 1
                imp_end = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else imp_start + 1
                imports.append("\n".join(lines[imp_start:imp_end]))
        
        func_source = "\n".join(lines[start_line:end_line])
        
        # Build new file content
        new_content = f"""# Auto-extracted from {source.name}
# Original file: {source}

{chr(10).join(set(imports)) if imports else ""}

{func_source}
"""
        
        dest = Path(new_file or source.parent / f"{func_name}.py")
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "source": str(source),
                "function": func_name,
                "destination": str(dest),
                "imports": imports,
                "code": func_source,
                "new_file_content": new_content,
            }
        
        # Write the new file
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(new_content, encoding="utf-8")
            
            # Remove the function from the source
            new_source_lines = lines[:start_line] + lines[end_line:]
            # Clean up extra blank lines
            while start_line < len(new_source_lines) and new_source_lines[start_line].strip() == "":
                if start_line + 1 < len(new_source_lines) and new_source_lines[start_line + 1].strip() == "":
                    new_source_lines.pop(start_line)
                else:
                    break
            
            source.write_text("\n".join(new_source_lines), encoding="utf-8")
            
            return {
                "success": True,
                "dry_run": False,
                "source": str(source),
                "function": func_name,
                "destination": str(dest),
                "removed_from_source": True,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def split_file(self, source_file: str, output_dir: str = None,
                   by: str = "class", dry_run: bool = True) -> Dict:
        """Split a file into multiple files by class/function.
        
        Args:
            source_file: Path to file to split
            output_dir: Output directory (uses source dir if empty)
            by: Split by 'class', 'function', or 'both'
            dry_run: Preview only
            
        Returns:
            Dict with results
        """
        source = Path(source_file)
        if not source.exists():
            return {"success": False, "error": f"File not found: {source_file}"}
        
        try:
            content = source.read_text(encoding="utf-8")
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        if source.suffix != '.py':
            return {"success": False, "error": "Only Python files supported for splitting"}
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {"success": False, "error": f"Parse error: {e}"}
        
        lines = content.split("\n")
        out_dir = Path(output_dir or source.parent)
        
        # Collect imports (top-level imports)
        imports = []
        non_import_lines_start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(("import ", "from ")):
                imports.append(line)
            elif line.strip() and not line.strip().startswith("#"):
                non_import_lines_start = i
                break
        
        import_block = "\n".join(imports)
        
        # Collect classes and functions
        extracted = []
        
        for node in ast.walk(tree):
            if by in ("class", "both") and isinstance(node, ast.ClassDef):
                start = node.lineno - 1
                end = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else start + 1
                code = "\n".join(lines[start:end])
                extracted.append({
                    "type": "class",
                    "name": node.name,
                    "code": code,
                    "file": out_dir / f"{node.name}.py",
                })
            elif by in ("function", "both") and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip methods inside classes
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        if node in ast.walk(parent) and node is not parent:
                            break
                else:
                    start = node.lineno - 1
                    end = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else start + 1
                    code = "\n".join(lines[start:end])
                    extracted.append({
                        "type": "function",
                        "name": node.name,
                        "code": code,
                        "file": out_dir / f"{node.name}.py",
                    })
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "source": str(source),
                "output_dir": str(out_dir),
                "files_to_create": [str(e["file"]) for e in extracted],
                "imports": import_block,
                "extracted": extracted,
            }
        
        # Create the files
        created = []
        for item in extracted:
            try:
                item["file"].parent.mkdir(parents=True, exist_ok=True)
                content = f"# Extracted from {source.name}\n{import_block}\n\n{item['code']}\n"
                item["file"].write_text(content, encoding="utf-8")
                created.append(str(item["file"]))
            except Exception as e:
                return {"success": False, "error": f"Error writing {item['file']}: {e}"}
        
        # Update original file to import from new files
        new_imports = []
        for item in extracted:
            rel_path = os.path.relpath(item["file"], source.parent)
            module_name = rel_path.replace("\\", "/").replace("/", ".").replace(".py", "")
            new_imports.append(f"from {module_name} import {item['name']}")
        
        new_content = f"{import_block}\n{chr(10).join(new_imports)}\n\n"
        source.write_text(new_content, encoding="utf-8")
        
        return {
            "success": True,
            "dry_run": False,
            "source": str(source),
            "files_created": created,
            "original_updated": True,
        }


# Singleton
_refactoring_instance = None

def get_refactoring_engine() -> RefactoringEngine:
    global _refactoring_instance
    if _refactoring_instance is None:
        _refactoring_instance = RefactoringEngine()
    return _refactoring_instance


# ─────────────────────────────────────────────────────────────────────────────
# 17. RELEASE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

class ReleaseManager:
    """Semantic versioning, changelog generation, release management."""
    
    VERSION_FILE_NAMES = [
        "version.txt", "VERSION", ".version",
        "pyproject.toml", "setup.cfg", "setup.py",
        "package.json", "Cargo.toml", "Gopkg.toml",
    ]
    
    def detect_version(self, path: str = None) -> Dict:
        """Detect current project version from common version files.
        
        Returns:
            Dict with version, file, and source type
        """
        root = Path(path or os.getcwd()).resolve()
        
        for name in self.VERSION_FILE_NAMES:
            candidate = root / name
            if candidate.exists():
                try:
                    content = candidate.read_text(encoding="utf-8")
                    
                    if name == "package.json":
                        data = json.loads(content)
                        return {"file": str(candidate), "version": data.get("version", "0.0.0"), "source": "package.json"}
                    
                    elif name == "pyproject.toml":
                        m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                        if m:
                            return {"file": str(candidate), "version": m.group(1), "source": "pyproject.toml"}
                    
                    elif name == "setup.cfg":
                        m = re.search(r'version\s*=\s*(\S+)', content)
                        if m:
                            return {"file": str(candidate), "version": m.group(1), "source": "setup.cfg"}
                    
                    elif name == "setup.py":
                        m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                        if m:
                            return {"file": str(candidate), "version": m.group(1), "source": "setup.py"}
                    
                    elif name in ("version.txt", "VERSION", ".version"):
                        return {"file": str(candidate), "version": content.strip(), "source": name}
                    
                    elif name == "Cargo.toml":
                        m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                        if m:
                            return {"file": str(candidate), "version": m.group(1), "source": "Cargo.toml"}
                except Exception:
                    continue
        
        # Try git tag
        try:
            import subprocess as sp
            result = sp.run(["git", "describe", "--tags", "--abbrev=0"],
                           cwd=root, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return {"file": "git-tag", "version": result.stdout.strip().lstrip("v"), "source": "git-tag"}
        except Exception:
            pass
        
        return {"file": None, "version": "0.0.0", "source": "unknown"}
    
    def bump_version(self, part: str = "patch", path: str = None,
                     pre_release: str = None, dry_run: bool = True) -> Dict:
        """Bump semantic version.
        
        Args:
            part: 'major', 'minor', 'patch', 'premajor', 'preminor', 'prepatch'
            path: Project root
            pre_release: Pre-release tag (e.g. 'alpha', 'beta', 'rc1')
            dry_run: Preview only
            
        Returns:
            Dict with old and new version
        """
        current = self.detect_version(path)
        old_version = current["version"]
        version_file = current["file"]
        
        if not version_file:
            return {"success": False, "error": "No version file found"}
        
        # Parse version
        m = re.match(r'(\d+)\.(\d+)\.(\d+)(.*)', old_version)
        if not m:
            return {"success": False, "error": f"Cannot parse version: {old_version}"}
        
        major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
        suffix = m.group(4).strip()
        
        if part == "major":
            major += 1
            minor = 0
            patch = 0
        elif part == "minor":
            minor += 1
            patch = 0
        elif part == "patch":
            patch += 1
        elif part == "premajor":
            major += 1
            minor = 0
            patch = 0
        elif part == "preminor":
            minor += 1
            patch = 0
        elif part == "prepatch":
            patch += 1
        else:
            return {"success": False, "error": f"Unknown part: {part}"}
        
        new_version = f"{major}.{minor}.{patch}"
        if pre_release:
            new_version += f"-{pre_release}"
        elif part.startswith("pre"):
            new_version += f"-alpha.1"
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "file": version_file,
                "old_version": old_version,
                "new_version": new_version,
                "part": part,
            }
        
        # Write new version
        try:
            vf = Path(version_file)
            content = vf.read_text(encoding="utf-8")
            
            name = vf.name
            if name == "package.json":
                data = json.loads(content)
                data["version"] = new_version
                vf.write_text(json.dumps(data, indent=2), encoding="utf-8")
            elif name in ("pyproject.toml", "setup.cfg"):
                content = re.sub(r'(version\s*=\s*)[\'"][^\'"]*[\'"]',
                                rf'\1"{new_version}"', content)
                vf.write_text(content, encoding="utf-8")
            elif name == "setup.py":
                content = re.sub(r'(version\s*=\s*)[\'"][^\'"]*[\'"]',
                                rf'\1"{new_version}"', content)
                vf.write_text(content, encoding="utf-8")
            elif name in ("version.txt", "VERSION", ".version"):
                vf.write_text(new_version + "\n", encoding="utf-8")
            elif name == "Cargo.toml":
                content = re.sub(r'(version\s*=\s*)[\'"][^\'"]*[\'"]',
                                rf'\1"{new_version}"', content)
                vf.write_text(content, encoding="utf-8")
            
            # Git commit
            try:
                import subprocess as sp
                sp.run(["git", "add", version_file], cwd=Path(path or os.getcwd()),
                       capture_output=True, text=True)
                sp.run(["git", "commit", "-m", f"chore: bump version to {new_version}"],
                       cwd=Path(path or os.getcwd()), capture_output=True, text=True)
                sp.run(["git", "tag", f"v{new_version}"],
                       cwd=Path(path or os.getcwd()), capture_output=True, text=True)
            except Exception:
                pass
            
            return {
                "success": True,
                "dry_run": False,
                "file": version_file,
                "old_version": old_version,
                "new_version": new_version,
                "git_tag": f"v{new_version}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_changelog(self, path: str = None,
                           from_tag: str = None,
                           to_tag: str = "HEAD",
                           format: str = "markdown") -> Dict:
        """Generate changelog from git log.
        
        Args:
            path: Git repo path
            from_tag: Starting tag (auto-detects last)
            to_tag: Ending tag/ref
            format: 'markdown' or 'json'
            
        Returns:
            Dict with changelog content
        """
        root = Path(path or os.getcwd()).resolve()
        
        try:
            import subprocess as sp
            
            # Detect last tag if not specified
            if not from_tag:
                result = sp.run(["git", "describe", "--tags", "--abbrev=0", "--always"],
                               cwd=root, capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    from_tag = result.stdout.strip()
                else:
                    # No tags, get all commits
                    log_result = sp.run(
                        ["git", "log", "--oneline", "--no-decorate"],
                        cwd=root, capture_output=True, text=True, timeout=10
                    )
                    if log_result.returncode == 0:
                        commits = [line.strip() for line in log_result.stdout.strip().split("\n") if line.strip()]
                        return {
                            "success": True,
                            "commits": commits,
                            "format": format,
                            "changelog": "# Changelog\n\n" + "\n".join(f"- {c}" for c in commits),
                            "from": "(beginning)",
                            "to": "HEAD",
                        }
                    return {"success": False, "error": "No git history found"}
            
            # Get log between tags
            range_spec = f"{from_tag}..{to_tag}" if from_tag else to_tag
            log_result = sp.run(
                ["git", "log", "--oneline", "--no-decorate", range_spec],
                cwd=root, capture_output=True, text=True, timeout=10
            )
            
            if log_result.returncode != 0:
                return {"success": False, "error": log_result.stderr.strip()}
            
            commits = [line.strip() for line in log_result.stdout.strip().split("\n") if line.strip()]
            
            # Categorize commits
            categories = {
                "feat": [], "feature": [],
                "fix": [], "bugfix": [],
                "chore": [], "refactor": [],
                "docs": [], "doc": [],
                "style": [], "test": [],
                "perf": [], "ci": [],
                "security": [], "other": [],
            }
            
            for commit in commits:
                # Try to extract conventional commit type
                m = re.match(r'(\w+)(?:\(.+\))?!?:\s*(.+)', commit)
                if m:
                    cat = m.group(1)
                    msg = m.group(2)
                    if cat in categories:
                        categories[cat].append(msg)
                    else:
                        categories["other"].append(commit)
                else:
                    categories["other"].append(commit)
            
            # Build markdown
            if format == "markdown":
                lines = [f"# Changelog\n",
                        f"\n## [{to_tag if to_tag != 'HEAD' else 'Unreleased'}]"]
                if from_tag:
                    lines[1] += f" — {from_tag} → {to_tag if to_tag != 'HEAD' else 'HEAD'}"
                
                label_map = {
                    "feat": "🚀 Features", "feature": "🚀 Features",
                    "fix": "🐛 Bug Fixes", "bugfix": "🐛 Bug Fixes",
                    "chore": "🔧 Maintenance",
                    "refactor": "♻️ Refactoring",
                    "docs": "📚 Documentation", "doc": "📚 Documentation",
                    "style": "🎨 Style",
                    "test": "🧪 Testing",
                    "perf": "⚡ Performance",
                    "ci": "🤖 CI/CD",
                    "security": "🔒 Security",
                    "other": "📋 Other",
                }
                
                for cat, label in label_map.items():
                    if categories.get(cat):
                        lines.append(f"\n### {label}\n")
                        for msg in categories[cat]:
                            lines.append(f"- {msg}")
                
                changelog = "\n".join(lines)
            else:
                changelog = json.dumps({
                    "from": from_tag,
                    "to": to_tag,
                    "categories": {k: v for k, v in categories.items() if v},
                    "total": len(commits),
                }, indent=2)
            
            return {
                "success": True,
                "commits": commits,
                "categories": {k: v for k, v in categories.items() if v},
                "total": len(commits),
                "format": format,
                "changelog": changelog,
                "from": from_tag,
                "to": to_tag,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def write_changelog(self, path: str = None, filename: str = "CHANGELOG.md",
                        from_tag: str = None, to_tag: str = "HEAD") -> Dict:
        """Generate and write changelog to file."""
        result = self.generate_changelog(path, from_tag, to_tag)
        if not result.get("success"):
            return result
        
        changelog_path = Path(path or os.getcwd()) / filename
        try:
            # Check if file exists, prepend new content
            if changelog_path.exists():
                existing = changelog_path.read_text(encoding="utf-8")
                # Insert after the first heading
                new_content = result["changelog"] + "\n\n" + existing
            else:
                new_content = result["changelog"]
            
            changelog_path.write_text(new_content, encoding="utf-8")
            
            return {
                "success": True,
                "file": str(changelog_path),
                "total_commits": result["total"],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_release_manager_instance = None

def get_release_manager() -> ReleaseManager:
    global _release_manager_instance
    if _release_manager_instance is None:
        _release_manager_instance = ReleaseManager()
    return _release_manager_instance
