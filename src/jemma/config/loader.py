from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from jemma.core.types import (
    AgentObjective,
    AppConfig,
    BenchmarkScenario,
    CapabilityPolicy,
    ModelSpec,
    PairwiseBenchmarkManifest,
    SoloBenchmarkManifest,
    StressBenchmarkManifest,
)


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_app_config(
    repo_root: Path,
    *,
    default_path: Path | None = None,
    models_path: Path | None = None,
    lan_path: Path | None = None,
) -> AppConfig:
    default_path = default_path or repo_root / "configs" / "default.toml"
    models_path = models_path or repo_root / "configs" / "models.toml"
    lan_path = lan_path or repo_root / "configs" / "lan.toml"

    base_data = _load_toml(default_path)
    models_data = _load_toml(models_path)
    lan_data = _load_toml(lan_path)

    models = {
        item["model_id"]: ModelSpec(
            model_id=item["model_id"],
            provider=item["provider"],
            remote_name=item["remote_name"],
            context_window=int(item["context_window"]),
            quantization=item.get("quantization"),
            tags=list(item.get("tags", [])),
        )
        for item in models_data.get("models", [])
    }

    safety = base_data.get("safety", {})
    capability_policies = {
        "discord": CapabilityPolicy(
            capability="discord",
            allowed_actions=["observe_blueprint", "build_invite_url", "render_channel_matrix", "render_ruleset"],
            require_confirmation=False,
        ),
        "tailscale": CapabilityPolicy(
            capability="tailscale",
            allowed_actions=["observe_status", "list_peers"],
            require_confirmation=False,
        ),
        "router_status": CapabilityPolicy(
            capability="router_status",
            allowed_actions=["observe_gateway", "observe_dns", "observe_internet"],
            require_confirmation=False,
        ),
        "hue": CapabilityPolicy(
            capability="hue",
            allowed_actions=["observe_bridge", "observe_lights", "activate_scene"],
            allowlisted_targets=list(lan_data.get("hue", {}).get("allowlisted_rooms", [])),
            require_confirmation=True,
        ),
        "smartplug": CapabilityPolicy(
            capability="smartplug",
            allowed_actions=["observe_status", "power_on", "power_off"],
            allowlisted_targets=list(lan_data.get("smartplug", {}).get("allowlisted_plugs", [])),
            require_confirmation=True,
        ),
    }

    agent = base_data.get("agent", {})
    provider = base_data.get("provider", {}).get("ollama", {})
    llamacpp = base_data.get("provider", {}).get("llamacpp", {})
    app = base_data.get("app", {})
    return AppConfig(
        repo_root=repo_root,
        state_dir=repo_root / app.get("state_dir", "state"),
        artifacts_dir=repo_root / app.get("artifacts_dir", "artifacts"),
        ollama_base_url=provider.get("base_url", "http://127.0.0.1:11434"),
        ollama_timeout_s=int(provider.get("timeout_s", 120)),
        llamacpp_base_url=llamacpp.get("base_url", "http://127.0.0.1:8080"),
        llamacpp_timeout_s=int(llamacpp.get("timeout_s", 120)),
        default_model=agent.get("default_model", ""),
        planner_model=agent.get("planner_model", ""),
        validator_model=agent.get("validator_model", ""),
        fallback_model=agent.get("fallback_model"),
        max_steps=int(agent.get("max_steps", 4)),
        actuation_enabled=bool(safety.get("actuation_enabled", False)),
        capability_policies=capability_policies,
        raw_sections={"default": base_data, "lan": lan_data, "models": models_data},
        models=models,
    )


def load_scenarios(path: Path) -> list[BenchmarkScenario]:
    scenarios: list[BenchmarkScenario] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            data = json.loads(line)
            scenarios.append(
                BenchmarkScenario(
                    scenario_id=data["scenario_id"],
                    prompt=data["prompt"],
                    system=data.get("system", ""),
                    validator=data.get("validator", "exact_text"),
                    expected=data.get("expected"),
                    expected_keywords=list(data.get("expected_keywords", [])),
                    tags=list(data.get("tags", [])),
                    metadata=dict(data.get("metadata", {})),
                )
            )
    return scenarios


def load_solo_manifest(repo_root: Path, path: Path) -> SoloBenchmarkManifest:
    data = _load_toml(path)
    dataset = repo_root / data["dataset"]["path"]
    run = data.get("run", {})
    return SoloBenchmarkManifest(
        name=data["name"],
        models=list(data["models"]),
        dataset_path=dataset,
        repetitions=int(run.get("repetitions", 1)),
        warmup_runs=int(run.get("warmup_runs", 0)),
        options=dict(run),
    )


def load_pairwise_manifest(repo_root: Path, path: Path) -> PairwiseBenchmarkManifest:
    data = _load_toml(path)
    dataset = repo_root / data["dataset"]["path"]
    run = data.get("run", {})
    return PairwiseBenchmarkManifest(
        name=data["name"],
        left_model=data["left"]["model"],
        right_model=data["right"]["model"],
        dataset_path=dataset,
        repetitions=int(run.get("repetitions", 1)),
        warmup_runs=int(run.get("warmup_runs", 0)),
        options=dict(run),
    )


def load_stress_manifest(repo_root: Path, path: Path) -> StressBenchmarkManifest:
    data = _load_toml(path)
    run = data.get("run", {})
    return StressBenchmarkManifest(
        name=data["name"],
        models=list(data["models"]),
        standard_dataset_path=repo_root / data["datasets"]["standard"],
        reasoning_dataset_path=repo_root / data["datasets"]["reasoning"],
        repetitions=int(run.get("repetitions", 1)),
        warmup_runs=int(run.get("warmup_runs", 0)),
        options=dict(run),
    )


def load_objective(path: Path) -> AgentObjective:
    data = _load_toml(path)
    return AgentObjective(
        name=data["name"],
        prompt=data["objective"]["prompt"],
        success_criteria=list(data["objective"].get("success_criteria", [])),
        max_steps=int(data["objective"].get("max_steps", 4)),
        model=data["objective"].get("model"),
        fallback_model=data["objective"].get("fallback_model"),
    )

