"""
Ω OMEGA Error Catalog — structured, standardized error codes.

Usage:
    from packages.errors import (
        OmegaException,
        AUTH_REQUIRED,
        AI_PROVIDER_UNAVAILABLE,
        lookup,
        format_error,
    )

    # Raise with context
    raise OmegaException(AUTH_REQUIRED, details="Token expired")

    # Look up by code string
    err = lookup("REPO_001")

    # Format for display
    print(format_error(REPO_NOT_FOUND, request_id="req-abc123"))
"""

from .catalog import (
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
    # Utilities
    ErrorCode,
    format_error,
    list_codes,
    lookup,
)

from .handlers import (
    OmegaException,
    ai_error,
    auth_error,
    deploy_error,
    format_api_response,
    http_status_from_error,
    repo_error,
    task_error,
)

__all__ = [
    # Auth
    "AUTH_INVALID_CREDENTIALS",
    "AUTH_SESSION_EXPIRED",
    "AUTH_REQUIRED",
    # Repository
    "REPO_NOT_FOUND",
    "REPO_NOT_INDEXED",
    "REPO_SYNC_FAILED",
    # AI Runtime
    "AI_PROVIDER_UNAVAILABLE",
    "AI_CONTEXT_TOO_LARGE",
    "AI_TOOL_EXECUTION_FAILED",
    "AI_STREAMING_INTERRUPTED",
    # Tasks
    "TASK_NOT_FOUND",
    "TASK_EXECUTION_CANCELLED",
    "TASK_VALIDATION_FAILED",
    # Deployment
    "DEPLOY_FAILED",
    "DEPLOY_ROLLBACK_COMPLETED",
    "DEPLOY_ENV_MISCONFIGURED",
    # Types
    "ErrorCode",
    "OmegaException",
    # Utilities
    "ai_error",
    "auth_error",
    "deploy_error",
    "format_api_response",
    "format_error",
    "http_status_from_error",
    "list_codes",
    "lookup",
    "repo_error",
    "task_error",
]
