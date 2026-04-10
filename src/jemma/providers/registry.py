from __future__ import annotations

from jemma.core.types import AppConfig
from jemma.providers.ollama import OllamaProvider


def build_provider(config: AppConfig, provider_name: str = "ollama") -> OllamaProvider:
    if provider_name != "ollama":
        raise ValueError(f"Unsupported provider: {provider_name}")
    return OllamaProvider(config)
