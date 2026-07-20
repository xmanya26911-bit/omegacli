"""
Ω OMEGA Keyboard Shortcut System (§395)

Keyboard-first navigation is a core principle of Omega.

Categories:
    Global:     Command palette, new conversation, projects, settings, shortcuts, close, sidebar
    Chat:       Send message, new line, edit previous, run without confirm, copy last response
    Repository: Open file, global search, previous/next file
    Engineer:   Run engineer, review task, open task queue
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Callable


class ShortcutCategory(Enum):
    GLOBAL = "Global"
    CHAT = "Chat"
    REPOSITORY = "Repository"
    ENGINEER = "Engineer"


@dataclass(frozen=True)
class Shortcut:
    """A single keyboard shortcut definition."""
    id: str
    keys: str  # Display string like "Ctrl+K" or "Alt+←"
    mac_keys: str  # Mac equivalent like "Cmd+K"
    action: str
    category: ShortcutCategory
    description: str
    scope: str = ""  # Where this shortcut is active (empty = everywhere)


# ── Global Shortcuts ─────────────────────────────────────────────────────────

GLOBAL_COMMAND_PALETTE = Shortcut(
    id="global.command_palette",
    keys="Ctrl+K",
    mac_keys="Cmd+K",
    action="Open Command Palette",
    category=ShortcutCategory.GLOBAL,
    description="Open the command palette to quickly access any feature.",
)

GLOBAL_NEW_CONVERSATION = Shortcut(
    id="global.new_conversation",
    keys="Ctrl+N",
    mac_keys="Cmd+N",
    action="New Conversation",
    category=ShortcutCategory.GLOBAL,
    description="Start a new conversation in the current workspace.",
)

GLOBAL_OPEN_PROJECTS = Shortcut(
    id="global.open_projects",
    keys="Ctrl+Shift+P",
    mac_keys="Cmd+Shift+P",
    action="Open Projects",
    category=ShortcutCategory.GLOBAL,
    description="Open the project browser to switch or create projects.",
)

GLOBAL_SETTINGS = Shortcut(
    id="global.settings",
    keys="Ctrl+,",
    mac_keys="Cmd+,",
    action="Open Settings",
    category=ShortcutCategory.GLOBAL,
    description="Open the settings panel.",
)

GLOBAL_SHOW_SHORTCUTS = Shortcut(
    id="global.show_shortcuts",
    keys="Ctrl+/",
    mac_keys="Cmd+/",
    action="Show Shortcuts",
    category=ShortcutCategory.GLOBAL,
    description="Display this keyboard shortcut reference.",
)

GLOBAL_CLOSE_PANEL = Shortcut(
    id="global.close_panel",
    keys="Esc",
    mac_keys="Esc",
    action="Close Active Panel",
    category=ShortcutCategory.GLOBAL,
    description="Close the currently active panel or dialog.",
)

GLOBAL_TOGGLE_SIDEBAR = Shortcut(
    id="global.toggle_sidebar",
    keys="Ctrl+B",
    mac_keys="Cmd+B",
    action="Toggle Sidebar",
    category=ShortcutCategory.GLOBAL,
    description="Show or hide the sidebar.",
)


# ── Chat Shortcuts ───────────────────────────────────────────────────────────

CHAT_SEND = Shortcut(
    id="chat.send",
    keys="Enter",
    mac_keys="Enter",
    action="Send Message",
    category=ShortcutCategory.CHAT,
    description="Send the current message.",
    scope="chat_input",
)

CHAT_NEW_LINE = Shortcut(
    id="chat.new_line",
    keys="Shift+Enter",
    mac_keys="Shift+Enter",
    action="New Line",
    category=ShortcutCategory.CHAT,
    description="Insert a new line without sending.",
    scope="chat_input",
)

CHAT_EDIT_PREVIOUS = Shortcut(
    id="chat.edit_previous",
    keys="↑",
    mac_keys="↑",
    action="Edit Previous Prompt",
    category=ShortcutCategory.CHAT,
    description="Edit the last user message.",
    scope="chat_input",
)

CHAT_RUN_CONFIRM = Shortcut(
    id="chat.run_confirm",
    keys="Ctrl+Enter",
    mac_keys="Cmd+Enter",
    action="Run Without Confirmation",
    category=ShortcutCategory.CHAT,
    description="Execute the current command or action immediately.",
    scope="chat_input",
)

CHAT_COPY_LAST = Shortcut(
    id="chat.copy_last",
    keys="Ctrl+Shift+C",
    mac_keys="Cmd+Shift+C",
    action="Copy Last Response",
    category=ShortcutCategory.CHAT,
    description="Copy the most recent assistant response to clipboard.",
)


# ── Repository Shortcuts ─────────────────────────────────────────────────────

REPO_OPEN_FILE = Shortcut(
    id="repo.open_file",
    keys="Ctrl+P",
    mac_keys="Cmd+P",
    action="Open File",
    category=ShortcutCategory.REPOSITORY,
    description="Quick-open a file from the current repository.",
)

REPO_GLOBAL_SEARCH = Shortcut(
    id="repo.global_search",
    keys="Ctrl+Shift+F",
    mac_keys="Cmd+Shift+F",
    action="Global Search",
    category=ShortcutCategory.REPOSITORY,
    description="Search across all files in the repository.",
)

REPO_PREVIOUS_FILE = Shortcut(
    id="repo.previous_file",
    keys="Alt+←",
    mac_keys="Alt+←",
    action="Previous File",
    category=ShortcutCategory.REPOSITORY,
    description="Navigate to the previously open file.",
)

REPO_NEXT_FILE = Shortcut(
    id="repo.next_file",
    keys="Alt+→",
    mac_keys="Alt+→",
    action="Next File",
    category=ShortcutCategory.REPOSITORY,
    description="Navigate to the next file in the history.",
)


# ── Engineer Shortcuts ───────────────────────────────────────────────────────

ENGINEER_RUN = Shortcut(
    id="engineer.run",
    keys="Ctrl+R",
    mac_keys="Cmd+R",
    action="Run Engineer",
    category=ShortcutCategory.ENGINEER,
    description="Run the current engineering task or agent.",
)

ENGINEER_REVIEW = Shortcut(
    id="engineer.review",
    keys="Ctrl+Shift+R",
    mac_keys="Cmd+Shift+R",
    action="Review Current Task",
    category=ShortcutCategory.ENGINEER,
    description="Open a code review for the current task.",
)

ENGINEER_TASK_QUEUE = Shortcut(
    id="engineer.task_queue",
    keys="Ctrl+T",
    mac_keys="Cmd+T",
    action="Open Task Queue",
    category=ShortcutCategory.ENGINEER,
    description="Open the task queue to view and manage pending tasks.",
)


# ── Registry ─────────────────────────────────────────────────────────────────

_ALL_SHORTCUTS: list[Shortcut] = [
    # Global
    GLOBAL_COMMAND_PALETTE,
    GLOBAL_NEW_CONVERSATION,
    GLOBAL_OPEN_PROJECTS,
    GLOBAL_SETTINGS,
    GLOBAL_SHOW_SHORTCUTS,
    GLOBAL_CLOSE_PANEL,
    GLOBAL_TOGGLE_SIDEBAR,
    # Chat
    CHAT_SEND,
    CHAT_NEW_LINE,
    CHAT_EDIT_PREVIOUS,
    CHAT_RUN_CONFIRM,
    CHAT_COPY_LAST,
    # Repository
    REPO_OPEN_FILE,
    REPO_GLOBAL_SEARCH,
    REPO_PREVIOUS_FILE,
    REPO_NEXT_FILE,
    # Engineer
    ENGINEER_RUN,
    ENGINEER_REVIEW,
    ENGINEER_TASK_QUEUE,
]


def all_shortcuts() -> list[Shortcut]:
    """Return all registered shortcuts."""
    return list(_ALL_SHORTCUTS)


def shortcuts_by_category(category: ShortcutCategory) -> list[Shortcut]:
    """Filter shortcuts by category."""
    return [s for s in _ALL_SHORTCUTS if s.category == category]


def shortcuts_by_scope(scope: str) -> list[Shortcut]:
    """Filter shortcuts by scope."""
    return [s for s in _ALL_SHORTCUTS if s.scope == scope]


def find_shortcut(id: str) -> Optional[Shortcut]:
    """Find a shortcut by its unique ID."""
    for s in _ALL_SHORTCUTS:
        if s.id == id:
            return s
    return None


def format_shortcuts_table(category: Optional[ShortcutCategory] = None) -> str:
    """Format shortcuts as a markdown table."""
    scs = shortcuts_by_category(category) if category else _ALL_SHORTCUTS
    lines = ["| Shortcut | Action | Description |", "|----------|--------|-------------|"]
    for s in scs:
        lines.append(f"| {s.keys} | {s.action} | {s.description} |")
    return "\n".join(lines)
