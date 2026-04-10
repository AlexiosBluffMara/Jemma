from __future__ import annotations

import json
from dataclasses import asdict
from time import perf_counter

from jemma.core.store import ArtifactStore
from jemma.core.types import (
    AgentObjective,
    AgentRunResult,
    AppConfig,
    ChatRequest,
    ExecutionResult,
    PlanStep,
)
from jemma.providers.base import ChatProvider


class AgentLoop:
    def __init__(
        self,
        config: AppConfig,
        provider: ChatProvider,
        store: ArtifactStore,
        capabilities: dict[str, object],
    ) -> None:
        self.config = config
        self.provider = provider
        self.store = store
        self.capabilities = capabilities

    def run_objective(self, objective: AgentObjective) -> AgentRunResult:
        run_id, artifact_dir = self.store.create_run("agent-run", objective.name)
        self.store.write_json(artifact_dir / "objective.json", asdict(objective))
        plan = self._plan(objective)
        self.store.write_json(artifact_dir / "plan.json", [asdict(step) for step in plan])

        results: list[ExecutionResult] = []
        for step in plan[: objective.max_steps]:
            result = self._execute_step(objective, step)
            results.append(result)
            self.store.append_event(run_id, "step_completed", {"step": asdict(step), "result": asdict(result)})
            if not result.ok and step.kind == "infer" and objective.fallback_model:
                fallback_step = PlanStep(
                    step_id=f"{step.step_id}-fallback",
                    kind="infer",
                    target=objective.fallback_model,
                    instruction=step.instruction,
                    args=step.args,
                    expected_contains=step.expected_contains,
                )
                fallback_result = self._execute_step(objective, fallback_step)
                results.append(fallback_result)
                self.store.append_event(
                    run_id,
                    "fallback_completed",
                    {"step": asdict(fallback_step), "result": asdict(fallback_result)},
                )
                if fallback_result.ok:
                    results[-1] = fallback_result

        summary = self._summarize(objective, results)
        self.store.write_json(artifact_dir / "summary.json", {"summary": summary, "ok": not summary.startswith("FAILED")})
        return AgentRunResult(
            ok=not summary.startswith("FAILED"),
            objective=objective.name,
            steps=results,
            summary=summary,
            artifact_dir=artifact_dir,
        )

    def _plan(self, objective: AgentObjective) -> list[PlanStep]:
        capabilities = {name: adapter.describe() for name, adapter in self.capabilities.items()}
        system_prompt = (
            "You are the Jemma planner. Return strict JSON with a top-level 'steps' array. "
            "Each step must have step_id, kind ('infer' or 'capability'), target, instruction, args, expected_contains."
        )
        request = ChatRequest(
            model=objective.model or self.config.planner_model,
            system=system_prompt,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "objective": objective.prompt,
                            "success_criteria": objective.success_criteria,
                            "max_steps": min(objective.max_steps, self.config.max_steps),
                            "capabilities": capabilities,
                        }
                    ),
                },
            ],
            response_format="json",
        )
        try:
            response = self.provider.chat(request)
            data = json.loads(response.content)
            steps = [
                PlanStep(
                    step_id=item["step_id"],
                    kind=item["kind"],
                    target=item["target"],
                    instruction=item["instruction"],
                    args=dict(item.get("args", {})),
                    expected_contains=list(item.get("expected_contains", [])),
                )
                for item in data.get("steps", [])
            ]
            if steps:
                return steps
        except (json.JSONDecodeError, KeyError, RuntimeError):
            pass

        return [
            PlanStep(
                step_id="step-1",
                kind="infer",
                target=objective.model or self.config.default_model,
                instruction=objective.prompt,
                expected_contains=objective.success_criteria,
            )
        ]

    def _execute_step(self, objective: AgentObjective, step: PlanStep) -> ExecutionResult:
        if step.kind == "infer":
            started = perf_counter()
            response = self.provider.chat(
                ChatRequest(
                    model=step.target,
                    system="",
                    messages=[{"role": "user", "content": step.instruction}],
                )
            )
            payload = {"content": response.content, "model": step.target}
            passed = all(item in response.content for item in step.expected_contains)
            return ExecutionResult(
                ok=passed or not step.expected_contains,
                output=payload,
                error=None,
                duration_ms=int((perf_counter() - started) * 1000),
            )

        if step.kind == "capability":
            adapter = self.capabilities.get(step.target)
            if adapter is None:
                return ExecutionResult(ok=False, output={}, error=f"unknown capability {step.target!r}")
            started = perf_counter()
            result = adapter.execute(
                str(step.args.get("action", "observe_status")),
                step.args,
                confirmed=bool(step.args.get("confirmed", False)),
            )
            passed = bool(result.get("ok"))
            if step.expected_contains:
                serialized = json.dumps(result)
                passed = passed and all(item in serialized for item in step.expected_contains)
            return ExecutionResult(
                ok=passed,
                output=result,
                error=result.get("error"),
                duration_ms=int((perf_counter() - started) * 1000),
            )

        return ExecutionResult(ok=False, output={}, error=f"unsupported step kind {step.kind!r}")

    @staticmethod
    def _summarize(objective: AgentObjective, results: list[ExecutionResult]) -> str:
        if not results:
            return f"FAILED: {objective.name} produced no steps"
        failures = [result for result in results if not result.ok]
        if failures:
            return f"FAILED: {objective.name} completed with {len(failures)} failing steps"
        return f"SUCCESS: {objective.name} completed with {len(results)} passing steps"

