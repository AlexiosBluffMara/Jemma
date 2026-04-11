from __future__ import annotations

import json
from urllib import error, request

from jemma.core.types import AppConfig, ChatRequest, ChatResponse, ProviderHealth


class LlamaCppProvider:
    """Provider for llama.cpp server (llama-server) using its OpenAI-compatible API."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.base_url = config.llamacpp_base_url.rstrip("/")
        self.timeout_s = config.llamacpp_timeout_s

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
            raise RuntimeError(f"llama.cpp HTTP error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"llama.cpp connection failed: {exc.reason}") from exc

    def list_models(self) -> list[str]:
        payload = self._request("GET", "/v1/models")
        return [item["id"] for item in payload.get("data", [])]

    def health(self) -> ProviderHealth:
        try:
            models = self.list_models()
        except RuntimeError as exc:
            return ProviderHealth(provider="llamacpp", ok=False, detail=str(exc), models=[])
        return ProviderHealth(provider="llamacpp", ok=True, detail="reachable", models=models)

    def chat(self, request_data: ChatRequest) -> ChatResponse:
        resolved_model = self.config.models.get(request_data.model)
        messages: list[dict[str, str]] = []
        if request_data.system:
            messages.append({"role": "system", "content": request_data.system})
        messages.extend(request_data.messages)

        payload: dict[str, object] = {
            "model": resolved_model.remote_name if resolved_model else request_data.model,
            "messages": messages,
            "stream": False,
        }
        if request_data.options.get("temperature") is not None:
            payload["temperature"] = request_data.options["temperature"]
        if request_data.options.get("top_p") is not None:
            payload["top_p"] = request_data.options["top_p"]
        if request_data.options.get("num_predict") is not None:
            payload["max_tokens"] = request_data.options["num_predict"]
        if request_data.response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        response = self._request("POST", "/v1/chat/completions", payload=payload, timeout_s=request_data.timeout_s)
        choices = response.get("choices", [])
        content = choices[0]["message"]["content"] if choices else ""
        usage = response.get("usage", {})
        return ChatResponse(
            model=resolved_model.remote_name if resolved_model else request_data.model,
            content=content,
            raw=response,
            total_duration_ms=None,
            prompt_eval_count=usage.get("prompt_tokens"),
            eval_count=usage.get("completion_tokens"),
        )
