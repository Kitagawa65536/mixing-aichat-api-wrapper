from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from app.models.chat import ChatCompletionRequest, ChatCompletionResponse


class ChatCompletionEvent(BaseModel):
    route: str
    router_fallback: bool = False
    request: ChatCompletionRequest
    final_response: ChatCompletionResponse
    companion_enabled: bool = False


class ConversationEventSink(Protocol):
    async def record_chat_completion(self, event: ChatCompletionEvent) -> None:
        raise NotImplementedError


class NoopConversationEventSink:
    async def record_chat_completion(self, event: ChatCompletionEvent) -> None:
        return None
