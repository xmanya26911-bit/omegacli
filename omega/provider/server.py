"""
OmegaCLI Provider Server — REST API server for custom model serving.

Run:
    python -m omega.provider.server

Serves an OpenAI-compatible API at http://localhost:8080/v1
"""

import os
from typing import Any

from omega.provider import OmegaCLIProvider, FREE_MODELS

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
except ImportError:
    raise ImportError(
        "Run: pip install fastapi uvicorn"
    )

app = FastAPI(
    title="OmegaCLI Provider",
    description="Custom model provider — 5 free models with API key auth",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

provider = OmegaCLIProvider()


def _extract_api_key(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


# ─── Models ─────────────────────────────────────────────────────────────────


@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": provider.list_models()}


# ─── Chat Completions ────────────────────────────────────────────────────────


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: dict[str, Any]):
    api_key = _extract_api_key(request)
    model = body.get("model", "deepseek-v4-flash-free")
    messages = body.get("messages", [])
    stream = body.get("stream", False)
    temperature = body.get("temperature", 0.7)
    max_tokens = body.get("max_tokens", 4096)

    try:
        response = provider.chat(
            model=model,
            messages=messages,
            api_key=api_key,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))


# ─── API Key Management ─────────────────────────────────────────────────────


@app.post("/v1/api-keys")
async def create_key(label: str = "default"):
    return provider.create_api_key(label)


@app.get("/v1/api-keys")
async def list_keys():
    return {"object": "list", "data": provider.list_api_keys()}


@app.delete("/v1/api-keys/{key}")
async def revoke_key(key: str):
    return provider.revoke_api_key(key)


# ─── Health ─────────────────────────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "ok", "provider": "omegacli", "models": len(FREE_MODELS)}


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    port = int(os.environ.get("OMEGA_PROVIDER_PORT", "8080"))
    host = os.environ.get("OMEGA_PROVIDER_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
