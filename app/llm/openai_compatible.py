from __future__ import annotations

from typing import Any

import httpx
from pydantic import ValidationError

from app.config.settings import EndpointConfig
from app.llm.base import LLMClient
from app.models.chat import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Usage,
)


class LLMConnectionError(Exception):
    def __init__(self, role_name: str, message: str) -> None:
        self.role_name = role_name
        super().__init__(message)


class OpenAICompatibleClient(LLMClient):
    def __init__(
        self,
        role_name: str,
        endpoint: EndpointConfig,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.role_name = role_name
        self.endpoint = endpoint
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            timeout=endpoint.request_timeout_seconds,
        )

    async def generate(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        payload = self._build_payload(request)
        headers = self._build_headers()

        try:
            response = await self._http_client.post(
                self._chat_completions_url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return self._parse_response(response.json())
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise LLMConnectionError(
                self.role_name,
                f"{self.role_name} endpoint returned HTTP {exc.response.status_code} "
                f"at {self._chat_completions_url}: {body}",
            ) from exc
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            raise LLMConnectionError(
                self.role_name,
                f"{self.role_name} endpoint request failed at {self._chat_completions_url}: {exc}",
            ) from exc

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    @property
    def _chat_completions_url(self) -> str:
        return f"{self.endpoint.api_base}/chat/completions"

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.endpoint.api_key:
            headers["Authorization"] = f"Bearer {self.endpoint.api_key}"
        return headers

    def _build_payload(self, request: ChatCompletionRequest) -> dict[str, Any]:
        payload = request.model_dump(exclude_none=True)
        payload.update(self.endpoint.extra_body)
        payload["model"] = self.endpoint.model
        payload["stream"] = False
        return payload

    def _parse_response(self, raw_response: dict[str, Any]) -> ChatCompletionResponse:
        if "choices" in raw_response:
            return self._strip_reasoning_content(
                ChatCompletionResponse.model_validate(raw_response)
            )

        content = str(raw_response.get("content", ""))
        return ChatCompletionResponse(
            model=self.endpoint.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason=raw_response.get("finish_reason"),
                )
            ],
            usage=Usage(),
        )

    def _strip_reasoning_content(
        self,
        response: ChatCompletionResponse,
    ) -> ChatCompletionResponse:
        choices = []
        changed = False
        for choice in response.choices:
            if choice.message.reasoning_content is None:
                choices.append(choice)
                continue
            message = choice.message.model_copy(update={"reasoning_content": None})
            choices.append(choice.model_copy(update={"message": message}))
            changed = True
        if not changed:
            return response
        return response.model_copy(update={"choices": choices})
