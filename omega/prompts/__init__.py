"""
OMEGA Prompts — System prompts and tool definitions for the OMEGA agent.

This package provides modular prompt components that can be composed
to build the full system prompt for any agent configuration.

Modules:
    personality.py     — Chatbot personality strings

Parts not yet extracted from the legacy 4,216-line prompts.py:
    base.py           — System prompt base
    tool_defs.py      — Tool definitions (TOOL_DEFINITIONS dict)
    
Use the legacy prompts.py directly for full prompt composition.
This package currently re-exports the personality and will grow
as extraction progresses.
"""

from __future__ import annotations

from omega.prompts.personality import CHATBOT_PERSONALITY

__all__ = [
    "CHATBOT_PERSONALITY",
    "build_system_prompt",
]


def build_system_prompt(self_paths: list | None = None) -> str:
    """Build the complete system prompt.

    NOTE: Full prompt composition with tool definitions is currently
    handled by the legacy prompts.py module (4,216 lines). This function
    returns the personality as a placeholder until extraction completes.

    Args:
        self_paths: Optional list of file paths for self-examination.

    Returns:
        System prompt string (currently personality only).
    """
    return CHATBOT_PERSONALITY
