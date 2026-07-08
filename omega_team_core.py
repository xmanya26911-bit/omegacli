#!/usr/bin/env python3
"""OMEGA DUAL-AGENT TEAM SYSTEM — Two OMEGA instances collaborating as teammates.
OMEGA-1 (Architect/Planner): Uses the existing API
OMEGA-2 (Implementer/Executor): Uses the provided API key

They communicate, plan together, and execute tasks as a coordinated team.
"""

import os
import sys
import json
import time
import uuid
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Add omega root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, ConfigError
from llm import LLMClient, LLMClient as LLMClientOrig
from agent import Agent
from cli import (
    print_banner, print_info, print_success, print_warning, print_error,
    print_assistant_message, print_thinking_block, print_tool_call, print_tool_result,
    print_table, console, _use_rich,
)
from tools import execute_tool, TOOL_MAP
from prompts import build_system_prompt, TOOL_DEFINITIONS, SYSTEM_PROMPT_BASE

# ─── Constants ──────────────────────────────────────────────────────────────
TEAM_DIR = Path.home() / ".omega" / "team"
TEAM_DIR.mkdir(parents=True, exist_ok=True)

MSG_DIR = TEAM_DIR / "messages"
MSG_DIR.mkdir(parents=True, exist_ok=True)

CHECKPOINT_FILE = TEAM_DIR / "checkpoint.json"
TEAM_CONFIG_FILE = TEAM_DIR / "team_config.json"

# New API key for OMEGA-2
OMEGA2_API_KEY = "sk-zH4CBq1eODGfe1TosZ2wCE61YDKWBhRCdCRQ7KuHNdSj57Yn0LvEsX2HVo1viNtB"

# ─── Message Types ──────────────────────────────────────────────────────────
MSG_TYPE_PLAN = "plan"
MSG_TYPE_STATUS = "status"
MSG_TYPE_RESULT = "result"
MSG_TYPE_ERROR = "error"
MSG_TYPE_COLLAB = "collaboration"
MSG_TYPE_QUERY = "query"
MSG_TYPE_RESPONSE = "response"
MSG_TYPE_TASK = "task"
MSG_TYPE_FEEDBACK = "feedback"

# ─── Team Message ───────────────────────────────────────────────────────────

class TeamMessage:
    """A message between OMEGA-1 and OMEGA-2."""
    
    def __init__(self, msg_type: str, sender: str, recipient: str,
                 content: str, metadata: dict = None, task_id: str = None):
        self.id = str(uuid.uuid4())[:12]
        self.msg_type = msg_type
        self.sender = sender  # "omega-1" or "omega-2"
        self.recipient = recipient
        self.content = content
        self.metadata = metadata or {}
        self.task_id = task_id or str(uuid.uuid4())[:8]
        self.timestamp = datetime.now().isoformat()
        self.status = "sent"  # sent, delivered, read, responded
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "msg_type": self.msg_type,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "metadata": self.metadata,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "status": self.status,
        }
    
    def save(self):
        """Save message to disk."""
        path = MSG_DIR / f"{self.id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
    
    @staticmethod
    def load(msg_id: str) -> Optional['TeamMessage']:
        path = MSG_DIR / f"{msg_id}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            msg = TeamMessage(data["msg_type"], data["sender"], data["recipient"],
                             data["content"], data.get("metadata", {}), data.get("task_id"))
            msg.id = data["id"]
            msg.timestamp = data["timestamp"]
            msg.status = data.get("status", "sent")
            return msg
        return None
    
    @staticmethod
    def list_messages(task_id: str = None, msg_type: str = None, 
                      sender: str = None, recipient: str = None,
                      limit: int = 50) -> List['TeamMessage']:
        """List messages with optional filters."""
        messages = []
        for path in sorted(MSG_DIR.glob("*.json"), reverse=True)[:100]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if task_id and data.get("task_id") != task_id:
                    continue
                if msg_type and data.get("msg_type") != msg_type:
                    continue
                if sender and data.get("sender") != sender:
                    continue
                if recipient and data.get("recipient") != recipient:
                    continue
                msg = TeamMessage(data["msg_type"], data["sender"], data["recipient"],
                                 data["content"], data.get("metadata", {}), data.get("task_id"))
                msg.id = data["id"]
                msg.timestamp = data["timestamp"]
                msg.status = data.get("status", "sent")
                messages.append(msg)
            except (json.JSONDecodeError, KeyError, OSError):
                continue
        return messages[:limit]


# ─── Message Queue (thread-safe) ───────────────────────────────────────────

