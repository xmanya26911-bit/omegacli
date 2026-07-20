"""Core types and exceptions for OMEGA framework."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Generic, TypeVar

from omega.core.config import Config, ConfigError, AVAILABLE_MODELS, MODEL_PROVIDERS
from packages.errors import OmegaException, lookup as error_lookup

T = TypeVar("T")


# ── Results ──────────────────────────────────────────────────────────────

class ErrorLevel(Enum):
    """Severity levels for tool execution results."""
    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class ToolResult:
    """Standard result container for all tool executions.

    Attributes:
        content: Human-readable output string.
        is_error: Whether the execution failed.
        data: Optional structured data payload.
        error_level: Severity classification.
        execution_time: Wall-clock time in seconds.
        tool_name: Name of the tool that produced this result.
    """
    content: str
    is_error: bool = False
    data: dict[str, Any] | None = None
    error_level: ErrorLevel = ErrorLevel.INFO
    execution_time: float = 0.0
    tool_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __bool__(self) -> bool:
        return not self.is_error

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "is_error": self.is_error,
            "data": self.data,
            "error_level": self.error_level.name,
            "execution_time": self.execution_time,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def error(cls, message: str, tool_name: str = "",
              data: dict[str, Any] | None = None) -> ToolResult:
        return cls(
            content=message,
            is_error=True,
            error_level=ErrorLevel.ERROR,
            tool_name=tool_name,
            data=data,
        )

    @classmethod
    def warning(cls, message: str, tool_name: str = "") -> ToolResult:
        return cls(
            content=message,
            is_error=False,
            error_level=ErrorLevel.WARNING,
            tool_name=tool_name,
        )

    @classmethod
    def from_value(cls, value: Any) -> ToolResult:
        """Create a result from any value, with auto-serialization."""
        if isinstance(value, ToolResult):
            return value
        if isinstance(value, str):
            return cls(content=value)
        try:
            content = json.dumps(value, indent=2, default=str)
            return cls(content=content, data=value if isinstance(value, dict) else None)
        except (TypeError, ValueError):
            return cls(content=str(value))


# ── Exceptions ───────────────────────────────────────────────────────────

class OmegaError(OmegaException):
    """Base exception for all OMEGA errors.

    Backward-compatible wrapper around packages.errors.OmegaException.
    If no ErrorCode is given, falls back to the catalog lookup or UNKNOWN.
    """

    def __init__(self, message: str, code: str | None = None,
                 details: dict[str, Any] | None = None):
        # Try to find a matching catalog code
        catalog_code = error_lookup(code) if code else None
        if catalog_code:
            detail_str = str(details or {}) if details else ""
            super().__init__(catalog_code, details=detail_str)
        else:
            # Fallback: create a synthetic ErrorCode from the message
            from packages.errors import ErrorCode
            fake_code = ErrorCode(
                code=code or "UNKNOWN_ERROR",
                message=message,
                suggestion="Check the system logs for more details.",
                http_status=500,
            )
            super().__init__(fake_code, details=str(details or {}))

    @property
    def message(self) -> str:
        return self.code.message


class ToolExecutionError(OmegaError):
    """Raised when a tool fails during execution."""
    def __init__(self, message: str, tool_name: str = "",
                 code: str = "TOOL_ERROR", details: dict[str, Any] | None = None):
        self.tool_name = tool_name
        super().__init__(message, code=code, details=details)


class ConfigurationError(OmegaError):
    """Raised when system configuration is invalid."""
    def __init__(self, message: str = "", code: str = "CONFIG_ERROR",
                 details: dict[str, Any] | None = None):
        super().__init__(message, code=code, details=details)


class MemoryError(OmegaError):
    """Raised on memory system failures."""
    pass


class ProviderError(OmegaError):
    """Raised when an LLM provider fails."""
    def __init__(self, message: str, provider: str = "",
                 code: str = "PROVIDER_ERROR"):
        self.provider = provider
        super().__init__(message, code=code)


# ── Permission Levels ────────────────────────────────────────────────────

class Permission(Enum):
    """Access control levels for tools and capabilities."""
    ALWAYS = auto()        # No restrictions
    CONFIRM = auto()       # Requires user confirmation
    RESTRICTED = auto()    # Requires explicit configuration
    NEVER = auto()         # Disabled by default, opt-in only
    SANDBOXED = auto()     # Runs in sandboxed environment


# ── Execution Metadata ───────────────────────────────────────────────────

@dataclass
class ExecutionMetadata:
    """Metadata captured during tool execution."""
    tool_name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    success: bool = False
    arguments: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    cpu_time: float = 0.0
    memory_delta: int = 0

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)
