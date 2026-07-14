# OMEGA Architecture Refactor — Design Document

> Production-ready architecture for an async-first AI CLI with event-driven rendering, plugin system, and clean separation of concerns.

---

## 1. High-Level Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         OMEGA Application                         │
│                                                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐  │
│  │   Entry   │──▶│  Router  │──▶│  Session  │──▶│  Event Bus   │  │
│  │  (main)   │   │ (modes)  │   │ Manager  │   │ (pub/sub)    │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────┬───────┘  │
│                                                        │          │
│           ┌────────────────────────────────────────────┼────┐     │
│           │                Subscribers                 │    │     │
│           │  ┌──────────┐  ┌──────────┐  ┌────────┐   │    │     │
│           │  │ Renderer │  │  Logger  │  │ Metrics│   │    │     │
│           │  │ (Rich)   │  │ (file)   │  │ (stats)│   │    │     │
│           │  └──────────┘  └──────────┘  └────────┘   │    │     │
│           └────────────────────────────────────────────┼────┘     │
│                                                        │          │
│  ┌─────────────────────────────────────────────────────┼──────┐  │
│  │                    Agent Pipeline                    │      │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────┐ │      │  │
│  │  │ Command  │─▶│  Agent   │─▶│   LLM    │─▶│Tools│ │      │  │
│  │  │  Router  │  │          │  │ Provider │  │     │ │      │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └─────┘ │      │  │
│  └─────────────────────────────────────────────────────┼──────┘  │
│                                                        │          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │          │
│  │  Config      │  │    Plugins   │  │    Memory    │  │          │
│  │  (Pydantic)  │  │  (Registry)  │  │  (Provider)  │  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘  │          │
└──────────────────────────────────────────────────────────────────┘
```

**Key Principle:** The application is event-driven. Every action produces events. Renderers, loggers, and metrics all subscribe to the event bus. The agent never prints directly — it emits events.

---

## 2. Folder Structure

```
omega/
├── __init__.py
├── __main__.py              # python -m omega
├── main.py                  # Entry point → mode router
│
├── core/                    # No dependencies on other omega modules
│   ├── __init__.py
│   ├── events.py            # Event types (dataclasses)
│   ├── bus.py               # Event bus (pub/sub)
│   ├── session.py           # Session object (state container)
│   ├── config.py            # Pydantic config models
│   ├── exceptions.py        # Centralized exception hierarchy
│   └── types.py             # Shared type aliases, protocols
│
├── agent/                   # LLM interaction logic
│   ├── __init__.py
│   ├── pipeline.py          # Agent loop (orchestrates LLM + tools)
│   ├── provider.py          # LLM provider abstraction
│   ├── memory.py            # Conversation memory
│   └── context.py           # Context window management
│
├── cli/                     # Terminal interface layer
│   ├── __init__.py
│   ├── app.py               # Async REPL (PromptSession + asyncio)
│   ├── renderer.py          # RichRenderer (subscribes to events)
│   ├── components/          # Reusable Rich UI widgets
│   │   ├── message.py       # MessageView
│   │   ├── panel.py         # PanelView
│   │   ├── tool.py          # ToolView
│   │   ├── status.py        # StatusView
│   │   ├── progress.py      # ProgressView
│   │   ├── banner.py        # BannerView
│   │   └── error.py         # ErrorView
│   └── commands/            # Slash command implementations
│       ├── __init__.py
│       ├── registry.py      # Command registry
│       ├── help.py          # /help
│       ├── clear.py         # /clear
│       ├── model.py         # /model
│       ├── history.py       # /history
│       ├── tools.py         # /tools
│       ├── config.py        # /config
│       ├── session.py       # /reset, /save, /load
│       └── exit.py          # /exit, /quit
│
├── tools/                   # Tool definitions
│   ├── __init__.py
│   ├── registry.py          # Tool registry
│   ├── base.py              # BaseTool abstract class
│   ├── filesystem.py        # read/write/search files
│   ├── shell.py             # command execution
│   └── web.py               # web fetch/search
│
├── plugins/                 # Third-party plugin support
│   ├── __init__.py
│   ├── loader.py            # Plugin discovery & loading
│   ├── hooks.py             # Plugin hook points
│   └── examples/            # Example plugins
│
├── renderers/               # Alternative renderers for future UIs
│   ├── __init__.py
│   ├── rich_renderer.py     # Current terminal renderer
│   ├── plain_renderer.py    # For testing / scripting
│   └── json_renderer.py     # For JSON output mode
│
├── logging/                 # Structured logging
│   ├── __init__.py
│   ├── setup.py             # Logger configuration
│   ├── handlers.py          # File + terminal handlers
│   └── formats.py           # Log format definitions
│
├── config/                  # Configuration files
│   ├── default.yaml
│   └── schema.json
│
└── logs/                    # Log output directory
    ├── latest.log
    └── debug.log
