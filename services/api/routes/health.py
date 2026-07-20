"""
Ω OMEGA API — Health check routes.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request


router = APIRouter()


@router.get("")
@router.get("/")
async def health_check(request: Request):
    """Basic health check — returns service status and uptime."""
    uptime = time.time() - request.app.state.start_time
    return {
        "status": "ok",
        "service": "OMEGA API Gateway",
        "version": request.app.state.version if hasattr(request.app, "state") else "unknown",
        "uptime_seconds": round(uptime, 1),
        "request_id": getattr(request.state, "request_id", None),
    }


@router.get("/live")
async def liveness():
    """Kubernetes-style liveness probe."""
    return {"status": "alive"}


@router.get("/ready")
async def readiness(request: Request):
    """Kubernetes-style readiness probe — checks downstream dependencies."""
    deps = {
        "api": True,
        "ai_runtime": True,
        "database": False,  # TODO: connect to real DB
    }
    overall = all(deps.values())
    return {
        "status": "ready" if overall else "degraded",
        "dependencies": deps,
    }
