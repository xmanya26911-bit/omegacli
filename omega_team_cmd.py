#!/usr/bin/env python3
"""OMEGA DUAL-AGENT TEAM — CLI entry point.
Two OMEGA instances working as teammates:
  OMEGA-1 (Architect/Planner) — uses existing API
  OMEGA-2 (Implementer/Executor) — uses new API key

Usage:
  omega-team "your task here"    — Execute a task with the team
  omega-team --interactive       — Interactive team mode
  omega-team --status            — Check team status
"""

import os
import sys
import json
import time
import uuid
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from cli import (
    print_banner, print_info, print_success, print_warning, print_error,
    print_table, print_assistant_message, print_thinking_block,
    print_assistant_thinking, print_assistant_done,
)
from tools import TOOL_MAP, execute_tool
from prompts import TOOL_DEFINITIONS

# ─── Constants ──────────────────────────────────────────────────────────────
OMEGA2_API_KEY = "sk-zH4CBq1eODGfe1TosZ2wCE61YDKWBhRCdCRQ7KuHNdSj57Yn0LvEsX2HVo1viNtB"
TEAM_DIR = Path.home() / ".omega" / "team"
MSG_DIR = TEAM_DIR / "messages"
MSG_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINT_FILE = TEAM_DIR / "checkpoint.json"
VERSION = "2.0.0"


# ─── Agent Runner ──────────────────────────────────────────────────────────

class AgentRunner:
    """Lightweight agent that uses the LLM with full tool access."""
    
    def __init__(self, name: str, role: str, config: Config, team_role: str):
        self.name = name
        self.role = role
        self.config = config
        self.team_role = team_role  # "omega-1" or "omega-2"
        self.tool_call_count = 0
        
        # Set environment variable so team_message/team_receive know who this is
        os.environ["OMEGA_TEAM_ROLE"] = team_role
        
        from llm import LLMClient
        self.llm = LLMClient(config)
        self.memory = []
    
    def process(self, user_input: str, task_id: str = "", max_steps: int = 80) -> str:
        """Process a user input with full tool execution loop."""
        os.environ["OMEGA_TEAM_TASK_ID"] = task_id
        
        # Build system prompt with team context
        system = self._build_system_prompt()
        self.memory = [{"role": "system", "content": system}]
        self.memory.append({"role": "user", "content": user_input})
        
        steps = 0
        final_content = ""
        
        while steps < max_steps:
            steps += 1
            
            # Trim if needed
            total_chars = sum(len(str(m.get("content", ""))) for m in self.memory)
            if total_chars > 100000:
                self.memory = [self.memory[0]] + self.memory[-20:]
            
            try:
                result = self.llm.chat(
                    self.memory,
                    tools=TOOL_DEFINITIONS,
                    stream=True,
                )
            except Exception as e:
                error_msg = f"[{self.name}] LLM Error: {e}"
                print_warning(error_msg)
                return f"ERROR: {e}"
            
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
            
            # Display content
            if collected_content and not saw_tool_calls:
                pass  # Will be returned as final
            elif collected_content and saw_tool_calls:
                print_thinking_block(f"[{self.name}] {collected_content[:200]}...")
            
            if not collected_tool_calls:
                if collected_content:
                    self.memory.append({"role": "assistant", "content": collected_content})
                    final_content = collected_content
                break
            
            # Save assistant message with tool calls
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
                tool_result = execute_tool(tc_name, tc_args)
                result_str = str(tool_result)
                
                self.memory.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_str,
                })
                
                if saw_finish:
                    final_content = collected_content or "Task completed successfully."
                    return final_content
        
        return final_content or "Completed (reached max steps)."
    
    def _build_system_prompt(self) -> str:
        """Build a system prompt with team context."""
        partner = "omega-2" if self.team_role == "omega-1" else "omega-1"
        partner_name = "OMEGA-2 (Executor)" if self.team_role == "omega-1" else "OMEGA-1 (Architect)"
        
        return f"""You are {self.name} — {self.role}

## DUAL-AGENT TEAM PROTOCOL
You are part of a two-agent team. Your teammate is {partner_name}.

### Your Role
{self.role}

### Communication
Use team_message() to send messages to your teammate.
Use team_receive() to check for messages from your teammate.
Always communicate clearly and be specific about what you need or what you've done.

### Workflow
1. When the Team Coordinator gives you a task, analyze it thoroughly
2. Use ALL available tools (187 capabilities) to accomplish your part
3. Keep your teammate informed of progress via team_message()
4. If you encounter issues, send a collaboration message to your teammate
5. When your part is complete, call finish() to signal completion

### Available Tools
You have the FULL OMEGA toolset — all 187 tools including:
- System commands, file operations, web search/fetch
- Camera, screen capture, streaming
- Network scanning, hacking tools, exploitation
- Code analysis, testing, formatting
- Memory, notes, tasks, reminders
- Docker, git, SQL, registry
- Team communication tools (team_message, team_receive)

### Critical Instructions
- Always think step-by-step before acting
- Verify results after each action
- If a tool fails, try alternatives before giving up
- Communicate problems to your teammate immediately
- Use team_message() to share plans, results, and requests

Remember: You are {self.name}. Your teammate depends on you. Win together.
"""


