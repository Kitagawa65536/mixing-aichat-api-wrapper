from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.config.settings import AppConfig

os.environ.setdefault("CONFIG_PATH", "config.example.yaml")

from app.main import create_app
from app.models.chat import ChatCompletionResponse


def make_config() -> AppConfig:
    return AppConfig.model_validate(
        {
            "router": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "same-model",
            },
            "actor": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "same-model",
            },
            "formatter": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "formatter-model",
            },
            "director": {
                "api_base": "http://127.0.0.1:1234/v1",
                "model": "director-model",
            },
        }
    )


def test_models_endpoint_returns_deduplicated_configured_models() -> None:
    with TestClient(create_app(make_config())) as client:
        response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json() == {
        "object": "list",
        "data": [
            {"id": "same-model", "object": "model", "owned_by": "gateway"},
            {"id": "formatter-model", "object": "model", "owned_by": "gateway"},
            {"id": "director-model", "object": "model", "owned_by": "gateway"},
        ],
    }


def test_streaming_requests_are_rejected_before_upstream_call() -> None:
    with TestClient(create_app(make_config())) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gateway-model",
                "stream": True,
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Streaming is not supported. Use stream=false."


def test_response_model_accepts_llama_swap_extra_fields() -> None:
    response = ChatCompletionResponse.model_validate(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1780889819,
            "model": "qwen3.5-0.8b",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "ok",
                        "reasoning_content": "",
                        "tool_calls": [],
                    },
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 18,
                "completion_tokens": 2,
                "total_tokens": 20,
                "completion_tokens_details": {"reasoning_tokens": 0},
            },
            "stats": {},
            "system_fingerprint": "qwen3.5-0.8b",
        }
    )

    assert response.choices[0].message.content == "ok"
    assert response.choices[0].message.reasoning_content == ""
    assert response.system_fingerprint == "qwen3.5-0.8b"
