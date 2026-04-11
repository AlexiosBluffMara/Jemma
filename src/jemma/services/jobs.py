from __future__ import annotations

import threading
from dataclasses import asdict
from datetime import UTC, datetime
from itertools import count
from typing import Any

from jemma.benchmarks.runner import BenchmarkRunner
from jemma.config.loader import load_scenarios
from jemma.core.store import ArtifactStore
from jemma.core.types import (
    AppConfig,
    JobRecord,
    PairwiseBenchmarkManifest,
    SoloBenchmarkManifest,
    StressBenchmarkManifest,
)
from jemma.providers.base import ChatProvider
from jemma.services.telemetry import collect_runtime_telemetry


class JobManager:
    def __init__(self, config: AppConfig, provider: ChatProvider, store: ArtifactStore) -> None:
        self.config = config
        self.provider = provider
        self.store = store
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._sequence = count(1)
        self._event_sequence = count(1)

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = [asdict(item) for item in self._jobs.values()]
        return sorted(jobs, key=lambda item: item["created_at"], reverse=True)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._jobs.get(job_id)
            return asdict(record) if record else None

    def get_events(self, job_id: str, after: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            events = list(self._events.get(job_id, []))
        return [event for event in events if event["sequence"] > after]

    def submit_solo(self, manifest: SoloBenchmarkManifest, *, visibility: str = "local") -> dict[str, Any]:
        scenario_count = len(load_scenarios(manifest.dataset_path))
        total_steps = max(len(manifest.models) * scenario_count * max(manifest.repetitions, 1), 1)
        return self._submit_job(
            kind="solo",
            visibility=visibility,
            models=manifest.models,
            prompt_style="standard",
            total_steps=total_steps,
            target=self._run_solo_job,
            args=(manifest,),
        )

    def submit_pairwise(self, manifest: PairwiseBenchmarkManifest, *, visibility: str = "local") -> dict[str, Any]:
        scenario_count = len(load_scenarios(manifest.dataset_path))
        total_steps = max(scenario_count * max(manifest.repetitions, 1), 1)
        return self._submit_job(
            kind="pairwise",
            visibility=visibility,
            models=[manifest.left_model, manifest.right_model],
            prompt_style="standard",
            total_steps=total_steps,
            target=self._run_pairwise_job,
            args=(manifest,),
        )

    def submit_stress(self, manifest: StressBenchmarkManifest, *, visibility: str = "local") -> dict[str, Any]:
        total_scenarios = len(load_scenarios(manifest.standard_dataset_path)) + len(
            load_scenarios(manifest.reasoning_dataset_path)
        )
        total_steps = max(len(manifest.models) * total_scenarios * max(manifest.repetitions, 1), 1)
        return self._submit_job(
            kind="stress",
            visibility=visibility,
            models=manifest.models,
            prompt_style="both",
            total_steps=total_steps,
            target=self._run_stress_job,
            args=(manifest,),
        )

    def _submit_job(
        self,
        *,
        kind: str,
        visibility: str,
        models: list[str],
        prompt_style: str,
        total_steps: int,
        target: Any,
        args: tuple[Any, ...],
    ) -> dict[str, Any]:
        job_id = f"job-{next(self._sequence):04d}"
        record = JobRecord(
            job_id=job_id,
            kind=kind,
            status="queued",
            visibility=visibility,
            created_at=datetime.now(UTC).isoformat(),
            total_steps=total_steps,
            models=models,
            prompt_style=prompt_style,
        )
        with self._lock:
            self._jobs[job_id] = record
            self._events[job_id] = []
        self._append_event(job_id, "job_queued", {"job_id": job_id, "kind": kind, "models": models})
        thread = threading.Thread(target=target, args=(job_id, *args), daemon=True)
        thread.start()
        return asdict(record)

    def _runner(self, job_id: str) -> BenchmarkRunner:
        return BenchmarkRunner(
            self.config,
            self.provider,
            self.store,
            event_callback=lambda event, payload: self._on_runner_event(job_id, event, payload),
        )

    def _run_solo_job(self, job_id: str, manifest: SoloBenchmarkManifest) -> None:
        self._mark_started(job_id, phase="running solo benchmark")
        try:
            result = self._runner(job_id).run_solo(manifest)
        except Exception as exc:
            self._mark_failed(job_id, str(exc))
            return
        self._mark_completed(job_id, result)

    def _run_pairwise_job(self, job_id: str, manifest: PairwiseBenchmarkManifest) -> None:
        self._mark_started(job_id, phase="running pairwise benchmark")
        try:
            result = self._runner(job_id).run_pairwise(manifest)
        except Exception as exc:
            self._mark_failed(job_id, str(exc))
            return
        self._mark_completed(job_id, result)

    def _run_stress_job(self, job_id: str, manifest: StressBenchmarkManifest) -> None:
        self._mark_started(job_id, phase="running stress benchmark")
        self._append_event(job_id, "telemetry_sample", collect_runtime_telemetry(self.config))
        try:
            result = self._runner(job_id).run_stress(manifest)
        except Exception as exc:
            self._mark_failed(job_id, str(exc))
            return
        self._append_event(job_id, "telemetry_sample", collect_runtime_telemetry(self.config))
        self._mark_completed(job_id, result)

    def _mark_started(self, job_id: str, *, phase: str) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = "running"
            record.started_at = datetime.now(UTC).isoformat()
            record.current_phase = phase
        self._append_event(job_id, "job_started", {"job_id": job_id, "phase": phase})

    def _mark_completed(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = "succeeded"
            record.finished_at = datetime.now(UTC).isoformat()
            record.current_phase = "completed"
            record.summary = result["summary"]
            if result["run_id"] not in record.run_ids:
                record.run_ids.append(result["run_id"])
            record.completed_steps = max(record.completed_steps, record.total_steps)
        self._append_event(job_id, "job_completed", {"job_id": job_id, "run_id": result["run_id"], "summary": result["summary"]})

    def _mark_failed(self, job_id: str, message: str) -> None:
        with self._lock:
            record = self._jobs[job_id]
            record.status = "failed"
            record.finished_at = datetime.now(UTC).isoformat()
            record.current_phase = "failed"
            record.error = message
        self._append_event(job_id, "job_failed", {"job_id": job_id, "error": message})

    def _on_runner_event(self, job_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._lock:
            record = self._jobs[job_id]
            if event_type.endswith("_completed"):
                record.completed_steps += 1
            record.current_phase = event_type.replace("_", " ")
            run_id = payload.get("run_id")
            if isinstance(run_id, str) and run_id not in record.run_ids:
                record.run_ids.append(run_id)
        self._append_event(job_id, event_type, payload)

    def _append_event(self, job_id: str, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "sequence": next(self._event_sequence),
            "type": event_type,
            "created_at": datetime.now(UTC).isoformat(),
            "payload": payload,
        }
        with self._lock:
            self._events.setdefault(job_id, []).append(event)
