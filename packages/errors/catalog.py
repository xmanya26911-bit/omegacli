"""
OMEGA Error Code Catalog (§397)

Every error includes:
- code:      Standardized identifier (e.g. AUTH_001)
- message:   Human-readable explanation
- suggestion: Suggested next action
- http_status: HTTP status code mapping
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


# ── Error Code Definition ────────────────────────────────────────────────────

@dataclass(frozen=True)
class ErrorCode:
    """A single entry in the error code catalog."""
    code: str
    message: str
    suggestion: str
    http_status: int = 500

    def __repr__(self) -> str:
        return f"[{self.code}] {self.message}"


# ── Authentication (AUTH_00x) ────────────────────────────────────────────────

AUTH_INVALID_CREDENTIALS = ErrorCode(
    code="AUTH_001",
    message="Invalid Credentials",
    suggestion="Check your username and password and try again.",
    http_status=401,
)

AUTH_SESSION_EXPIRED = ErrorCode(
    code="AUTH_002",
    message="Session Expired",
    suggestion="Sign in again to continue.",
    http_status=401,
)

AUTH_REQUIRED = ErrorCode(
    code="AUTH_003",
    message="Authentication Required",
    suggestion="Sign in to access this resource.",
    http_status=401,
)


# ── Repository (REPO_00x) ────────────────────────────────────────────────────

REPO_NOT_FOUND = ErrorCode(
    code="REPO_001",
    message="Repository Not Found",
    suggestion="Verify the repository URL or path and try again.",
    http_status=404,
)

REPO_NOT_INDEXED = ErrorCode(
    code="REPO_002",
    message="Repository Not Indexed",
    suggestion="Run repository indexing first before searching.",
    http_status=400,
)

REPO_SYNC_FAILED = ErrorCode(
    code="REPO_003",
    message="Synchronization Failed",
    suggestion="Check your network connection and try again. If the problem persists, re-clone the repository.",
    http_status=502,
)


# ── AI Runtime (AI_00x) ──────────────────────────────────────────────────────

AI_PROVIDER_UNAVAILABLE = ErrorCode(
    code="AI_001",
    message="Provider Unavailable",
    suggestion="The AI provider is currently unreachable. Try again in a few seconds or switch models.",
    http_status=503,
)

AI_CONTEXT_TOO_LARGE = ErrorCode(
    code="AI_002",
    message="Context Too Large",
    suggestion="Reduce the conversation length or start a new conversation. The current context exceeds the model's limit.",
    http_status=413,
)

AI_TOOL_EXECUTION_FAILED = ErrorCode(
    code="AI_003",
    message="Tool Execution Failed",
    suggestion="The tool encountered an error. Check the tool input and try again.",
    http_status=500,
)

AI_STREAMING_INTERRUPTED = ErrorCode(
    code="AI_004",
    message="Streaming Interrupted",
    suggestion="The response stream was interrupted. Check your connection and try again.",
    http_status=500,
)


# ── Tasks (TASK_00x) ─────────────────────────────────────────────────────────

TASK_NOT_FOUND = ErrorCode(
    code="TASK_001",
    message="Task Not Found",
    suggestion="Verify the task ID and try again.",
    http_status=404,
)

TASK_EXECUTION_CANCELLED = ErrorCode(
    code="TASK_002",
    message="Execution Cancelled",
    suggestion="The task was cancelled. Review the cancellation reason and re-submit if needed.",
    http_status=400,
)

TASK_VALIDATION_FAILED = ErrorCode(
    code="TASK_003",
    message="Validation Failed",
    suggestion="Check the task parameters against the required schema and fix any errors.",
    http_status=422,
)


# ── Deployment (DEPLOY_00x) ──────────────────────────────────────────────────

DEPLOY_FAILED = ErrorCode(
    code="DEPLOY_001",
    message="Deployment Failed",
    suggestion="Check the build logs for errors. Verify your configuration and try again.",
    http_status=500,
)

DEPLOY_ROLLBACK_COMPLETED = ErrorCode(
    code="DEPLOY_002",
    message="Rollback Completed",
    suggestion="The deployment was rolled back to the previous version. Investigate the failure cause before re-deploying.",
    http_status=200,
)

DEPLOY_ENV_MISCONFIGURED = ErrorCode(
    code="DEPLOY_003",
    message="Environment Misconfigured",
    suggestion="Check that all required environment variables are set in the deployment target.",
    http_status=400,
)


# ── Catalog Lookup ───────────────────────────────────────────────────────────

_CATALOG: Dict[str, ErrorCode] = {
    e.code: e
    for e in [
        # Auth
        AUTH_INVALID_CREDENTIALS,
        AUTH_SESSION_EXPIRED,
        AUTH_REQUIRED,
        # Repository
        REPO_NOT_FOUND,
        REPO_NOT_INDEXED,
        REPO_SYNC_FAILED,
        # AI Runtime
        AI_PROVIDER_UNAVAILABLE,
        AI_CONTEXT_TOO_LARGE,
        AI_TOOL_EXECUTION_FAILED,
        AI_STREAMING_INTERRUPTED,
        # Tasks
        TASK_NOT_FOUND,
        TASK_EXECUTION_CANCELLED,
        TASK_VALIDATION_FAILED,
        # Deployment
        DEPLOY_FAILED,
        DEPLOY_ROLLBACK_COMPLETED,
        DEPLOY_ENV_MISCONFIGURED,
    ]
}


def lookup(code: str) -> Optional[ErrorCode]:
    """Look up an error code by its string identifier."""
    return _CATALOG.get(code)


def list_codes(category: Optional[str] = None) -> list[ErrorCode]:
    """List all error codes, optionally filtered by category prefix."""
    if category is None:
        return list(_CATALOG.values())
    prefix = category.upper().rstrip("_") + "_"
    return [e for e in _CATALOG.values() if e.code.startswith(prefix)]


def format_error(code: ErrorCode, request_id: str = "", details: str = "") -> str:
    """Format an error code into a human-readable string."""
    lines = [f"[{code.code}] {code.message}"]
    if details:
        lines.append(f"  Details: {details}")
    lines.append(f"  Suggestion: {code.suggestion}")
    if request_id:
        lines.append(f"  Request ID: {request_id}")
    return "\n".join(lines)