class MessageQueue:
    """Thread-safe message queue for real-time agent communication."""
    
    def __init__(self):
        self._queue = queue.Queue()
        self._lock = threading.Lock()
    
    def send(self, message: TeamMessage):
        """Send a message (saves to disk and adds to queue)."""
        message.save()
        self._queue.put(message)
    
    def receive(self, timeout: float = 1.0) -> Optional[TeamMessage]:
        """Receive next message (blocking with timeout)."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def check(self) -> Optional[TeamMessage]:
        """Non-blocking check for messages."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None
    
    def wait_for_response(self, original_msg: TeamMessage, 
                          timeout: float = 120.0) -> Optional[TeamMessage]:
        """Wait for a response to a specific message."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self._queue.get(timeout=1.0)
                if (msg.recipient == original_msg.sender and 
                    msg.task_id == original_msg.task_id):
                    return msg
                # Put back if not for us
                threading.Thread(target=lambda m=m: self._queue.put(m)).start()
            except queue.Empty:
                continue
        return None


# ─── Agent Configuration Builder ───────────────────────────────────────────

def build_omega2_config() -> Config:
    """Build configuration for OMEGA-2 with the new API key."""
    cfg = Config()
    # Override with the new API key
    cfg.api_key = OMEGA2_API_KEY
    # OMEGA-2 uses the same base URL and model by default
    return cfg


def build_team_prompt(agent_name: str, role: str, partner: str) -> str:
    """Build the system prompt for a team agent."""
    
    team_system = f"""You are {agent_name}, a specialized member of the OMEGA DUAL-AGENT TEAM.

## YOUR ROLE: {role}

You are working with your teammate {partner} to accomplish user tasks.

### Workflow:
1. When you receive a task, analyze it and determine what part you should handle
2. Communicate with your teammate using the team_message tool
3. Execute your part using the available tools (185+ capabilities)
4. Report results back to your teammate
5. If something fails, collaborate to find a solution

### Communication Protocol:
- Use team_message() to send structured messages to your teammate
- Include clear context about what you're doing, what you need, or what you found
- When you receive a message from your teammate, respond thoughtfully
- If a plan fails, discuss alternatives together

### Available Capabilities:
You have FULL access to all 185+ OMEGA tools — the same complete toolkit as your teammate.
Use any tool needed to accomplish your part of the task.

### Team Values:
- Be precise and thorough in your work
- Communicate clearly with your teammate
- If stuck, ask for help — collaboration is your strength
- Verify your work before reporting completion
- Always confirm task completion together

