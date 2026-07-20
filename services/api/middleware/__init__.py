"""
Ω OMEGA API — Middleware layer: auth, logging, rate limiting.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


# ── Auth Middleware ─────────────────────────────────────────────────────────

class AuthMiddleware(BaseHTTPMiddleware):
    """API key / Bearer token authentication."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Assign request ID
        request.state.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])

        # Skip auth for health/openapi
        if request.url.path in ("/health", "/health/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Extract API key
        auth_header = request.headers.get("Authorization", "")
        api_key: Optional[str] = None
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        elif auth_header.startswith("ApiKey "):
            api_key = auth_header[7:]

        if not api_key:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "AUTH_001",
                        "message": "Missing or invalid Authorization header",
                        "request_id": request.state.request_id,
                    }
                },
            )

        # TODO: Validate against stored keys (Vercel Blob / DB)
        request.state.api_key = api_key
        request.state.user_id = f"user_{api_key[:8]}"

        return await call_next(request)


# ── Request Logging Middleware ──────────────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status, duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        print(
            f"[API] {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms:.0f}ms) "
            f"[{getattr(request.state, 'request_id', '-')}]"
        )
        return response


# ── Rate Limit Middleware ──────────────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter."""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip for health/docs
        if request.url.path in ("/health", "/health/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        user_id = getattr(request.state, "user_id", "anonymous")
        now = time.time()

        # Clean old entries
        bucket = self._buckets.get(user_id, [])
        cutoff = now - self.window_seconds
        bucket = [t for t in bucket if t > cutoff]

        if len(bucket) >= self.max_requests:
            from fastapi.responses import JSONResponse
            retry_after = int(bucket[0] + self.window_seconds - now)
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "error": {
                        "code": "RATE_LIMIT",
                        "message": f"Rate limit exceeded. Try again in {retry_after}s",
                        "request_id": request.state.request_id,
                    }
                },
            )

        bucket.append(now)
        self._buckets[user_id] = bucket
        return await call_next(request)
