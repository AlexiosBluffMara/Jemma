from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SoloBenchmarkRequest(BaseModel):
    name: str = Field(default="api-solo-benchmark")
    models: list[str]
    dataset_path: str
    repetitions: int = Field(default=1, ge=1)
    warmup_runs: int = Field(default=0, ge=0)
    visibility: Literal["local", "public"] = "local"
    options: dict[str, Any] = Field(default_factory=dict)


class PairwiseBenchmarkRequest(BaseModel):
    name: str = Field(default="api-pairwise-benchmark")
    left_model: str
    right_model: str
    dataset_path: str
    repetitions: int = Field(default=1, ge=1)
    warmup_runs: int = Field(default=0, ge=0)
    visibility: Literal["local", "public"] = "local"
    options: dict[str, Any] = Field(default_factory=dict)


class StressBenchmarkRequest(BaseModel):
    name: str = Field(default="api-stress-benchmark")
    models: list[str]
    standard_dataset_path: str
    reasoning_dataset_path: str
    repetitions: int = Field(default=1, ge=1)
    warmup_runs: int = Field(default=0, ge=0)
    visibility: Literal["local", "public"] = "local"
    options: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str = Field(min_length=1)


class ChatRequestBody(BaseModel):
    model: str | None = None
    system: str = ""
    messages: list[ChatMessage] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)
    response_format: Literal["json"] | None = None
    timeout_s: int = Field(default=120, ge=1, le=600)


class ChatResponseBody(BaseModel):
    model: str
    content: str
    raw: dict[str, Any]
    total_duration_ms: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None


class CapabilityDescriptor(BaseModel):
    name: str
    actions: list[str] = Field(default_factory=list)
    allowlisted_targets: list[str] = Field(default_factory=list)
    require_confirmation: bool = True
    summary: str = ""


class CapabilityListResponse(BaseModel):
    capabilities: list[CapabilityDescriptor] = Field(default_factory=list)

