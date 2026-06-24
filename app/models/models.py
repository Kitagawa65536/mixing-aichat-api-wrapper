from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    object: Literal["model"] = "model"
    owned_by: str = "gateway"


class ModelListResponse(BaseModel):
    object: Literal["list"] = "list"
    data: list[ModelInfo]
