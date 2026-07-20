"""
Ω OMEGA API — Model listing routes.
"""

from __future__ import annotations

from fastapi import APIRouter

from apps.cli.omega.core.config import MODEL_PROVIDERS


router = APIRouter()


@router.get("")
@router.get("/")
async def list_models():
    """List all available models with metadata."""
    models = []
    for model_id, config in MODEL_PROVIDERS.items():
        models.append({
            "id": model_id,
            "object": "model",
            "created": None,
            "owned_by": config.get("provider", "omega"),
            "permission": [],
            "root": model_id,
        })
    return {
        "object": "list",
        "data": models,
    }


@router.get("/{model_id}")
async def get_model(model_id: str):
    """Get model details by ID."""
    if model_id in MODEL_PROVIDERS:
        config = MODEL_PROVIDERS[model_id]
        return {
            "id": model_id,
            "object": "model",
            "owned_by": config.get("provider", "omega"),
        }
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "MODEL_NOT_FOUND",
                "message": f"Model '{model_id}' not found",
            }
        },
    )