```

**Why this is better than the current flat structure:**
- `core/` has zero dependencies on other modules — independently testable
- `cli/` and `renderers/` are swappable without touching agent logic
- `plugins/` is a directory; plugins auto-register on import
- `events.py` in `core/` defines the contract everything shares

---

## 3. Core Abstractions

### 3.1 Event System (`core/events.py` + `core/bus.py`)

```python
# core/events.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class EventPriority(Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class Event:
    """Base event — all events inherit from this."""
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL


@dataclass
class UserMessage(Event):
    content: str


@dataclass
class AssistantMessageStart(Event):
    """Fired when the LLM begins generating."""


@dataclass
class AssistantToken(Event):
    """Fired for each streaming token from the LLM."""
    token: str


@dataclass
class AssistantMessageEnd(Event):
    """Fired when the assistant completes its response."""
    full_content: str


@dataclass
class ToolStarted(Event):
    name: str
    args: dict[str, Any]


@dataclass
class ToolProgress(Event):
    name: str
    message: str


@dataclass
class ToolFinished(Event):
    name: str
    duration_ms: int
    success: bool


@dataclass
class ToolOutput(Event):
    name: str
    content: str
    truncated: bool = False


@dataclass
class SystemMessage(Event):
    content: str
    style: str = "dim"  # dim, info, success, warning


@dataclass
class Error(Event):
    message: str
    exception: Optional[Exception] = None
    recoverable: bool = False


@dataclass
class Status(Event):
    text: str
    spinner: bool = True


@dataclass
class Progress(Event):
    current: int
    total: int
    label: str = ""
```

```python
# core/bus.py
import asyncio
import logging
from collections import defaultdict
from typing import Callable, Coroutine

from omega.core.events import Event, EventPriority

Handler = Callable[[Event], Coroutine[None, None, None]]


