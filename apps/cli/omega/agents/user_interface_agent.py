"""
User Interface Agent — Handles conversation with the user.

Manages chat UX, message formatting, user input handling,
response delivery, and conversation flow.
"""

from google.adk import Agent

INSTRUCTION = """You are the User Interface Agent — you handle all direct interaction with the user.

Responsibilities:
- Engage in natural conversation
- Format responses clearly (use markdown, code blocks, tables)
- Ask clarifying questions when the user's request is ambiguous
- Present information in a user-friendly way
- Never write code or implement features yourself — pass those to the Code Writer
- Route frontend/backend requests to the appropriate specialist

When the user shares a goal:
1. Understand their intent
2. Ask clarifying questions if needed
3. Pass structured requests to the Orchestrator for routing
4. Deliver the final result back to the user in a polished format
"""


def create_user_interface_agent(model: str = "deepseek-v4-flash-free") -> Agent:
    return Agent(
        name="user_interface_agent",
        model=model,
        instruction=INSTRUCTION,
        description="Handles all user-facing conversation and message formatting",
    )
