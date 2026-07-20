"""
Omega Agents — Multi-agent system powered by Google ADK 2.0.

Architecture:
   Orchestrator (leader) — runs in a Workflow graph
    ├── user_interface_agent  — talks to user
    ├── frontend_agent        — UI/frontend tasks
    ├── backend_agent         — API/server tasks
    ├── code_writer_agent     — writes code
    └── verifier_agent        — reviews & validates

The orchestrator has all specialists as sub_agents and transfers
work to them via ADK's built-in agent-to-agent delegation.
"""

from omega.agents.workflow import create_workflow
from omega.agents.llm import OpenCodeLlm

__all__ = ["create_workflow", "OpenCodeLlm"]
