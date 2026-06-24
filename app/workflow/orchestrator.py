from __future__ import annotations

from dataclasses import dataclass
import logging
import random
from collections.abc import Sequence

from app.companion import CompanionContextProvider
from app.config.settings import WorkflowConfig
from app.llm.base import LLMClient
from app.models.chat import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Usage,
)
from app.storage.events import (
    ChatCompletionEvent,
    ConversationEventSink,
    NoopConversationEventSink,
)
from app.storage.injection_guard import InjectionPromptStore
from app.workflow.routing import parse_route_decision


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RouteOutcome:
    route: str
    router_fallback: bool = False
    risk_level: int | None = None
    matched_prompt: str | None = None


class Orchestrator:
    def __init__(
        self,
        actor_client: LLMClient,
        router_client: LLMClient,
        director_client: LLMClient,
        formatter_client: LLMClient,
        workflow_config: WorkflowConfig,
        router_prompt: str,
        director_prompt: str,
        formatter_prompt: str,
        companion_context: str = "",
        companion_context_provider: CompanionContextProvider | None = None,
        event_sink: ConversationEventSink | None = None,
        injection_prompt_store: InjectionPromptStore | None = None,
        injection_fallback_messages: Sequence[str] | None = None,
    ) -> None:
        self._actor_client = actor_client
        self._router_client = router_client
        self._director_client = director_client
        self._formatter_client = formatter_client
        self._workflow_config = workflow_config
        self._router_prompt = router_prompt
        self._director_prompt = director_prompt
        self._formatter_prompt = formatter_prompt
        self._companion_context = companion_context.strip()
        self._companion_context_provider = companion_context_provider
        self._event_sink = event_sink or NoopConversationEventSink()
        self._injection_prompt_store = injection_prompt_store
        self._injection_fallback_messages = list(
            injection_fallback_messages
            or ["よくわからないのでもう一回説明してください。"]
        )

    async def run_chat_completion(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        request = self._sanitize_request(request)

        if not self._workflow_config.router_enabled:
            outcome = RouteOutcome(route="actor")
            response = await self._actor_client.generate(self._build_actor_request(request))
            final_response = await self._format_response(request, response)
            await self._record_event(request, final_response, outcome)
            return final_response

        outcome = await self._decide_route(request)
        if outcome.route == "injection":
            self._remember_injection_prompt(request, outcome)
            final_response = self._build_injection_fallback_response(request)
            await self._record_event(request, final_response, outcome)
            return final_response

        if outcome.route == "director":
            response = await self._director_client.generate(
                self._build_director_request(request)
            )
            final_response = await self._format_response(request, response)
            await self._record_event(request, final_response, outcome)
            return final_response

        response = await self._actor_client.generate(self._build_actor_request(request))
        final_response = await self._format_response(request, response)
        await self._record_event(request, final_response, outcome)
        return final_response

    async def _decide_route(self, request: ChatCompletionRequest) -> RouteOutcome:
        router_request = self._build_router_request(request)
        try:
            response = await self._router_client.generate(router_request)
            content = response.choices[0].message.content
            decision = parse_route_decision(content if isinstance(content, str) else None)
            if self._workflow_config.router_debug_logging:
                logger.info(
                    "Router decision selected route=%s risk_level=%s reason=%r",
                    decision.route,
                    decision.risk_level,
                    decision.reason,
                )
            return RouteOutcome(
                route=decision.route,
                risk_level=decision.risk_level,
                matched_prompt=decision.matched_prompt,
            )
        except Exception as exc:
            if self._workflow_config.router_debug_logging:
                logger.warning(
                    "Router decision failed; falling back to route=actor reason=%s: %s",
                    type(exc).__name__,
                    exc,
                )
            return RouteOutcome(route="actor", router_fallback=True)

    def _sanitize_request(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionRequest:
        if self._injection_prompt_store is None:
            return request
        return self._injection_prompt_store.sanitize_request(request)

    def _remember_injection_prompt(
        self,
        request: ChatCompletionRequest,
        outcome: RouteOutcome,
    ) -> None:
        if self._injection_prompt_store is None:
            return
        prompt = outcome.matched_prompt or self._latest_user_text(request)
        try:
            self._injection_prompt_store.add_prompt(prompt)
        except Exception as exc:
            logger.warning(
                "Injection prompt store failed reason=%s: %s",
                type(exc).__name__,
                exc,
            )

    def _latest_user_text(self, request: ChatCompletionRequest) -> str | None:
        for message in reversed(request.messages):
            if message.role != "user":
                continue
            content = message.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts = [
                    part["text"]
                    for part in content
                    if isinstance(part.get("text"), str)
                ]
                return "\n".join(text_parts)
        return None

    def _build_injection_fallback_response(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        content = random.choice(self._injection_fallback_messages)
        return ChatCompletionResponse(
            model=request.model or "gateway-model",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="stop",
                )
            ],
            usage=Usage(),
        )

    def _build_router_request(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionRequest:
        messages = [
            ChatMessage(role="system", content=self._router_prompt),
            *request.messages,
        ]
        return ChatCompletionRequest(
            model=request.model,
            messages=messages,
            stream=False,
            temperature=self._workflow_config.router_temperature,
            max_tokens=self._workflow_config.router_max_tokens,
        )

    def _build_director_request(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionRequest:
        messages = [
            *self._build_companion_messages(request),
            ChatMessage(role="system", content=self._director_prompt),
            *request.messages,
        ]
        return request.model_copy(update={"messages": messages})

    def _build_actor_request(
        self,
        request: ChatCompletionRequest,
    ) -> ChatCompletionRequest:
        companion_messages = self._build_companion_messages(request)
        if not companion_messages:
            return request
        return request.model_copy(
            update={"messages": [*companion_messages, *request.messages]}
        )

    def _build_companion_messages(
        self,
        request: ChatCompletionRequest,
    ) -> list[ChatMessage]:
        context = self._companion_context
        if self._companion_context_provider is not None:
            context = self._companion_context_provider.build_for_request(request).strip()
        if not context:
            return []
        return [ChatMessage(role="system", content=context)]

    async def _format_response(
        self,
        request: ChatCompletionRequest,
        draft_response: ChatCompletionResponse,
    ) -> ChatCompletionResponse:
        if not self._workflow_config.formatter_enabled:
            return draft_response

        try:
            formatter_response = await self._formatter_client.generate(
                self._build_formatter_request(request, draft_response)
            )
            formatted_content = formatter_response.choices[0].message.content
            if not isinstance(formatted_content, str) or not formatted_content.strip():
                raise ValueError("formatter returned empty content")
        except Exception as exc:
            logger.warning(
                "Formatter failed; returning draft response reason=%s: %s",
                type(exc).__name__,
                exc,
            )
            return draft_response

        choice = draft_response.choices[0]
        message = choice.message.model_copy(update={"content": formatted_content})
        choices = [
            choice.model_copy(update={"message": message}),
            *draft_response.choices[1:],
        ]
        return draft_response.model_copy(update={"choices": choices})

    def _build_formatter_request(
        self,
        request: ChatCompletionRequest,
        draft_response: ChatCompletionResponse,
    ) -> ChatCompletionRequest:
        draft_content = draft_response.choices[0].message.content
        messages = [
            ChatMessage(role="system", content=self._formatter_prompt),
            *request.messages,
            ChatMessage(
                role="assistant",
                content=draft_content if isinstance(draft_content, str) else "",
            ),
        ]
        return request.model_copy(update={"messages": messages, "stream": False})

    async def _record_event(
        self,
        request: ChatCompletionRequest,
        final_response: ChatCompletionResponse,
        outcome: RouteOutcome,
    ) -> None:
        try:
            await self._event_sink.record_chat_completion(
                ChatCompletionEvent(
                    route=outcome.route,
                    router_fallback=outcome.router_fallback,
                    request=request,
                    final_response=final_response,
                    companion_enabled=self._companion_enabled(),
                )
            )
        except Exception as exc:
            logger.warning(
                "Conversation event sink failed reason=%s: %s",
                type(exc).__name__,
                exc,
            )

    def _companion_enabled(self) -> bool:
        return bool(self._companion_context or self._companion_context_provider)
