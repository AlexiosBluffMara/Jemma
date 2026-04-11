import type { BenchmarkPreset, JobEvent, JobRecord, ModelSpec, ProviderHealth, RunRecord, SystemPayload } from "./types";

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<{ ok: boolean; provider: ProviderHealth }> {
  return jsonFetch("/api/health");
}

export function getModels(): Promise<{ models: ModelSpec[] }> {
  return jsonFetch("/api/models");
}

export function getSystem(): Promise<SystemPayload> {
  return jsonFetch("/api/system");
}

export function getRuns(): Promise<{ runs: RunRecord[] }> {
  return jsonFetch("/api/runs");
}

export function getRun(runId: string): Promise<{ run: RunRecord; summary: Record<string, unknown> | null }> {
  return jsonFetch(`/api/runs/${runId}`);
}

export function getRunResults(runId: string): Promise<{ run_id: string; results: unknown[] }> {
  return jsonFetch(`/api/runs/${runId}/results`);
}

export function getJobs(): Promise<{ jobs: JobRecord[] }> {
  return jsonFetch("/api/jobs");
}

export function getJob(jobId: string): Promise<{ job: JobRecord }> {
  return jsonFetch(`/api/jobs/${jobId}`);
}

export function getPresets(): Promise<{ presets: BenchmarkPreset[] }> {
  return jsonFetch("/api/benchmarks/presets");
}

export function submitSoloBenchmark(payload: Record<string, unknown>): Promise<{ job: JobRecord }> {
  return jsonFetch("/api/jobs/benchmark/solo", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function submitPairwiseBenchmark(payload: Record<string, unknown>): Promise<{ job: JobRecord }> {
  return jsonFetch("/api/jobs/benchmark/pairwise", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function submitStressBenchmark(payload: Record<string, unknown>): Promise<{ job: JobRecord }> {
  return jsonFetch("/api/jobs/benchmark/stress", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function subscribeJobEvents(jobId: string, onEvent: (event: JobEvent) => void): () => void {
  const source = new EventSource(`/api/jobs/${jobId}/events`);
  source.onmessage = (event) => {
    onEvent(JSON.parse(event.data) as JobEvent);
  };
  return () => source.close();
}