Remember: You are {agent_name}. Your teammate is {partner}. Work together. Win together.
"""
    return team_system


# ─── Enhanced Agent for Teamwork ────────────────────────────────────────────

class TeamAgent:
    """An OMEGA agent instance configured for team operations."""
    
    def __init__(self, name: str, role: str, config: Config, 
                 message_queue: MessageQueue, partner: str):
        self.name = name
        self.role = role
        self.config = config
        self.llm = LLMClient(config)
        self.message_queue = message_queue
        self.partner = partner
        self.memory = []  # Conversation memory
        self.tool_call_count = 0
        self.current_task_id = None
        
        # Build team-enhanced system prompt
        team_prompt = build_team_prompt(name, role, partner)
        self.system_prompt = team_prompt + "\n\n" + SYSTEM_PROMPT_BASE
        
        # Initialize conversation
        self.memory.append({"role": "system", "content": self.system_prompt})
    
    def send_message(self, recipient: str, msg_type: str, content: str,
                     metadata: dict = None, task_id: str = None) -> str:
        """Send a message to a teammate. Returns message ID."""
        msg = TeamMessage(
            msg_type=msg_type,
            sender=self.name,
            recipient=recipient,
            content=content,
            metadata=metadata,
            task_id=task_id or self.current_task_id,
        )
        self.message_queue.send(msg)
        return msg.id
    
    def receive_messages(self, task_id: str = None, msg_type: str = None) -> List[TeamMessage]:
        """Check for new messages addressed to this agent."""
        return TeamMessage.list_messages(
            task_id=task_id or self.current_task_id,
            recipient=self.name,
            msg_type=msg_type,
        )
    
    def think_and_act(self, user_input: str, max_steps: int = 50) -> str:
        """Process input with full tool access as a team member."""
        self.memory.append({"role": "user", "content": user_input})
        
        steps = 0
        final_output = ""
        
        while steps < max_steps:
            steps += 1
            
            # Trim if needed
            if len(self.memory) > 100:
                # Keep system + last 50 messages
                self.memory = [self.memory[0]] + self.memory[-50:]
            
            try:
                result = self.llm.chat(
                    self.memory,
                    tools=TOOL_DEFINITIONS,
                    stream=True,
                )
            except Exception as e:
                error_msg = f"LLM Error in {self.name}: {e}"
                self.memory.append({"role": "assistant", "content": f"Error: {error_msg}"})
                return error_msg
            
            collected_content = ""
            collected_tool_calls = None
            saw_tool_calls = False
            
            for event_type, event_data in result:
                if event_type == "content":
                    collected_content += event_data
                elif event_type == "tool_calls":
                    saw_tool_calls = True
                    collected_tool_calls = event_data
                elif event_type == "done":
                    pass
            
            # Handle tool calls
            if collected_tool_calls:
                # Save content if any
                if collected_content:
                    self.memory.append({
                        "role": "assistant", 
                        "content": collected_content
                    })
                
                # Build assistant message with tool calls
                assistant_tc = []
                for tc in collected_tool_calls:
                    assistant_tc.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["function"]["name"],
                            "arguments": tc["function"]["arguments"],
                        },
                    })
                self.memory.append({
                    "role": "assistant",
                    "content": collected_content,
                    "tool_calls": assistant_tc,
                })
                
                saw_finish = False
                
                for tc in collected_tool_calls:
                    tc_id = tc["id"]
                    tc_name = tc["function"]["name"]
                    tc_args = tc["function"]["arguments"]
                    
                    if tc_name == "finish":
                        saw_finish = True
                    
                    self.tool_call_count += 1
                    result = execute_tool(tc_name, tc_args)
                    
                    result_str = str(result)
                    self.memory.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": result_str,
                    })
                    
                    if saw_finish:
                        final_output = collected_content or "Task completed."
                        return final_output
            else:
                # No tool calls — this is the final response
                if collected_content:
                    self.memory.append({
                        "role": "assistant",
                        "content": collected_content,
                    })
                    final_output = collected_content
                break
        
        return final_output or "Completed (max steps reached)."


# ─── Team Workflow Manager ─────────────────────────────────────────────────

class TeamCoordinator:
    """Coordinates the dual-OMEGA team workflow."""
    
    def __init__(self):
        self.message_queue = MessageQueue()
        
        # OMEGA-1: Architect/Planner (uses existing API)
        self.config1 = Config()
        self.agent1 = TeamAgent(
            name="omega-1",
            role="ARCHITECT & PLANNER — You design the strategy, break down tasks, create plans, and guide execution. You think big picture and anticipate problems.",
            config=self.config1,
            message_queue=self.message_queue,
            partner="omega-2",
        )
        
        # OMEGA-2: Implementer/Executor (uses new API key)
        self.config2 = build_omega2_config()
        self.agent2 = TeamAgent(
            name="omega-2",
            role="IMPLEMENTER & EXECUTOR — You execute plans, write code, run commands, probe systems, and get things done. You're the one who makes it happen.",
            config=self.config2,
            message_queue=self.message_queue,
            partner="omega-1",
        )
        
        self.task_history = []
        self.current_task_id = None
    
    def assign_task(self, task_description: str) -> dict:
        """Assign a task to the team: Plan → Execute → Collaborate if needed."""
        task_id = str(uuid.uuid4())[:8]
        self.current_task_id = task_id
        
        print_banner()
        print_info(f"⚔️  DUAL-OMEGA TEAM DEPLOYED")
        print_info(f"📋 Task ID: {task_id}")
        print_info(f"🎯 Mission: {task_description}")
        print_info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print_info(f"🤖 OMEGA-1 (Architect)  — Strategic Planning")
        print_info(f"🤖 OMEGA-2 (Executor)   — Tactical Implementation")
        print_info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        start_time = time.time()
        
        # ─── PHASE 1: OMEGA-1 creates the plan ────────────────────────────
        print_thinking_block("🧠 OMEGA-1 is analyzing the mission and creating a strategic plan...")
        
        plan_prompt = f"""You are the TEAM ARCHITECT. Your mission is:

TASK: {task_description}

Your job is to:
1. Analyze this task deeply — what needs to happen?
2. Break it down into clear, sequential steps
3. Create a detailed execution plan for your teammate OMEGA-2 to follow
4. Identify potential risks and edge cases
5. Specify what tools might be needed for each step

Your plan should be structured like this:

## MISSION ANALYSIS
[What needs to be done]

