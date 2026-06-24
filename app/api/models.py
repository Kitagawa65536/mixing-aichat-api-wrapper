from __future__ import annotations

from fastapi import APIRouter, Request

from app.config.settings import AppConfig
from app.models.models import ModelInfo, ModelListResponse


router = APIRouter(prefix="/v1")


@router.get("/models", response_model=ModelListResponse)
async def list_models(request: Request) -> ModelListResponse:
    config: AppConfig = request.app.state.config
    model_ids = [
        config.router.model,
        config.actor.model,
        config.formatter.model,
        config.director.model,
    ]

    seen: set[str] = set()
    models: list[ModelInfo] = []
    for model_id in model_ids:
        if model_id in seen:
            continue
        seen.add(model_id)
        models.append(ModelInfo(id=model_id))

    return ModelListResponse(data=models)
