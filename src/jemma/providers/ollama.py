from __future__ import annotations

import json
from urllib import error, request

from jemma.core.types import AppConfig, ChatRequest, ChatResponse, ProviderHealth


class OllamaProvider:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.base_url = config.ollama_base_url.rstrip("/")
        self.timeout_s = config.ollama_timeout_s

    def _request(self, method: str, path: str, payload: dict | None = None, *, timeout_s: int | None = None) -> dict:
        body = None
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        req = request.Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=timeout_s or self.timeout_s) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Ollama connection failed: {exc.reason}") from exc

    def list_models(self) -> list[str]:
        payload = self._request("GET", "/api/tags")
        return [item["name"] for item in payload.get("models", [])]

    def health(self) -> ProviderHealth:
        try:
            models = self.list_models()
        except RuntimeError as exc:
            return ProviderHealth(provider="ollama", ok=False, detail=str(exc), models=[])
        return ProviderHealth(provider="ollama", ok=True, detail="reachable", models=models)

    def chat(self, request_data: ChatRequest) -> ChatResponse:
        resolved_model = self.config.models.get(request_data.model)
        messages = list(request_data.messages)
        if request_data.system:
            messages = [{"role": "system", "content": request_data.system}, *messages]
        payload: dict[str, object] = {
            "model": resolved_model.remote_name if resolved_model else request_data.model,
            "messages": messages,
            "stream": False,
            "options": request_data.options,
        }
        if request_data.response_format == "json":
            payload["format"] = "json"

        response = self._request("POST", "/api/chat", payload=payload, timeout_s=request_data.timeout_s)
        message = response.get("message", {})
        content = message.get("content", "")
        total_duration = response.get("total_duration")
        total_ms = int(total_duration / 1_000_000) if isinstance(total_duration, int) else None
        return ChatResponse(
            model=resolved_model.remote_name if resolved_model else request_data.model,
            content=content,
            raw=response,
            total_duration_ms=total_ms,
            prompt_eval_count=response.get("prompt_eval_count"),
            eval_count=response.get("eval_count"),
        )