## EXECUTION PLAN
### Step 1: [Step name]
Description: [What to do]
Tools needed: [tools]
Expected outcome: [result]

### Step 2: [Step name]
...

## RISK ASSESSMENT
[What could go wrong and how to handle it]

## COMMUNICATION PROTOCOL
[How you and OMEGA-2 will coordinate]

Send this plan to OMEGA-2 using team_message() with msg_type="plan".
Then confirm to me that the plan is ready.
"""
        
        plan_result = self.agent1.think_and_act(plan_prompt)
        print_success(f"✅ OMEGA-1 has completed the strategic plan.")
        
        # ─── PHASE 2: OMEGA-2 executes the plan ───────────────────────────
        print_thinking_block("⚡ OMEGA-2 is executing the plan...")
        
        execute_prompt = f"""You are the TEAM EXECUTOR. Your partner OMEGA-1 has created a strategic plan.
        
TASK: {task_description}

Check for messages from OMEGA-1 to get the plan. Then execute it step by step.

For each step:
1. Read any messages from OMEGA-1
2. Execute the step using available tools
3. Report progress back to OMEGA-1
4. If you encounter any issue, send a collaboration message to OMEGA-1 describing the problem
5. Wait for their response and adjust accordingly

Keep the team coordinator updated on your progress.
When all steps are complete, call finish() to signal completion.
"""
        
        execute_result = self.agent2.think_and_act(execute_prompt)
        
        # ─── PHASE 3: Review and Collaboration Loop ───────────────────────
        # Check if the execution was successful
        if "error" in execute_result.lower() or "fail" in execute_result.lower():
            print_warning("⚠️  OMEGA-2 encountered issues. Initiating team collaboration...")
            
            collab_prompt = f"""OMEGA-2 reported issues with the execution. Here's what happened:

{execute_result}

As the ARCHITECT, analyze what went wrong and create a revised plan.
Consider:
1. What failed and why?
2. Alternative approaches
3. What should OMEGA-2 try instead?

Send OMEGA-2 a collaboration message with your revised strategy.
"""
            revised_plan = self.agent1.think_and_act(collab_prompt)
            
            # OMEGA-2 retries with revised plan
            retry_prompt = f"""OMEGA-1 has sent you a revised strategy. Check your messages.
