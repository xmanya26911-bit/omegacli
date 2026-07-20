"""
Ω OMEGA API — Chat completion routes (OpenAI-compatible).
"""

from __future__ import annotations

import json
import time
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field


router = APIRouter()


# ── Request/Response Schemas ───────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # system, user, assistant
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False
    top_p: Optional[float] = 1.0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[dict]
    usage: Optional[dict] = None


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex[:12])

    # Validate model
    from apps.cli.omega.core.config import MODEL_PROVIDERS
    if body.model not in MODEL_PROVIDERS:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "MODEL_NOT_FOUND",
                    "message": f"Model '{body.model}' not available",
                    "request_id": request_id,
                }
            },
        )

    # TODO: Route to actual AI provider via services/ai_runtime
    # For now, return a mock streaming response
    if body.stream:
        return StreamingResponse(
            _mock_stream(body.model, body.messages),
            media_type="text/event-stream",
        )

    # Non-streaming mock response
    response_id = f"chatcmpl-{uuid.uuid4().hex[:16]}"
    return ChatCompletionResponse(
        id=response_id,
        created=int(time.time()),
        model=body.model,
        choices=[
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"Mock response for {body.model}. "
                               f"AI Runtime integration pending.",
                },
                "finish_reason": "stop",
            }
        ],
        usage={
            "prompt_tokens": sum(len(m.content) // 4 for m in body.messages),
            "completion_tokens": 16,
            "total_tokens": sum(len(m.content) // 4 for m in body.messages) + 16,
        },
    )


# ── Mock Streaming ─────────────────────────────────────────────────────────

async def _mock_stream(model: str, messages: list) -> AsyncGenerator[str, None]:
    """Mock SSE streaming response."""
    words = f"Mock streaming response from {model}. ".split()
    response_id = f"chatcmpl-{uuid.uuid4().hex[:16]}"

    for i, word in enumerate(words):
        chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": word + " "},
                    "finish_reason": None if i < len(words) - 1 else "stop",
                }
            ],
        }
        yield f"data: {json.dumps(chunk)}\n\n"

    yield "data: [DONE]\n\n"
