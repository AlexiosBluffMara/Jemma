from __future__ import annotations

from typing import Protocol

from jemma.core.types import ChatRequest, ChatResponse, ProviderHealth


class ChatProvider(Protocol):
    def list_models(self) -> list[str]:
        ...

    def health(self) -> ProviderHealth:
        ...

    def chat(self, request: ChatRequest) -> ChatResponse:
        ...