class EventBus:
    """Async pub/sub event bus.

    Renderers, loggers, and metrics subscribe to events.
    The agent emits events. Zero direct coupling.
    """

    def __init__(self):
        self._subscribers: dict[type[Event], list[Handler]] = defaultdict(list)
        self._logger = logging.getLogger("omega.bus")

    def subscribe(self, event_type: type[Event], handler: Handler) -> None:
        """Register a handler for an event type."""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type[Event], handler: Handler) -> None:
        """Remove a handler."""
        self._subscribers[event_type].remove(handler)

    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers."""
        handlers = self._subscribers.get(type(event), [])
        if not handlers:
            return
        # Sort by priority: HIGH first
        handlers_sorted = sorted(handlers, key=lambda h: event.priority.value)
        for handler in handlers_sorted:
            try:
                await handler(event)
            except Exception:
                self._logger.exception(f"Handler {handler.__name__} failed for {type(event).__name__}")
```

**Why event bus is better than direct patching:**
- Current: agent calls `cli.print_info()` → we monkey-patch `cli` module to redirect
- New: agent calls `bus.emit(SystemMessage(...))` → renderer receives it → prints
- Zero monkey-patching needed. Clear contract. Testable in isolation.

---

### 3.2 Session (`core/session.py`)

```python
# core/session.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from omega.core.config import Config
from omega.agent.memory import ConversationMemory


@dataclass
class Session:
    """Immutable-ish state container — injected everywhere.

    NOT global. Created at startup, passed through constructors.
    """

    config: Config
    model_name: str
    memory: ConversationMemory = field(default_factory=ConversationMemory)
    started_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    tool_count: int = 0
    current_user_input: str = ""
    current_response: str = ""
    running: bool = True
```

**Why session is better than scattered state:**
- Current: `self.model_name`, `self.message_count`, `self.running` scattered across classes
- New: one session object injected everywhere. Easy to snapshot, save, load.

---

### 3.3 Renderer Abstraction (`renderers/__init__.py`)

```python
# renderers/__init__.py
from abc import ABC, abstractmethod
from omega.core.events import (
    UserMessage, AssistantToken, AssistantMessageStart, AssistantMessageEnd,
    ToolStarted, ToolProgress, ToolFinished, ToolOutput,
    SystemMessage, Error, Status, Progress,
)


class Renderer(ABC):
    """Abstract renderer — every UI must implement this.

    Methods are called by the event bus. Each method is a visual handler.
    """

    @abstractmethod
    async def on_user_message(self, event: UserMessage) -> None: ...

    @abstractmethod
    async def on_assistant_start(self, event: AssistantMessageStart) -> None: ...

    @abstractmethod
    async def on_assistant_token(self, event: AssistantToken) -> None: ...

    @abstractmethod
    async def on_assistant_end(self, event: AssistantMessageEnd) -> None: ...

    @abstractmethod
    async def on_tool_started(self, event: ToolStarted) -> None: ...

    @abstractmethod
    async def on_tool_progress(self, event: ToolProgress) -> None: ...

    @abstractmethod
    async def on_tool_finished(self, event: ToolFinished) -> None: ...

    @abstractmethod
    async def on_tool_output(self, event: ToolOutput) -> None: ...

    @abstractmethod
    async def on_system_message(self, event: SystemMessage) -> None: ...

    @abstractmethod
    async def on_error(self, event: Error) -> None: ...

    @abstractmethod
    async def on_status(self, event: Status) -> None: ...

    @abstractmethod
    async def on_progress(self, event: Progress) -> None: ...
```

**Why renderer abstraction is better:**
- Current: `cli.py` functions called directly, only text output possible
- New: implement `PlainRenderer` for tests, `JsonRenderer` for API mode, `WebRenderer` for web UI. No agent code changes.

---

### 3.4 RichRenderer Implementation (`renderers/rich_renderer.py`)

```python
# renderers/rich_renderer.py
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live

from renderers import Renderer
from omega.core.events import (
    UserMessage, AssistantToken, AssistantMessageStart, AssistantMessageEnd,
    ToolStarted, ToolProgress, ToolFinished, ToolOutput,
    SystemMessage, Error, Status, Progress,
)


class RichRenderer(Renderer):
    """Terminal renderer using rich — current default UI."""

    CLAY = "#d97757"

    def __init__(self):
        self.console = Console(force_terminal=True, color_system="truecolor")
        self._buffer = ""
        self._tool_buffer = ""

    async def on_user_message(self, event: UserMessage) -> None:
        self.console.print()
        self.console.print(f"[bold {self.CLAY}]┃ You[/]")
        self.console.print(f"  {event.content}")

    async def on_assistant_start(self, event: AssistantMessageStart) -> None:
        self.console.print(f"[bold {self.CLAY}]┃ OMEGA[/]")
        self._buffer = ""

    async def on_assistant_token(self, event: AssistantToken) -> None:
        self._buffer += event.token
        self.console.print(event.token, end="")

    async def on_assistant_end(self, event: AssistantMessageEnd) -> None:
        self.console.print()

    async def on_tool_started(self, event: ToolStarted) -> None:
        self.console.print(f"  [dim]→ {event.name}(...)[/]")

    async def on_tool_progress(self, event: ToolProgress) -> None:
        self.console.print(f"    [dim]{event.message}[/]")

    async def on_tool_finished(self, event: ToolFinished) -> None:
        icon = "✓" if event.success else "✖"
        color = "green" if event.success else "red"
        self.console.print(f"  [{color}]{icon}[/] [dim]({event.duration_ms}ms)[/]")

    async def on_tool_output(self, event: ToolOutput) -> None:
        if event.content:
            content = event.content[:500]
            suffix = "..." if event.truncated else ""
            self.console.print(f"    [dim]{content}{suffix}[/]")

    async def on_system_message(self, event: SystemMessage) -> None:
        self.console.print(f"[{event.style}]{event.content}[/]")

    async def on_error(self, event: Error) -> None:
        self.console.print(Panel(
            event.message,
            title="[red]ERROR[/]",
            border_style="red",
        ))

    async def on_status(self, event: Status) -> None:
        # Overwritten by prompt — shown between turns
        pass

    async def on_progress(self, event: Progress) -> None:
        bar_len = 20
        filled = int(bar_len * event.current / event.total)
        bar = "█" * filled + "░" * (bar_len - filled)
        label = f" {event.label}" if event.label else ""
        self.console.print(f"  [dim]{bar} {event.current}/{event.total}{label}[/]")
```

**Why separate components for each event type:**
- Each handler is independently testable
- RichRenderer can be replaced with TextualRenderer without touching agent
- Components (`MessageView`, `ToolView`, etc.) can be extracted from the renderer

---

### 3.5 Command System (`cli/commands/`)

```python
# cli/commands/registry.py
from abc import ABC, abstractmethod
from typing import Protocol

from omega.core.events import EventBus
from omega.core.session import Session


class Command(ABC):
    """A single slash command — independently testable."""

    name: str  # e.g. "help"
    aliases: list[str] = []
    description: str = ""

    @abstractmethod
    async def execute(self, args: str, session: Session, bus: EventBus) -> None: ...


class CommandRegistry:
    """Holds all commands. Discovered automatically via plugin-style imports."""

    def __init__(self):
        self._commands: dict[str, Command] = {}

    def register(self, cmd: Command) -> None:
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd

    def get(self, name: str) -> Command | None:
        return self._commands.get(name.lstrip("/"))

    async def execute(self, cmd_line: str, session: Session, bus: EventBus) -> bool:
        """Execute a slash command. Returns False if not found."""
        parts = cmd_line.strip().split(maxsplit=1)
        raw_cmd = parts[0] if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        cmd = self.get(raw_cmd)
        if cmd is None:
            return False
        await cmd.execute(args, session, bus)
        return True
```

```python
# cli/commands/help.py
from rich.panel import Panel

from cli.commands.registry import Command
from omega.core.session import Session
from omega.core.events import EventBus, SystemMessage
from cli.commands.registry import CommandRegistry


class HelpCommand(Command):
    name = "help"
    aliases = ["h"]
    description = "Show available commands"

    def __init__(self, registry: CommandRegistry):
        self.registry = registry

    async def execute(self, args: str, session: Session, bus: EventBus) -> None:
        lines = ["[bold]Commands[/]\n"]
        for cmd in self.registry._commands.values():
            if cmd.name not in lines:
                lines.append(f"  [bold]/{cmd.name}[/]  {cmd.description}")
        unique = dict.fromkeys(lines)
        await bus.emit(SystemMessage("\n".join(unique), style="info"))
```

**Why command classes are better:**
- Current: `_handle_slash_command()` with a giant `if/elif` chain
- New: each command is a file, a class, independently testable
- New commands added by creating a file and registering it — zero routing changes

---

### 3.6 Plugin System (`plugins/loader.py`)

```python
# plugins/loader.py
import importlib
import pkgutil
import logging
from pathlib import Path

logger = logging.getLogger("omega.plugins")


class PluginHook:
    """Shared lifecycle hooks for plugins."""

    on_startup = []
    on_shutdown = []
    on_command = []
    on_event = []

    @classmethod
    def register_startup(cls, fn):
        cls.on_startup.append(fn)
        return fn

    @classmethod
    def register_command(cls, name, aliases=None, description=""):
        """Decorator: mark a function as a slash command handler."""
        def wrapper(fn):
            cls.on_command.append({"name": name, "aliases": aliases or [], "description": description, "handler": fn})
            return fn
        return wrapper


def discover_plugins(plugin_dir: str | None = None):
    """Auto-discover and load plugins from the plugins directory."""
    if plugin_dir is None:
        plugin_dir = str(Path(__file__).parent.parent / "plugins")

    plugin_path = Path(plugin_dir)
    if not plugin_path.exists():
        logger.info("No plugins directory at %s", plugin_dir)
        return

    # Add to sys.path
    import sys
    if str(plugin_path.parent) not in sys.path:
        sys.path.insert(0, str(plugin_path.parent))

    for module in pkgutil.iter_modules([plugin_dir]):
        try:
            importlib.import_module(f"plugins.{module.name}")
            logger.info("Loaded plugin: %s", module.name)
        except Exception:
            logger.exception("Failed to load plugin: %s", module.name)
```

```python
# plugins/github.py (example)
from plugins.loader import PluginHook, discover_plugins


@PluginHook.register_command("github", aliases=["gh"], description="GitHub operations")
async def handle_github(args: str):
    # Plugin registers itself — zero boilerplate
    print(f"GitHub: {args}")
```

**Why plugin system is better:**
- Current: no plugin support
- New: drop a `.py` file in `plugins/`, it auto-loads and registers
- Hooks for startup, shutdown, commands, and events

---

## 4. Event Flow Diagrams

### 4.1 Normal Message Flow

```
User types "hello"
       │
       ▼
PromptSession.prompt_async()
       │
       ▼
CLI App receives input
       │
       ├── starts with "/" → CommandRegistry.execute()
       │                        │
       │                        ▼
       │                    Command.execute() → EventBus.emit(SystemMessage|Error)
       │
       └── normal text
            │
            ▼
       EventBus.emit(UserMessage(content="hello"))
            │
            ▼
       RichRenderer.on_user_message()
            │  prints: "┃ You\n  hello"
            │
            ▼
       EventBus.emit(AssistantMessageStart())
            │
            ▼
       RichRenderer.on_assistant_start()
            │  prints: "┃ OMEGA"
            │
            ▼
       Agent.run_once(user_input)
            │
            ├── LLM streams tokens
            │       │
            │       ▼
            │   EventBus.emit(AssistantToken(token="Hello"))
            │       │
            │       ▼
            │   RichRenderer.on_assistant_token()
            │       │  prints: "Hello" (no newline)
            │       │
            ├── LLM calls tool
            │       │
            │       ▼
            │   EventBus.emit(ToolStarted(name="read_file", args={path:...}))
            │       │
            │       ▼
            │   RichRenderer.on_tool_started()
            │       │  prints: "  → read_file(...)"
            │       │
            │   EventBus.emit(ToolProgress(name="read_file", message="Reading..."))
            │       │
            │       ▼
            │   RichRenderer.on_tool_progress()
            │       │  prints: "    Reading..."
            │       │
            │   EventBus.emit(ToolFinished(name="read_file", duration_ms=150, success=True))
            │       │
            │       ▼
            │   RichRenderer.on_tool_finished()
            │       │  prints: "  ✓ (150ms)"
            │       │
            ├── LLM continues streaming
            │
            ▼
       EventBus.emit(AssistantMessageEnd(full_content="Hello! How can I help?"))
            │
            ▼
       RichRenderer.on_assistant_end()
            │  prints: newline
            │
            ▼
       Prompt returns → loop continues
```

### 4.2 Error Event Flow

```
Agent pipeline raises ValueError("Invalid API key")
       │
       ▼
Agent catches → EventBus.emit(Error(message="Invalid API key",
                                     exception=e,
                                     recoverable=True))
       │
       ▼
RichRenderer.on_error()
       │  prints: Panel("Invalid API key", title="ERROR", border_style="red")
       │
       ▼
LoggerHandler.on_error()
       │  writes: ERROR 2026-07-10 20:00:00 Invalid API key
       │
       ▼
Session continues (recoverable=True) → prompt returns
```

---

## 5. Data Flow Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Config   │────▶│  Session │────▶│  Agent   │────▶│   LLM    │
│ (YAML)   │     │ (state)  │     │(pipeline)│     │Provider  │
└──────────┘     └──────────┘     └────┬─────┘     └──────────┘
                                       │
                          ┌────────────┴────────────┐
                          │                         │
                    ┌─────▼─────┐           ┌───────▼──────┐
                    │ Command   │           │    Tools     │
                    │ Registry  │           │  (registry)  │
                    └───────────┘           └───────┬──────┘
                                                    │
                          ┌─────────────────────────┼─────────┐
                          │                         │         │
                    ┌─────▼─────┐           ┌───────▼──────┐  │
                    │  Event    │◀──────────│  Tool Exec   │  │
                    │   Bus     │           └──────────────┘  │
                    └─────┬─────┘                             │
                          │                                   │
              ┌───────────┼───────────┐                       │
              │           │           │                       │
        ┌─────▼────┐ ┌───▼───┐ ┌─────▼────┐                  │
        │ Renderer │ │Logger │ │ Metrics  │                  │
        │  (Rich)  │ │(file) │ │ (stats)  │                  │
        └──────────┘ └───────┘ └──────────┘                  │
                                                              │
        Data flows:                                           │
        ──▶ User input path                                    │
        ──▶ Event path                                         │
        ──▶ LLM/Tool path                                      │
                                                               │
        State is in Session.                                   │
        Control flow is in EventBus (pub/sub).                 │
        Output is in Renderer.                                 │
        Logic is in Agent + Tools.                             │
```

---

## 6. Class Responsibilities

| Class | File | Responsibility |
|-------|------|---------------|
| `EventBus` | `core/bus.py` | Pub/sub dispatch, subscriber management |
| `Session` | `core/session.py` | Immutable state container, DI root |
| `Config` | `core/config.py` | Typed config (Pydantic/dataclass) |
| `Event` | `core/events.py` | Base event (all typed events inherit) |
| `App` | `cli/app.py` | Async REPL loop, PromptSession management |
| `RichRenderer` | `renderers/rich_renderer.py` | Handles events → rich terminal output |
| `PlainRenderer` | `renderers/plain_renderer.py` | Text-only for tests |
| `JsonRenderer` | `renderers/json_renderer.py` | JSON output for API mode |
| `Agent` | `agent/pipeline.py` | Orchestrates LLM + tool calls |
| `LLMProvider` | `agent/provider.py` | Abstract LLM interface (OpenAI, Anthropic, etc.) |
| `ConversationMemory` | `agent/memory.py` | Stores message history, manages context |
| `CommandRegistry` | `cli/commands/registry.py` | Maps names → Command instances |
| `Command` | `cli/commands/registry.py` | Base class for slash commands |
| `ToolRegistry` | `tools/registry.py` | Maps names → Tool instances |
| `BaseTool` | `tools/base.py` | Abstract tool with execute() |
| `PluginLoader` | `plugins/loader.py` | Discovers and loads plugins |
| `LogSetup` | `logging/setup.py` | Configures file + terminal logging |

---

## 7. Dependency Injection Diagram

```
main.py
   │
   ▼
   Config ─────────────────────┐
   │                           │
   ▼                           │
   Session(config, model)      │
   │        │                  │
   │        ▼                  │
   │   EventBus ───────────────┤
   │        │                  │
   │        ├── RichRenderer(bus)   subscribe(bus)
   │        ├── Logger(bus)         subscribe(bus)
   │        └── Metrics(bus)        subscribe(bus)
   │
   │   AgentPipeline(session, bus, llm_provider, tool_registry)
   │        │
   │        ├── LLMProvider(session, bus)       ← emits AssistantToken events
   │        └── ToolRegistry(session, bus)      ← emits ToolStarted/Finished events
   │                │
   │                ├── ReadFileTool(session)
   │                ├── ShellTool(session)
   │                └── WebTool(session)
   │
   │   CommandRegistry(session, bus)
   │        │
   │        ├── HelpCommand(registry)
   │        ├── ClearCommand()
   │        └── ExitCommand(bus)
   │
   ▼
App(session, bus, agent_pipeline, command_registry)
   │
   ├── PromptSession(prompt_async)
   ├── receives input
   │     ├── "/cmd" → CommandRegistry.execute()
   │     └── normal → AgentPipeline.run(input)
   │
   └── app.run_async()
```

**Key rule:** No class imports another class directly. Everything is injected via constructors. This makes every component independently testable.

---

## 8. Migration Plan

### Phase 1: Core Abstractions (1-2 days)

1. Create `omega/core/` directory
2. Implement `events.py` — all event dataclasses
3. Implement `bus.py` — async EventBus
4. Implement `session.py` — Session dataclass
5. Implement `config.py` — typed Config models
6. Write unit tests for all core components

**No changes to existing code.** Just create new files alongside the old ones.

### Phase 2: Renderer Layer (1 day)

1. Create `renderers/` directory
2. Implement `Renderer` abstract base class
3. Implement `RichRenderer` (replicates current output behavior)
4. Implement `PlainRenderer` (for tests)
5. Test: emit events → verify renderer output

### Phase 3: Agent Refactor (2-3 days)

1. Create `agent/` directory
2. Move `Memory` into `agent/memory.py`
3. Create `LLMProvider` abstraction (wraps current `self.llm.chat()`)
4. Create `AgentPipeline` that:
   - Emits events instead of calling `cli.print_*` functions
   - Takes `EventBus` + `Session` via constructor
5. Add `run_once()` to pipeline

### Phase 4: CLI Refactor (1 day)

1. Create `cli/` directory
2. Implement `App` with `PromptSession` + asyncio loop
3. Implement `CommandRegistry` + all slash commands
4. Replace `main.py` mode routing with new App

### Phase 5: Remove Old Code (1 day)

1. Verify the new code handles all modes (--version, --diagnose, --team, etc.)
2. Delete `omega_tui.py`, old `cli.py` functions
3. Clean up `main.py` — keep only mode router
4. Run full integration test

### Phase 6: Plugin System & Polish (1 day)

1. Implement plugin loader
2. Add logging setup
3. Add testing infrastructure
4. Create example plugins

---

## 9. Performance Improvements

| Issue | Current | Improvement |
|-------|---------|-------------|
| Agent blocks UI | Single thread, agent blocks prompt | `asyncio.to_thread()` or `run_in_executor()` |
| No streaming visualization | All output at once | `AssistantToken` events → incremental print |
| Tools block UI | Tools printed after completion | `ToolStarted`/`ToolProgress`/`ToolFinished` events |
| History grows unbounded | No context management | `ConversationMemory.trim()` with token budget |
| Import chains | Circular imports | Core modules have zero internal deps |

---

## 10. Extensibility Improvements

| Feature | How the architecture enables it |
|---------|--------------------------------|
| New UI (Textual, Web) | Implement `Renderer` interface, plug into `EventBus` |
| New LLM provider | Implement `LLMProvider` interface |
| New tool | Extend `BaseTool`, register in `ToolRegistry` |
| New command | Create file in `cli/commands/`, register in `CommandRegistry` |
| Plugin | Drop `.py` in `plugins/`, auto-discovered |
| Multi-agent | Spawn multiple `AgentPipeline` instances, shared `Session` |
| WebSocket output | `WebRenderer` subscribes to same `EventBus` |
| Voice interface | Separate `VoiceRenderer` + `STT/TTS` module |

---

## 11. Code Quality Improvements

| Practice | Current | New |
|----------|---------|-----|
| Type hints | Partial | Full mypy compliance |
| Testing | Manual | Each class unit-testable via dependency injection |
| Logging | `print()`  | `logging` module with file handlers |
| Error handling | `try/except` scattered | Centralized `Error` events + exception hierarchy |
| Configuration | Raw dict/json | Pydantic/dataclass validation |
| Separation of concerns | Monolithic `omega_tui.py` | `core/` + `cli/` + `agent/` + `renderers/` |

---

## 12. Example: End-to-End Flow Code

```python
# main.py (simplified new version)
import asyncio
from omega.core.config import Config
from omega.core.session import Session
from omega.core.bus import EventBus
from omega.renderers.rich_renderer import RichRenderer
from omega.agent.pipeline import AgentPipeline
from omega.agent.provider import LLMProvider
from omega.tools.registry import ToolRegistry
from omega.cli.commands.registry import CommandRegistry
from omega.cli.commands.help import HelpCommand
from omega.cli.commands.exit import ExitCommand
from omega.cli.commands.clear import ClearCommand
from omega.cli.app import App


async def main():
    # 1. Config
    config = Config.load()
    
    # 2. Core services
    bus = EventBus()
    session = Session(config=config, model_name=config.model)
    
    # 3. Tooling
    tool_registry = ToolRegistry()
    tool_registry.autodiscover()
    
    # 4. Agent
    llm = LLMProvider.from_config(config)
    agent = AgentPipeline(session=session, bus=bus, llm=llm, tools=tool_registry)
    
    # 5. Renderers (subscribe to events)
    renderer = RichRenderer()
    for event_type, handler in renderer.handlers():
        bus.subscribe(event_type, handler)
    
    # 6. Commands
    cmd_registry = CommandRegistry()
    cmd_registry.register(HelpCommand(cmd_registry))
    cmd_registry.register(ExitCommand(bus))
    cmd_registry.register(ClearCommand())
    
    # 7. Run
    app = App(session=session, bus=bus, agent=agent, commands=cmd_registry)
    await app.run_async()
```

---

## 13. Summary of Decisions

| Decision | Why better than current |
|----------|------------------------|
| EventBus instead of patched `cli.*` | No monkey-patching. Every output is an event. Testable. Subscribable by multiple receivers (renderer + logger + metrics). |
| Renderer ABC instead of hardcoded `Console.print()` | Swap terminal for web, JSON, tests without touching agent. The agent emits events — it doesn't care what consumes them. |
| Command classes instead of `if/elif` chain | Each command is a file. New commands added without modifying existing code. Each command has unit tests. |
| Dependency injection instead of `import` | Every component receives its dependencies via constructor. No hidden imports. Test doubles are trivial. |
| `Session` dataclass instead of scattered state | One place for all runtime state. Can snapshot, save, resume. Inject once, pass everywhere. |
| `core/` separation | Zero-dependency core = independently testable. Core can be extracted as a library. |
| Async-first (`asyncio`) | Non-blocking I/O, native streaming, cancel support, concurrent tool execution. |
| Plugin system | Third-party functionality without modifying OMEGA source. Drop-in `.py` files. |
| Structured logging | Separate terminal output from debug logs. Searchable, rotatable, persistable. |
| Typed events (Pydantic/dataclass) | IDE autocompletion, static analysis, validation. |
