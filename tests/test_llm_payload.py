from __future__ import annotations

from app.config.settings import EndpointConfig
from app.llm.openai_compatible import OpenAICompatibleClient
from app.models.chat import ChatCompletionRequest


def test_request_extra_fields_are_forwarded_to_upstream_payload() -> None:
    endpoint = EndpointConfig(
        api_base="http://127.0.0.1:1234/v1",
        model="configured-model",
    )
    client = OpenAICompatibleClient("actor", endpoint, http_client=object())
    request = ChatCompletionRequest.model_validate(
        {
            "model": "gateway-model",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
            "temperature": 0.7,
            "seed": 42,
            "response_format": {"type": "json_object"},
            "custom_llama_swap_option": "kept",
        }
    )

    payload = client._build_payload(request)

    assert payload["model"] == "configured-model"
    assert payload["stream"] is False
    assert payload["seed"] == 42
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["custom_llama_swap_option"] == "kept"


def test_endpoint_extra_body_is_forwarded_without_overriding_model_or_stream() -> None:
    endpoint = EndpointConfig(
        api_base="http://127.0.0.1:1234/v1",
        model="configured-model",
        extra_body={
            "model": "ignored-model",
            "stream": True,
            "reasoning_effort": "low",
        },
    )
    client = OpenAICompatibleClient("director", endpoint, http_client=object())
    request = ChatCompletionRequest.model_validate(
        {
            "model": "gateway-model",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        }
    )

    payload = client._build_payload(request)

    assert payload["model"] == "configured-model"
    assert payload["stream"] is False
    assert payload["reasoning_effort"] == "low"


def test_parse_response_strips_reasoning_content_from_upstream_message() -> None:
    endpoint = EndpointConfig(
        api_base="http://127.0.0.1:1234/v1",
        model="configured-model",
    )
    client = OpenAICompatibleClient("actor", endpoint, http_client=object())

    response = client._parse_response(
        {
            "model": "configured-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "visible answer",
                        "reasoning_content": "hidden thinking",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
    )

    assert response.choices[0].message.content == "visible answer"
    assert response.choices[0].message.reasoning_content is None
