"""
Ω OMEGA API Gateway — REST + WebSocket service entry point (§384)

FastAPI application with versioned routes, auth middleware,
CORS, rate limiting, and structured error handling.
"""

from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.api.routes import health, chat, models
from services.api.middleware import AuthMiddleware, RequestLoggingMiddleware, RateLimitMiddleware


# ── Config ─────────────────────────────────────────────────────────────────

API_VERSION = "1.0.0"
APP_NAME = "OMEGA API Gateway"


# ── App Factory ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Startup and shutdown lifecycle."""
    # Startup
    app.state.start_time = time.time()
    app.state.request_id = uuid.uuid4().hex[:8]
    print(f"[{APP_NAME}] v{API_VERSION} — starting (instance {app.state.request_id})")
    yield
    # Shutdown
    elapsed = time.time() - app.state.start_time
    print(f"[{APP_NAME}] v{API_VERSION} — shutdown after {elapsed:.1f}s")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=APP_NAME,
        version=API_VERSION,
        description="OMEGA AI Platform — Multi-user, multi-agent API gateway",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Middleware (order matters — outermost first) ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuthMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # ── Routers ──
    app.include_router(health.router, prefix="/health", tags=["Health"])
    app.include_router(models.router, prefix="/v1/models", tags=["Models"])
    app.include_router(chat.router, prefix="/v1/chat", tags=["Chat"])

    # ── Global Exception Handler ──
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    # ── Root ──
    @app.get("/")
    async def root():
        return {
            "service": APP_NAME,
            "version": API_VERSION,
            "status": "operational",
        }

    return app


# ── CLI Entry ──────────────────────────────────────────────────────────────

app = create_app()


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(
        "services.api.__init__:app",
        host=host,
        port=port,
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
    )
