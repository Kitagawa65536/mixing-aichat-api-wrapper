from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from app.llm.openai_compatible import LLMConnectionError
from app.models.chat import ChatCompletionRequest, ChatCompletionResponse
from app.workflow.orchestrator import Orchestrator


router = APIRouter(prefix="/v1")


def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request_body: ChatCompletionRequest,
    request: Request,
) -> ChatCompletionResponse:
    if request_body.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming is not supported. Use stream=false.",
        )

    orchestrator = get_orchestrator(request)
    try:
        return await orchestrator.run_chat_completion(request_body)
    except LLMConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"role": exc.role_name, "message": str(exc)},
        ) from exc
