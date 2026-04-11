from __future__ import annotations

from dataclasses import asdict
from time import perf_counter
from typing import Any, Callable

from jemma.benchmarks.system_probe import collect_system_probe
from jemma.benchmarks.validators import validate_response
from jemma.config.loader import load_scenarios
from jemma.core.store import ArtifactStore
from jemma.core.types import AppConfig, ChatRequest, PairwiseBenchmarkManifest, SoloBenchmarkManifest, StressBenchmarkManifest
from jemma.providers.base import ChatProvider


class BenchmarkRunner:
    def __init__(
        self,
        config: AppConfig,
        provider: ChatProvider,
        store: ArtifactStore,
        event_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self.config = config
        self.provider = provider
        self.store = store
        self.event_callback = event_callback

    def run_solo(self, manifest: SoloBenchmarkManifest) -> dict[str, Any]:
        run_id, artifact_dir = self.store.create_run("solo-benchmark", manifest.name)
        self.store.write_json(artifact_dir / "manifest.json", asdict(manifest))
        self.store.write_json(artifact_dir / "system_probe.json", collect_system_probe(self.config.repo_root))
        scenarios = load_scenarios(manifest.dataset_path)
        self.store.append_event(run_id, "manifest_loaded", {"scenario_count": len(scenarios)})
        self._emit("manifest_loaded", {"run_id": run_id, "scenario_count": len(scenarios), "models": manifest.models})

        records: list[dict[str, Any]] = []
        for model in manifest.models:
            for _warmup in range(manifest.warmup_runs):
                if scenarios:
                    self._run_prompt(model, scenarios[0].system, scenarios[0].prompt, manifest.options)
            for scenario in scenarios:
                for iteration in range(manifest.repetitions):
                    self._emit(
                        "scenario_started",
                        {"run_id": run_id, "model": model, "scenario_id": scenario.scenario_id, "iteration": iteration + 1},
                    )
                    response_text, latency_ms = self._run_prompt(model, scenario.system, scenario.prompt, manifest.options)
                    passed, score, reasons = validate_response(scenario, response_text)
                    record = {
                        "model": model,
                        "scenario_id": scenario.scenario_id,
                        "iteration": iteration + 1,
                        "latency_ms": latency_ms,
                        "passed": passed,
                        "score": score,
                        "reasons": reasons,
                        "response_text": response_text,
                    }
                    records.append(record)
                    self.store.append_event(run_id, "scenario_completed", record)
                    self._emit("scenario_completed", {"run_id": run_id, **record})

        summary = self._summarize_records(records)
        self.store.write_json(artifact_dir / "raw_results.json", records)
        self.store.write_json(artifact_dir / "summary.json", summary)
        self._emit("run_completed", {"run_id": run_id, "summary": summary})
        return {"run_id": run_id, "artifact_dir": artifact_dir, "summary": summary}

    def run_pairwise(self, manifest: PairwiseBenchmarkManifest) -> dict[str, Any]:
        run_id, artifact_dir = self.store.create_run("pairwise-benchmark", manifest.name)
        self.store.write_json(artifact_dir / "manifest.json", asdict(manifest))
        self.store.write_json(artifact_dir / "system_probe.json", collect_system_probe(self.config.repo_root))
        scenarios = load_scenarios(manifest.dataset_path)
        records: list[dict[str, Any]] = []
        self._emit(
            "manifest_loaded",
            {"run_id": run_id, "scenario_count": len(scenarios), "models": [manifest.left_model, manifest.right_model]},
        )

        for _warmup in range(manifest.warmup_runs):
            if scenarios:
                self._run_prompt(manifest.left_model, scenarios[0].system, scenarios[0].prompt, manifest.options)
                self._run_prompt(manifest.right_model, scenarios[0].system, scenarios[0].prompt, manifest.options)

        for scenario in scenarios:
            for iteration in range(manifest.repetitions):
                self._emit(
                    "pairwise_started",
                    {
                        "run_id": run_id,
                        "scenario_id": scenario.scenario_id,
                        "iteration": iteration + 1,
                        "left_model": manifest.left_model,
                        "right_model": manifest.right_model,
                    },
                )
                left_text, left_latency = self._run_prompt(
                    manifest.left_model, scenario.system, scenario.prompt, manifest.options
                )
                right_text, right_latency = self._run_prompt(
                    manifest.right_model, scenario.system, scenario.prompt, manifest.options
                )
                left_passed, left_score, left_reasons = validate_response(scenario, left_text)
                right_passed, right_score, right_reasons = validate_response(scenario, right_text)
                winner = self._pick_winner(left_score, right_score, left_latency, right_latency)
                record = {
                    "scenario_id": scenario.scenario_id,
                    "iteration": iteration + 1,
                    "left": {
                        "model": manifest.left_model,
                        "passed": left_passed,
                        "score": left_score,
                        "latency_ms": left_latency,
                        "reasons": left_reasons,
                        "response_text": left_text,
                    },
                    "right": {
                        "model": manifest.right_model,
                        "passed": right_passed,
                        "score": right_score,
                        "latency_ms": right_latency,
                        "reasons": right_reasons,
                        "response_text": right_text,
                    },
                    "winner": winner,
                }
                records.append(record)
                self.store.append_event(run_id, "pairwise_completed", record)
                self._emit("pairwise_completed", {"run_id": run_id, **record})

        summary = self._summarize_pairwise(records, manifest.left_model, manifest.right_model)
        self.store.write_json(artifact_dir / "raw_results.json", records)
        self.store.write_json(artifact_dir / "summary.json", summary)
        self._emit("run_completed", {"run_id": run_id, "summary": summary})
        return {"run_id": run_id, "artifact_dir": artifact_dir, "summary": summary}

    def run_stress(self, manifest: StressBenchmarkManifest) -> dict[str, Any]:
        run_id, artifact_dir = self.store.create_run("stress-benchmark", manifest.name)
        self.store.write_json(artifact_dir / "manifest.json", asdict(manifest))
        self.store.write_json(artifact_dir / "system_probe.json", collect_system_probe(self.config.repo_root))
        groups = [
            ("standard", load_scenarios(manifest.standard_dataset_path)),
            ("reasoning", load_scenarios(manifest.reasoning_dataset_path)),
        ]
        self._emit(
            "manifest_loaded",
            {
                "run_id": run_id,
                "scenario_count": sum(len(scenarios) for _, scenarios in groups),
                "models": manifest.models,
                "prompt_styles": [name for name, _ in groups],
            },
        )

        records: list[dict[str, Any]] = []
        for model in manifest.models:
            for _warmup in range(manifest.warmup_runs):
                if groups[0][1]:
                    first = groups[0][1][0]
                    self._run_prompt(model, first.system, first.prompt, manifest.options)
            for prompt_style, scenarios in groups:
                for scenario in scenarios:
                    for iteration in range(manifest.repetitions):
                        self._emit(
                            "stress_started",
                            {
                                "run_id": run_id,
                                "model": model,
                                "prompt_style": prompt_style,
                                "scenario_id": scenario.scenario_id,
                                "iteration": iteration + 1,
                            },
                        )
                        response_text, latency_ms = self._run_prompt(model, scenario.system, scenario.prompt, manifest.options)
                        passed, score, reasons = validate_response(scenario, response_text)
                        record = {
                            "model": model,
                            "prompt_style": prompt_style,
                            "scenario_id": scenario.scenario_id,
                            "iteration": iteration + 1,
                            "latency_ms": latency_ms,
                            "passed": passed,
                            "score": score,
                            "reasons": reasons,
                            "response_text": response_text,
                        }
                        records.append(record)
                        self.store.append_event(run_id, "stress_completed", record)
                        self._emit("stress_completed", {"run_id": run_id, **record})

        summary = self._summarize_stress(records)
        self.store.write_json(artifact_dir / "raw_results.json", records)
        self.store.write_json(artifact_dir / "summary.json", summary)
        self._emit("run_completed", {"run_id": run_id, "summary": summary})
        return {"run_id": run_id, "artifact_dir": artifact_dir, "summary": summary}

    def _run_prompt(
        self,
        model: str,
        system_prompt: str,
        prompt: str,
        options: dict[str, Any],
    ) -> tuple[str, int]:
        request = ChatRequest(
            model=model,
            system=system_prompt,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
            if system_prompt
            else [{"role": "user", "content": prompt}],
            options=options,
            response_format="json" if options.get("format") == "json" else None,
        )
        started = perf_counter()
        response = self.provider.chat(request)
        latency_ms = int((perf_counter() - started) * 1000)
        return response.content, latency_ms

    @staticmethod
    def _pick_winner(left_score: float, right_score: float, left_latency: int, right_latency: int) -> str:
        if left_score > right_score:
            return "left"
        if right_score > left_score:
            return "right"
        if left_latency < right_latency:
            return "left"
        if right_latency < left_latency:
            return "right"
        return "tie"

    @staticmethod
    def _summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
        summary: dict[str, Any] = {"models": {}}
        for record in records:
            model_summary = summary["models"].setdefault(
                record["model"],
                {"runs": 0, "passed": 0, "latency_ms_total": 0, "score_total": 0.0},
            )
            model_summary["runs"] += 1
            model_summary["passed"] += int(record["passed"])
            model_summary["latency_ms_total"] += record["latency_ms"]
            model_summary["score_total"] += record["score"]

        for model, values in summary["models"].items():
            runs = max(values["runs"], 1)
            values["pass_rate"] = round(values["passed"] / runs, 3)
            values["avg_latency_ms"] = round(values["latency_ms_total"] / runs, 1)
            values["avg_score"] = round(values["score_total"] / runs, 3)
        return summary

    @staticmethod
    def _summarize_pairwise(records: list[dict[str, Any]], left_model: str, right_model: str) -> dict[str, Any]:
        left_wins = sum(1 for record in records if record["winner"] == "left")
        right_wins = sum(1 for record in records if record["winner"] == "right")
        ties = sum(1 for record in records if record["winner"] == "tie")
        total = max(len(records), 1)
        return {
            "left_model": left_model,
            "right_model": right_model,
            "left_wins": left_wins,
            "right_wins": right_wins,
            "ties": ties,
            "left_win_rate": round(left_wins / total, 3),
            "right_win_rate": round(right_wins / total, 3),
        }

    @staticmethod
    def _summarize_stress(records: list[dict[str, Any]]) -> dict[str, Any]:
        summary: dict[str, Any] = {"models": {}}
        for record in records:
            model_summary = summary["models"].setdefault(record["model"], {})
            style_summary = model_summary.setdefault(
                record["prompt_style"],
                {"runs": 0, "passed": 0, "latency_ms_total": 0, "score_total": 0.0},
            )
            style_summary["runs"] += 1
            style_summary["passed"] += int(record["passed"])
            style_summary["latency_ms_total"] += record["latency_ms"]
            style_summary["score_total"] += record["score"]

        for model_summary in summary["models"].values():
            for values in model_summary.values():
                runs = max(values["runs"], 1)
                values["pass_rate"] = round(values["passed"] / runs, 3)
                values["avg_latency_ms"] = round(values["latency_ms_total"] / runs, 1)
                values["avg_score"] = round(values["score_total"] / runs, 3)
        return summary

    def _emit(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_callback is not None:
            self.event_callback(event_type, payload)

