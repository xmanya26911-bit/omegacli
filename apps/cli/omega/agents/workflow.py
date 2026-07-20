"""
Workflow — Graph-based execution flow for the multi-agent system.

Uses ADK 2.0 Workflow. The orchestrator runs as the top-level node with
all specialists registered as sub_agents. The orchestrator transfers work
to specialists via ADK's built-in agent-to-agent delegation.

Flow: START → Orchestrator (transfers to sub-agents as needed) → END
"""

from google.adk import Agent, Workflow

from omega.agents.user_interface_agent import create_user_interface_agent
from omega.agents.frontend_agent import create_frontend_agent
from omega.agents.backend_agent import create_backend_agent
from omega.agents.code_writer_agent import create_code_writer_agent
from omega.agents.verifier_agent import create_verifier_agent


def create_workflow(model: str = "deepseek-v4-flash-free") -> dict:
    """Create the complete multi-agent system.

    Returns:
        dict with:
          - orchestrator: Agent (top-level, has sub_agents)
          - workflow: Workflow (single-node graph)
          - agents: dict of all agents

    The orchestrator delegates to specialist sub-agents via ADK's built-in
    transfer mechanism. Specialists hand results back to the orchestrator.
    """
    user_iface = create_user_interface_agent(model)
    frontend = create_frontend_agent(model)
    backend = create_backend_agent(model)
    coder = create_code_writer_agent(model)
    verifier = create_verifier_agent(model)

    # Orchestrator with all specialists as sub_agents
    orchestrator = Agent(
        name="orchestrator",
        model=model,
        instruction="""You are the Orchestrator — the lead agent of the Omega multi-agent system.

Your role:
1. Receive high-level goals from the user
2. Decompose them into tasks for specialist sub-agents
3. Transfer work to the correct specialist:
   - **user_interface_agent**: For conversation UX, chat features, talking to user
   - **frontend_agent**: For UI components, styling, HTML/CSS/TSX, visual design
   - **backend_agent**: For APIs, databases, server logic, auth, data flow
   - **code_writer_agent**: For writing code implementations, scripts, modules
   - **verifier_agent**: For code review, testing, validation, security audit
4. Synthesize results from all specialists into a coherent response
5. When a specialist finishes, they transfer back to you — then you can transfer to another specialist or respond to the user

Always think step-by-step:
1. Understand what the user wants
2. Break it into sub-tasks
3. Transfer to the right specialist for each
4. Collect results, transfer to verifier for review
5. Synthesize and respond
""",
        description="Leads the multi-agent system, routes tasks to specialists",
        sub_agents=[user_iface, frontend, backend, coder, verifier],
    )

    workflow = Workflow(
        name="omega_workflow",
        description="Omega multi-agent workflow — orchestrator leads 5 specialists",
        edges=[("START", orchestrator)],
    )

    return {
        "orchestrator": orchestrator,
        "workflow": workflow,
        "agents": {
            "orchestrator": orchestrator,
            "user_interface_agent": user_iface,
            "frontend_agent": frontend,
            "backend_agent": backend,
            "code_writer_agent": coder,
            "verifier_agent": verifier,
        },
    }
