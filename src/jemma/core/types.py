from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ModelSpec:
    model_id: str
    provider: str
    remote_name: str
    context_window: int
    quantization: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ChatRequest:
    model: str
    system: str
    messages: list[dict[str, str]]
    options: dict[str, Any] = field(default_factory=dict)
    response_format: str | None = None
    timeout_s: int = 120


@dataclass(slots=True)
class ChatResponse:
    model: str
    content: str
    raw: dict[str, Any]
    total_duration_ms: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None


@dataclass(slots=True)
class ProviderHealth:
    provider: str
    ok: bool
    detail: str
    models: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CapabilityPolicy:
    capability: str
    allowed_actions: list[str]
    allowlisted_targets: list[str] = field(default_factory=list)
    require_confirmation: bool = True


@dataclass(slots=True)
class AppConfig:
    repo_root: Path
    state_dir: Path
    artifacts_dir: Path
    ollama_base_url: str
    ollama_timeout_s: int
    default_model: str
    planner_model: str
    validator_model: str
    fallback_model: str | None
    max_steps: int
    actuation_enabled: bool
    capability_policies: dict[str, CapabilityPolicy]
    raw_sections: dict[str, Any]
    models: dict[str, ModelSpec]


@dataclass(slots=True)
class BenchmarkScenario:
    scenario_id: str
    prompt: str
    system: str = ""
    validator: str = "exact_text"
    expected: str | None = None
    expected_keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SoloBenchmarkManifest:
    name: str
    models: list[str]
    dataset_path: Path
    repetitions: int = 1
    warmup_runs: int = 0
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PairwiseBenchmarkManifest:
    name: str
    left_model: str
    right_model: str
    dataset_path: Path
    repetitions: int = 1
    warmup_runs: int = 0
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StressBenchmarkManifest:
    name: str
    models: list[str]
    standard_dataset_path: Path
    reasoning_dataset_path: Path
    repetitions: int = 1
    warmup_runs: int = 0
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PlanStep:
    step_id: str
    kind: str
    target: str
    instruction: str
    args: dict[str, Any] = field(default_factory=dict)
    expected_contains: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AgentObjective:
    name: str
    prompt: str
    success_criteria: list[str]
    max_steps: int = 4
    model: str | None = None
    fallback_model: str | None = None


@dataclass(slots=True)
class ExecutionResult:
    ok: bool
    output: dict[str, Any]
    error: str | None = None
    duration_ms: int = 0


@dataclass(slots=True)
class AgentRunResult:
    ok: bool
    objective: str
    steps: list[ExecutionResult]
    summary: str
    artifact_dir: Path


@dataclass(slots=True)
class JobRecord:
    job_id: str
    kind: str
    status: str
    visibility: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    current_phase: str = "queued"
    total_steps: int = 0
    completed_steps: int = 0
    models: list[str] = field(default_factory=list)
    run_ids: list[str] = field(default_factory=list)
    prompt_style: str = "standard"
    error: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)