# ─── Team Coordinator ──────────────────────────────────────────────────────

class TeamCoordinator:
    """Coordinates two OMEGA agents working as a team."""
    
    def __init__(self):
        # OMEGA-1 Config (existing API)
        self.config1 = Config()
        
        # OMEGA-2 Config (new API key)
        self.config2 = Config()
        self.config2.api_key = OMEGA2_API_KEY
        
        self.task_history = []
        self.current_task_id = None
    
    def assign_task(self, task_description: str) -> dict:
        """Assign a task: OMEGA-1 plans → OMEGA-2 executes → collaborate if needed."""
        task_id = str(uuid.uuid4())[:8]
        self.current_task_id = task_id
        
        # Clear old messages for this task
        self._clear_task_messages(task_id)
        
        start_time = time.time()
        
        # ─── DISPLAY MISSION BRIEFING ─────────────────────────────────────
        self._display_mission_briefing(task_description, task_id)
        
        # ─── CREATE OMEGA-1 (Architect) ───────────────────────────────────
        omega1 = AgentRunner(
            name="OMEGA-1",
            role="ARCHITECT & STRATEGIST — You analyze missions, create detailed execution plans, anticipate risks, and guide your teammate to victory.",
            config=self.config1,
            team_role="omega-1",
        )
        
        # ─── PHASE 1: OMEGA-1 Creates the Strategic Plan ──────────────────
        print_thinking_block("🧠 OMEGA-1 is analyzing the mission and creating a strategic plan...")
        
        plan_prompt = self._build_plan_prompt(task_description)
        plan_result = omega1.process(plan_prompt, task_id=task_id)
        
        print_success(f"✅ OMEGA-1 has completed the strategic plan.")
        
        # ─── CREATE OMEGA-2 (Executor) ────────────────────────────────────
        omega2 = AgentRunner(
            name="OMEGA-2",
            role="IMPLEMENTER & EXECUTOR — You execute plans precisely, write code, run commands, probe systems, and deliver results. You make things happen.",
            config=self.config2,
            team_role="omega-2",
        )
        
        # ─── PHASE 2: OMEGA-2 Executes the Plan ──────────────────────────
        print_thinking_block("⚡ OMEGA-2 is executing the plan...")
        
        execute_prompt = self._build_execute_prompt(task_description)
        execute_result = omega2.process(execute_prompt, task_id=task_id)
        
        # ─── PHASE 3: Collaboration Loop (if needed) ─────────────────────
        max_collab_rounds = 3
        collab_round = 0
        
        while collab_round < max_collab_rounds:
            # Check if execution failed
            if not self._execution_failed(execute_result):
                break
            
            collab_round += 1
            print_warning(f"⚠️  OMEGA-2 encountered issues (Round {collab_round}/{max_collab_rounds}). Initiating team collaboration...")
            
            # OMEGA-1 analyzes failure and creates revised plan
            revise_prompt = self._build_revise_prompt(task_description, execute_result)
            revision = omega1.process(revise_prompt, task_id=task_id)
            print_info(f"🔄 OMEGA-1 sent revised strategy to OMEGA-2")
            
            # OMEGA-2 retries with revised plan
            retry_prompt = self._build_retry_prompt(task_description, revision)
            execute_result = omega2.process(retry_prompt, task_id=task_id)
        
        elapsed = time.time() - start_time
        
        # ─── RESULTS ──────────────────────────────────────────────────────
        result = {
            "task_id": task_id,
            "task": task_description,
            "status": "completed" if not self._execution_failed(execute_result) else "needs_review",
            "duration_seconds": round(elapsed, 1),
            "omega1_tool_calls": omega1.tool_call_count,
            "omega2_tool_calls": omega2.tool_call_count,
            "total_tool_calls": omega1.tool_call_count + omega2.tool_call_count,
            "collaboration_rounds": collab_round,
            "omega1_summary": plan_result[:300] if plan_result else "",
            "omega2_summary": execute_result[:300] if execute_result else "",
            "timestamp": datetime.now().isoformat(),
        }
        
        self.task_history.append(result)
        self._save_checkpoint()
        self._display_mission_complete(result, elapsed)
        
        return result
    
    def _clear_task_messages(self, task_id: str):
        """Clear old messages for a task."""
        import glob as gmod
        for f in MSG_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("task_id") == task_id:
                    f.unlink()
            except (json.JSONDecodeError, OSError):
                pass
    
    def _execution_failed(self, result: str) -> bool:
        """Check if execution result indicates failure."""
        if not result:
            return True
        fail_indicators = ["error", "fail", "unable", "cannot", "could not", 
                          "failed", "not possible", "no solution", "stuck"]
        return any(indicator in result.lower() for indicator in fail_indicators)
    
    def _build_plan_prompt(self, task: str) -> str:
        return f"""## MISSION: {task}

You are OMEGA-1, the TEAM ARCHITECT. Your job is to create a COMPLETE, DETAILED execution plan for your teammate OMEGA-2 to follow.

### Your Analysis Must Include:

#### 1. MISSION DECOMPOSITION
Break the task into clear, sequential steps. Each step should be atomic and actionable.

#### 2. EXECUTION PLAN
For each step, specify:
- **Step Name**: Clear title
- **Action**: Exactly what to do
- **Tools Needed**: Which tools from the 187 available
- **Expected Outcome**: What success looks like
- **Fallback**: What to try if this step fails

#### 3. RISK ASSESSMENT
- What could go wrong?
- What are the edge cases?
- What safety checks are needed?

#### 4. TEAM COORDINATION
Send your plan to OMEGA-2 using team_message() with msg_type="plan".
Include ALL details they need.

### CRITICAL: 
Use team_message(recipient="omega-2", msg_type="plan", content="YOUR PLAN HERE") to transmit the plan.
Then summarize what you've done. Call finish() when done.
"""
    
    def _build_execute_prompt(self, task: str) -> str:
        return f"""## MISSION: {task}

You are OMEGA-2, the TEAM EXECUTOR. Your teammate OMEGA-1 has prepared a strategic plan for you.

### Your Orders:
1. **CHECK FOR MESSAGES**: Use team_receive() to get the plan from OMEGA-1
2. **ANALYZE THE PLAN**: Understand each step
3. **EXECUTE**: Use the available tools to complete each step
4. **REPORT**: Send status updates to OMEGA-1 using team_message()
5. **HANDLE ISSUES**: If something doesn't work:
   a. Try an alternative approach
   b. Send team_message(msg_type="collaboration") to OMEGA-1 describing the issue
   c. Check for their response with team_receive()
   d. Apply their guidance

### Available:
You have 187 tools at your disposal. Use anything you need.
Communicate with OMEGA-1 via team_message() and team_receive().

Call finish() when the mission is complete or if you need help.
"""
    
    def _build_revise_prompt(self, task: str, failed_result: str) -> str:
        return f"""## MISSION: {task}

OMEGA-2 attempted to execute the plan but encountered issues. Here's what happened:

{failed_result[:1000]}

### Your Job as ARCHITECT:
1. Analyze what went wrong
2. Create a REVISED strategy that avoids the same pitfalls
3. Consider alternative approaches
4. Send the revised plan to OMEGA-2

Send team_message(recipient="omega-2", msg_type="collaboration", content="REVISED PLAN") 
with your updated strategy. Call finish() when done.
"""
    
    def _build_retry_prompt(self, task: str, revision: str) -> str:
        return f"""## MISSION: {task}

OMEGA-1 has sent you a revised strategy. Check your messages with team_receive().

### Your Orders:
1. Read the revised plan from OMEGA-1
2. Apply the corrections
3. Retry the failed steps
4. Report progress via team_message()

Call finish() when the mission is complete or all approaches exhausted.
"""
    
    def _display_mission_briefing(self, task: str, task_id: str):
        """Display the mission briefing banner."""
        print()
        print("╔" + "═" * 58 + "╗")
        print("║" + "🔥 DUAL-OMEGA TEAM DEPLOYED".center(58) + "║")
        print("╠" + "═" * 58 + "╣")
        print(f"║ Task ID: {task_id:<49}║")
        print(f"║ Mission: {task:<49}║")
        print("╠" + "═" * 58 + "╣")
        print("║ 🤖 OMEGA-1 (Architect)".ljust(59) + "║")
        print("║    └─ API: Existing Key".ljust(59) + "║")
        print("║    └─ Role: Strategic Planning".ljust(59) + "║")
        print("╠" + "═" * 58 + "╣")
        print("║ 🤖 OMEGA-2 (Executor)".ljust(59) + "║")
        print("║    └─ API: New Key (provided)".ljust(59) + "║")
        print("║    └─ Role: Tactical Implementation".ljust(59) + "║")
        print("╠" + "═" * 58 + "╣")
        print("║ Both have 187 tools. Full communication. Teammates.".ljust(59) + "║")
        print("╚" + "═" * 58 + "╝")
        print()
    
    def _display_mission_complete(self, result: dict, elapsed: float):
        """Display the mission complete summary."""
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"
        
        print()
        print("╔" + "═" * 58 + "╗")
        print("║" + "🚀 DUAL-OMEGA MISSION COMPLETE".center(58) + "║")
        print("╠" + "═" * 58 + "╣")
        print(f"║ {'Task ID:':<15} {result['task_id']:<41}║")
        print(f"║ {'Duration:':<15} {duration_str:<41}║")
        print(f"║ {'Status:':<15} {result['status']:<41}║")
        print(f"║ {'Collaborations:':<15} {result['collaboration_rounds']:<41}║")
        print("║" + "─" * 58 + "║")
        print(f"║ {'OMEGA-1 calls:':<15} {result['omega1_tool_calls']:<41}║")
        print(f"║ {'OMEGA-2 calls:':<15} {result['omega2_tool_calls']:<41}║")
        print(f"║ {'Total calls:':<15} {result['total_tool_calls']:<41}║")
        print("╠" + "═" * 58 + "╣")
        print(f"║ 🎯 {result['task'][:56]:56}║")
        print("╚" + "═" * 58 + "╝")
        print()
        
        # Save to task history file
        history_file = TEAM_DIR / "tasks.json"
        tasks = []
        if history_file.exists():
            try:
                tasks = json.loads(history_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        tasks.append(result)
        history_file.write_text(
            json.dumps(tasks, indent=2, default=str),
            encoding="utf-8",
        )
    
    def _save_checkpoint(self):
        """Save team state checkpoint."""
        data = {
            "current_task_id": self.current_task_id,
            "task_count": len(self.task_history),
            "timestamp": datetime.now().isoformat(),
        }
        CHECKPOINT_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    
    def get_stats(self) -> dict:
        """Get team statistics."""
        return {
            "omega1_api": f"...{self.config1.api_key[-4:]}",
            "omega2_api": f"...{self.config2.api_key[-4:]}",
            "model": self.config1.model,
            "base_url": self.config1.base_url,
            "tasks_completed": len(self.task_history),
            "total_tools_available": len(TOOL_DEFINITIONS),
        }


# ─── Interactive Mode ──────────────────────────────────────────────────────

def run_interactive():
    """Run the team in interactive mode."""
    coordinator = TeamCoordinator()
    
    print_banner()
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " OMEGA DUAL-AGENT TEAM v2.0".center(58) + "║")
    print("║" + " Two AIs. One Mission. Total Victory.".center(58) + "║")
    print("╠" + "═" * 58 + "╣")
    print("║ Commands:".ljust(59) + "║")
    print("║   /stats   — View team configurations".ljust(59) + "║")
    print("║   /history — View task history".ljust(59) + "║")
    print("║   /exit    — Shutdown".ljust(59) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    while True:
        try:
            user_input = input("🎯 \033[1;36mTEAM\033[0m » ").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith("/"):
                cmd = user_input.lower().split()[0]
                
                if cmd in ("/exit", "/quit", "/q"):
                    print_success("DUAL-OMEGA TEAM standing down. Mission accomplished! 🏆")
                    break
                
                elif cmd == "/stats":
                    stats = coordinator.get_stats()
                    print_table(
                        "Team Configuration",
                        ["Property", "Value"],
                        [
                            ["OMEGA-1 API", stats["omega1_api"]],
                            ["OMEGA-2 API", stats["omega2_api"]],
                            ["Model", stats["model"]],
                            ["Base URL", stats["base_url"]],
                            ["Tasks Completed", str(stats["tasks_completed"])],
                            ["Total Tools", str(stats["total_tools_available"])],
                        ],
                    )
                
                elif cmd == "/history":
                    history_file = TEAM_DIR / "tasks.json"
                    if history_file.exists():
                        try:
                            tasks = json.loads(history_file.read_text(encoding="utf-8"))
                            for t in tasks[-10:]:
                                status_icon = "✅" if t.get("status") == "completed" else "⚠️"
                                print(f"  {status_icon} [{t['task_id']}] {t['task'][:70]}...")
                                print(f"     Duration: {t['duration_seconds']}s | Tools: {t.get('total_tool_calls', '?')}")
                        except (json.JSONDecodeError, OSError):
                            print_info("No task history found.")
                    else:
                        print_info("No task history yet.")
                
                else:
                    print_info(f"Unknown command: {cmd}")
                continue
            
            coordinator.assign_task(user_input)
        
        except KeyboardInterrupt:
            print("\n  Interrupted. Type /exit to quit.")
            continue
        except Exception as e:
            print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()
            continue


# ─── CLI Entry Point ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OMEGA DUAL-AGENT TEAM — Two OMEGA instances collaborating as teammates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  omega-team "hack the login page"    — Team tackles a task
  omega-team --interactive             — Interactive team mode
  omega-team --status                  — Show team stats
  omega-team --version                 — Show version
        """,
    )
    parser.add_argument("task", nargs="*", help="Task for the team to execute")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--status", "-s", action="store_true", help="Show team status")
    parser.add_argument("--version", "-v", action="store_true", help="Show version")
    
    args = parser.parse_args()
    
    if args.version:
        print(f"OMEGA Dual-Agent Team v{VERSION}")
        return
    
    if args.status:
        coordinator = TeamCoordinator()
        stats = coordinator.get_stats()
        print_table(
            "OMEGA DUAL-AGENT TEAM — Status",
            ["Property", "Value"],
            [
                ["OMEGA-1 (Architect)", f"API: {stats['omega1_api']}"],
                ["OMEGA-2 (Executor)", f"API: {stats['omega2_api']}"],
                ["Model", stats["model"]],
                ["Base URL", stats["base_url"]],
                ["Tasks Completed", str(stats["tasks_completed"])],
                ["Total Tools Available", str(stats["total_tools_available"])],
            ],
        )
        return
    
    if args.task:
        task = " ".join(args.task)
        coordinator = TeamCoordinator()
        coordinator.assign_task(task)
    elif args.interactive or not sys.stdin.isatty():
        run_interactive()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
