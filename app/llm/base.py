from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.chat import ChatCompletionRequest, ChatCompletionResponse


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None