Apply the corrections and retry the failed steps.
Report back when done.
"""
            execute_result = self.agent2.think_and_act(retry_prompt)
        
        elapsed = time.time() - start_time
        
        # ─── FINAL SUMMARY ────────────────────────────────────────────────
        result = {
            "task_id": task_id,
            "task": task_description,
            "status": "completed",
            "duration_seconds": round(elapsed, 1),
            "omega1_plan": plan_result[:500] if plan_result else "No plan generated",
            "omega2_execution": execute_result[:500] if execute_result else "No execution result",
            "omega1_tool_calls": self.agent1.tool_call_count,
            "omega2_tool_calls": self.agent2.tool_call_count,
            "timestamp": datetime.now().isoformat(),
        }
        
        self.task_history.append(result)
        
        # Save checkpoint
        self._save_checkpoint()
        
        # Display results
        self._display_team_summary(result, elapsed)
        
        return result
    
    def _display_team_summary(self, result: dict, elapsed: float):
        """Display a beautiful team mission summary."""
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        
        print(f"\n{'═' * 60}")
        print_success(f"🚀 DUAL-OMEGA MISSION COMPLETE")
        print(f"{'═' * 60}")
        print_table(
            "Team Performance",
            ["Metric", "Value"],
            [
                ["Task ID", result["task_id"]],
                ["Duration", f"{mins}m {secs}s"],
                ["OMEGA-1 Tool Calls", str(result["omega1_tool_calls"])],
                ["OMEGA-2 Tool Calls", str(result["omega2_tool_calls"])],
                ["Total Tools Called", str(result["omega1_tool_calls"] + result["omega2_tool_calls"])],
                ["Status", result["status"]],
            ],
        )
        print(f"{'═' * 60}")
        print_info(f"🎯 Task: {result['task']}")
        print_info(f"📁 Full log: {TEAM_DIR}")
        print(f"{'═' * 60}\n")
    
    def _save_checkpoint(self):
        """Save team state checkpoint."""
        data = {
            "current_task_id": self.current_task_id,
            "task_count": len(self.task_history),
            "recent_tasks": [
                {
                    "task_id": t["task_id"],
                    "task": t["task"][:100],
                    "status": t["status"],
                    "duration": t["duration_seconds"],
                }
                for t in self.task_history[-5:]
            ],
            "timestamp": datetime.now().isoformat(),
        }
        CHECKPOINT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def load_history(self) -> List[dict]:
        """Load task history."""
        return self.task_history
    
    def get_agent_stats(self) -> dict:
        """Get statistics for both agents."""
        return {
            "omega-1": {
                "name": "OMEGA-1 (Architect)",
                "api": "Existing API Key",
                "model": self.config1.model,
                "tool_calls": self.agent1.tool_call_count,
            },
            "omega-2": {
                "name": "OMEGA-2 (Executor)", 
                "api": "New API Key (provided)",
                "model": self.config2.model,
                "tool_calls": self.agent2.tool_call_count,
            },
        }


# ─── Team Interactive Mode ──────────────────────────────────────────────────

def run_team_interactive():
    """Run the team in interactive mode."""
    coordinator = TeamCoordinator()
    
    print_banner()
    print_info("╔══════════════════════════════════════════════════════════╗")
    print_info("║     OMEGA DUAL-AGENT TEAM — DEPLOYED                   ║")
    print_info("║     OMEGA-1: Architect/Planner (Existing API)          ║")
    print_info("║     OMEGA-2: Implementer/Executor (New API)            ║")
    print_info("╚══════════════════════════════════════════════════════════╝")
    print()
    print_info("Type your mission, or:")
    print_info("  /stats   — View team statistics")
    print_info("  /history — View task history")
    print_info("  /agents  — View agent configurations")
    print_info("  /exit    — Shutdown team")
    print()
    
    while True:
        try:
            from cli import get_input
            user_input = get_input(model_name="DUAL-OMEGA TEAM")
            
            if user_input is None:
                break
            if not user_input:
                continue
            
            if user_input.startswith("/"):
                cmd = user_input.lower().split()[0]
                
                if cmd in ("/exit", "/quit", "/q"):
                    print_success("DUAL-OMEGA TEAM standing down. Mission accomplished! 🏆")
                    break
                    
                elif cmd == "/stats":
                    stats = coordinator.get_agent_stats()
                    for name, info in stats.items():
                        print_table(f"{name}", list(info.keys()), [list(info.values())])
                
                elif cmd == "/history":
                    history = coordinator.load_history()
                    if history:
                        for task in history[-5:]:
                            print_info(f"  [{task['task_id']}] {task['task'][:80]}... — {task['status']} ({task['duration_seconds']}s)")
                    else:
                        print_info("No task history yet.")
                
                elif cmd == "/agents":
                    print_table(
                        "Agent Configuration",
                        ["Property", "OMEGA-1 (Architect)", "OMEGA-2 (Executor)"],
                        [
                            ["API Key", f"...{coordinator.config1.api_key[-4:]}", f"...{coordinator.config2.api_key[-4:]}"],
                            ["Base URL", coordinator.config1.base_url, coordinator.config2.base_url],
                            ["Model", coordinator.config1.model, coordinator.config2.model],
                            ["Tools Available", str(len(TOOL_DEFINITIONS)), str(len(TOOL_DEFINITIONS))],
                        ],
                    )
                
                else:
                    print_info(f"Unknown command: {cmd}")
                continue
            
            # Process the task with the team
            coordinator.assign_task(user_input)
            
        except KeyboardInterrupt:
            print("\n  Team interrupted. Type /exit to quit.")
            continue
        except Exception as e:
            print_error(f"Team error: {e}")
            import traceback
            traceback.print_exc()
            continue


# ─── CLI Entry Point ────────────────────────────────────────────────────────

def main():
    """Main entry point for dual-OMEGA team mode."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OMEGA DUAL-AGENT TEAM — Two OMEGA instances working together",
    )
    parser.add_argument("task", nargs="*", help="Task to execute (omit for interactive mode)")
    parser.add_argument("--stats", action="store_true", help="Show team stats")
    parser.add_argument("--version", action="store_true", help="Show version")
    
    args = parser.parse_args()
    
    if args.version:
        print("OMEGA Dual-Agent Team v1.0")
        return
    
    if args.stats:
        coordinator = TeamCoordinator()
        stats = coordinator.get_agent_stats()
        for name, info in stats.items():
            print_table(f"{name}", list(info.keys()), [list(info.values())])
        return
    
    if args.task:
        task = " ".join(args.task)
        coordinator = TeamCoordinator()
        coordinator.assign_task(task)
    else:
        run_team_interactive()


if __name__ == "__main__":
    main()
