from __future__ import annotations

from jemma.core.types import AppConfig
from jemma.providers.base import ChatProvider
from jemma.providers.llamacpp import LlamaCppProvider
from jemma.providers.ollama import OllamaProvider


def build_provider(config: AppConfig, provider_name: str = "ollama") -> ChatProvider:
    if provider_name == "ollama":
        return OllamaProvider(config)
    if provider_name == "llamacpp":
        return LlamaCppProvider(config)
    raise ValueError(f"Unsupported provider: {provider_name}")
