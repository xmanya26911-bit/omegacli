"""
Error handler utilities — middleware, formatting, and exception wrappers.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Any, Optional

from .catalog import (
    ErrorCode,
    format_error,
    lookup,
)


# ── OmegaException ───────────────────────────────────────────────────────────

class OmegaException(Exception):
    """
    Standardized exception carrying an ErrorCode.

    Use this in place of raw Exception raises throughout the codebase
    so that every error site produces a traceable, documented error.
    """

    def __init__(
        self,
        code: ErrorCode,
        details: str = "",
        request_id: str = "",
        cause: Optional[Exception] = None,
    ) -> None:
        self.code = code
        self.details = details
        self.request_id = request_id
        self.cause = cause
        super().__init__(str(self))

    def __str__(self) -> str:
        return format_error(self.code, self.request_id, self.details)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict for API responses."""
        d: dict[str, Any] = {
            "error": {
                "code": self.code.code,
                "message": self.code.message,
                "suggestion": self.code.suggestion,
            }
        }
        if self.details:
            d["error"]["details"] = self.details
        if self.request_id:
            d["error"]["request_id"] = self.request_id
        if self.cause:
            d["error"]["cause"] = str(self.cause)
        return d

    def http_status(self) -> int:
        return self.code.http_status


# ── Convenience constructors ─────────────────────────────────────────────────

def auth_error(code: ErrorCode, details: str = "") -> OmegaException:
    """Shortcut for auth errors."""
    return OmegaException(code, details=details)


def repo_error(code: ErrorCode, details: str = "") -> OmegaException:
    """Shortcut for repository errors."""
    return OmegaException(code, details=details)


def ai_error(code: ErrorCode, details: str = "") -> OmegaException:
    """Shortcut for AI runtime errors."""
    return OmegaException(code, details=details)


def task_error(code: ErrorCode, details: str = "") -> OmegaException:
    """Shortcut for task errors."""
    return OmegaException(code, details=details)


def deploy_error(code: ErrorCode, details: str = "") -> OmegaException:
    """Shortcut for deployment errors."""
    return OmegaException(code, details=details)


# ── Middleware Helpers ────────────────────────────────────────────────────────

def format_api_response(error: OmegaException) -> dict[str, Any]:
    """Format an OmegaException into a standard API error response body."""
    return error.to_dict()


def http_status_from_error(error: OmegaException) -> int:
    """Extract the HTTP status code from an OmegaException."""
    return error.http_status()


def traceback_summary(limit: int = 5) -> str:
    """Get a short traceback summary for logging."""
    return "".join(traceback.format_exception(None, None, exc_info=None, limit=limit))
