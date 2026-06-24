from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


RouteTarget = Literal["actor", "director", "injection"]

JSON_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(?P<body>.*?)\s*```", re.DOTALL)


class RouteDecision(BaseModel):
    route: RouteTarget
    reason: str | None = None
    risk_level: int | None = Field(default=None, ge=1, le=5)
    matched_prompt: str | None = None


def parse_route_decision(content: str | None) -> RouteDecision:
    if content is None:
        raise ValueError("Router response content is empty")

    raw_content = content.strip()
    fence_match = JSON_FENCE_PATTERN.fullmatch(raw_content)
    if fence_match:
        raw_content = fence_match.group("body").strip()

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError("Router response content is not valid JSON") from exc

    try:
        return RouteDecision.model_validate(parsed)
    except ValidationError as exc:
        raise ValueError("Router response JSON does not match route schema") from exc
