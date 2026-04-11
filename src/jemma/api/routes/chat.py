from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from jemma.api.schemas import ChatRequestBody, ChatResponseBody
from jemma.core.types import ChatRequest

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponseBody)
def chat_with_model(request: Request, body: ChatRequestBody) -> ChatResponseBody:
    config = request.app.state.config
    provider = request.app.state.provider
    messages = [item.model_dump() for item in body.messages]
    if not messages:
        raise HTTPException(status_code=422, detail="At least one message is required")

    model = body.model or config.default_model
    if not model:
        raise HTTPException(status_code=500, detail="No default model is configured")

    try:
        response = provider.chat(
            ChatRequest(
                model=model,
                system=body.system,
                messages=messages,
                options=body.options,
                response_format=body.response_format,
                timeout_s=body.timeout_s,
            )
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponseBody(
        model=response.model,
        content=response.content,
        raw=response.raw,
        total_duration_ms=response.total_duration_ms,
        prompt_eval_count=response.prompt_eval_count,
        eval_count=response.eval_count,
    )
