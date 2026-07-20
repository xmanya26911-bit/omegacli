"""OMEGA ADK Team — Multi-agent orchestration via Google ADK 2.0.

Provides run_team_task() for one-shot execution and run_team_interactive()
for interactive session. Replaces the old custom omega_team_cmd module.

Team structure:
  Orchestrator → routes to 5 specialists:
    - User Interface Agent  (conversation UX)
    - Frontend Agent        (UI components, styling)
    - Backend Agent         (APIs, databases, auth)
    - Code Writer Agent     (code implementation)
    - Verifier Agent        (code review, testing)

Usage from main.py:
    from omega.team import run_team_task, run_team_interactive
    run_team_task("Build a login page")
    run_team_interactive()
"""

import sys
import os
import time
import uuid

from google.adk import Runner, Workflow
from google.adk.sessions import InMemorySessionService
from google.genai import types

from omega.agents.workflow import create_workflow

# Import LLM to ensure it's registered
from omega.agents import llm as _llm_module  # noqa: F401


def _style(text: str, style_name: str = "dim") -> str:
    """Simple styling for terminal output."""
    styles = {
        "dim": "\033[2m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "cyan": "\033[36m",
        "magenta": "\033[35m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }
    s = styles.get(style_name, styles["dim"])
    e = styles["reset"]
    return f"{s}{text}{e}"


def _print_header():
    """Print the ADK team header."""
    print()
    print(_style("  ╭───────────────────────────────────────────╮", "cyan"))
    print(_style("  │   Ω  OMEGA ADK TEAM  (Multi-Agent Mode)  │", "cyan"))
    print(_style("  │   Orchestrator + 5 Specialists            │", "cyan"))
    print(_style("  ╰───────────────────────────────────────────╯", "cyan"))
    print()


def _print_event(event, agent_name: str = "orchestrator"):
    """Print an ADK event to the console."""
    if event.content and hasattr(event.content, "parts"):
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                # Skip empty or function-call texts
                text = part.text.strip()
                if text and not text.startswith("{"):
                    prefix = _style(f"  [{agent_name}]", "green")
                    print(f"{prefix} {text}")
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                prefix = _style(f"  [{agent_name}]", "yellow")
                print(f"{prefix} ⚡ calling {fc.name}({fc.args if hasattr(fc, 'args') else ''})")
            if hasattr(part, "function_response") and part.function_response:
                prefix = _style(f"  [{agent_name}]", "magenta")
                print(f"{prefix} ✓ {part.function_response.name} done")


def run_team_task(task: str) -> str:
    """Run a single task through the ADK multi-agent system.

    Args:
        task: The task description to execute.

    Returns:
        The final response text.
    """
    _print_header()
    print(f"  {_style('Task:', 'bold')} {task}")
    print()

    # Create the multi-agent workflow
    workflow_system = create_workflow()

    # Create session service
    session_service = InMemorySessionService()
    user_id = "omega-user"
    session_id = str(uuid.uuid4())

    # Create runner for the orchestrator
    orchestrator = workflow_system["orchestrator"]

    runner = Runner(
        agent=orchestrator,
        app_name="omega_team",
        session_service=session_service,
        auto_create_session=True,
    )

    # Create the user message
    user_content = types.Content(
        role="user",
        parts=[types.Part(text=task)],
    )

    # Initialize session with proper context

    # Run and collect response
    full_response = ""
    print(f"  {_style('── Response ──', 'dim')}")
    try:
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=user_content,
        ):
            _print_event(event, event.node_name or "orchestrator")
            if event.content and hasattr(event.content, "parts"):
                for part in (event.content.parts or []):
                    if hasattr(part, "text") and part.text:
                        full_response += part.text
    except Exception as e:
        error_msg = f"Team execution error: {e}"
        print(f"\n  {_style('⚠ Error:', 'yellow')} {e}")
        return error_msg

    print(f"\n  {_style('── Task Complete ──', 'green')}")
    return full_response.strip()


def run_team_interactive():
    """Run the ADK multi-agent system in interactive mode.

    User can type tasks and see the full multi-agent workflow.
    Type 'exit', 'quit', or Ctrl+C to stop.
    """
    _print_header()
    print(f"  {_style('Interactive Mode — type your tasks below', 'dim')}")
    print(f"  {_style('  /help  show commands', 'dim')}")
    print(f"  {_style('  /agents  list all agents', 'dim')}")
    print(f"  {_style('  exit  quit', 'dim')}")
    print()

    # Create the workflow once and reuse the session
    workflow_system = create_workflow()
    orchestrator = workflow_system["orchestrator"]
    agents = workflow_system["agents"]

    session_service = InMemorySessionService()
    user_id = "omega-user"
    session_id = str(uuid.uuid4())

    runner = Runner(
        agent=orchestrator,
        app_name="omega_team",
        session_service=session_service,
        auto_create_session=True,
    )

    while True:
        try:
            task = input(f"\n{_style('Ω team> ', 'cyan')}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not task:
            continue

        if task.lower() in ("exit", "quit"):
            break

        if task.lower() == "/help":
            print(f"  {_style('Commands:', 'bold')}")
            print(f"    {_style('/agents', 'cyan')}  List all agents in the team")
            print(f"    {_style('exit', 'cyan')}     Quit interactive mode")
            print(f"    {_style('anything else', 'dim')}  Send as a task to the team")
            continue

        if task.lower() == "/agents":
            print(f"  {_style('Team Agents:', 'bold')}")
            for name, agent in agents.items():
                desc = agent.description if hasattr(agent, 'description') and agent.description else ""
                print(f"    {_style(f'• {name}', 'green')} {_style(desc, 'dim')}")
            continue

        # Run the task
        user_content = types.Content(
            role="user",
            parts=[types.Part(text=task)],
        )

        print(f"  {_style('── Response ──', 'dim')}")
        try:
            for event in runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=user_content,
            ):
                _print_event(event, event.node_name or "orchestrator")
        except Exception as e:
            print(f"\n  {_style(f'⚠ Error: {e}', 'yellow')}")

    print(f"\n  {_style('Team session ended.', 'dim')}")
