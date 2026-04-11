import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

import {
  getHealth,
  getJob,
  getJobs,
  getModels,
  getPresets,
  getRun,
  getRunResults,
  getRuns,
  getSystem,
  submitPairwiseBenchmark,
  submitSoloBenchmark,
  submitStressBenchmark,
  subscribeJobEvents
} from "./api";
import type { BenchmarkPreset, JobEvent, JobRecord, ModelSpec, ProviderHealth, RunRecord, SystemPayload } from "./types";

type TabName = "overview" | "benchmarks" | "jobs" | "runs" | "system";

const defaultStandardDataset = "datasets/prompts/stress-standard.jsonl";
const defaultReasoningDataset = "datasets/prompts/stress-reasoning.jsonl";
const defaultSoloDataset = "datasets/prompts/smoke.jsonl";
const defaultPairwiseDataset = "datasets/prompts/qa.jsonl";

export default function App() {
  const [tab, setTab] = useState<TabName>("overview");
  const [health, setHealth] = useState<ProviderHealth | null>(null);
  const [models, setModels] = useState<ModelSpec[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [presets, setPresets] = useState<BenchmarkPreset[]>([]);
  const [system, setSystem] = useState<SystemPayload | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [jobEvents, setJobEvents] = useState<JobEvent[]>([]);
  const [runSummary, setRunSummary] = useState<Record<string, unknown> | null>(null);
  const [runResults, setRunResults] = useState<unknown[] | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [benchmarkKind, setBenchmarkKind] = useState<"solo" | "pairwise" | "stress">("stress");
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [leftModel, setLeftModel] = useState("");
  const [rightModel, setRightModel] = useState("");
  const [soloDataset, setSoloDataset] = useState(defaultSoloDataset);
  const [pairwiseDataset, setPairwiseDataset] = useState(defaultPairwiseDataset);
  const [standardDataset, setStandardDataset] = useState(defaultStandardDataset);
  const [reasoningDataset, setReasoningDataset] = useState(defaultReasoningDataset);
  const [repetitions, setRepetitions] = useState(1);
  const [warmupRuns, setWarmupRuns] = useState(1);

  useEffect(() => {
    void refreshAll();
  }, []);

  useEffect(() => {
    if (models.length > 0 && selectedModels.length === 0) {
      setSelectedModels(models.slice(0, Math.min(3, models.length)).map((item) => item.model_id));
      setLeftModel(models[0]?.model_id ?? "");
      setRightModel(models[1]?.model_id ?? models[0]?.model_id ?? "");
    }
  }, [models, selectedModels.length]);

  useEffect(() => {
    if (!selectedJobId) {
      return undefined;
    }
    const unsubscribe = subscribeJobEvents(selectedJobId, (event) => {
      setJobEvents((previous) => [...previous, event].slice(-200));
      void getJob(selectedJobId).then((response) => {
        setJobs((previous) =>
          previous.map((item) => (item.job_id === response.job.job_id ? response.job : item))
        );
      });
      void getRuns().then((response) => setRuns(response.runs));
    });
    return unsubscribe;
  }, [selectedJobId]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    void Promise.all([getRun(selectedRunId), getRunResults(selectedRunId)])
      .then(([runResponse, resultResponse]) => {
        setRunSummary(runResponse.summary);
        setRunResults(resultResponse.results);
      })
      .catch(() => {
        setRunSummary(null);
        setRunResults(null);
      });
  }, [selectedRunId]);

  const activeJob = useMemo(
    () => jobs.find((job) => job.job_id === selectedJobId) ?? null,
    [jobs, selectedJobId]
  );

  async function refreshAll() {
    const [healthResponse, modelsResponse, jobsResponse, runsResponse, presetsResponse, systemResponse] =
      await Promise.all([getHealth(), getModels(), getJobs(), getRuns(), getPresets(), getSystem()]);
    setHealth(healthResponse.provider);
    setModels(modelsResponse.models);
    setJobs(jobsResponse.jobs);
    setRuns(runsResponse.runs);
    setPresets(presetsResponse.presets);
    setSystem(systemResponse);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    try {
      let response: { job: JobRecord };
      if (benchmarkKind === "solo") {
        response = await submitSoloBenchmark({
          name: "web-solo-benchmark",
          models: selectedModels,
          dataset_path: soloDataset,
          repetitions,
          warmup_runs: warmupRuns,
          options: { temperature: 0 }
        });
      } else if (benchmarkKind === "pairwise") {
        response = await submitPairwiseBenchmark({
          name: "web-pairwise-benchmark",
          left_model: leftModel,
          right_model: rightModel,
          dataset_path: pairwiseDataset,
          repetitions,
          warmup_runs: warmupRuns,
          options: { temperature: 0 }
        });
      } else {
        response = await submitStressBenchmark({
          name: "web-stress-benchmark",
          models: selectedModels,
          standard_dataset_path: standardDataset,
          reasoning_dataset_path: reasoningDataset,
          repetitions,
          warmup_runs: warmupRuns,
          options: { temperature: 0 }
        });
      }

      setSelectedJobId(response.job.job_id);
      setJobEvents([]);
      setTab("jobs");
      await refreshAll();
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Request failed");
    } finally {
      setSubmitting(false);
    }
  }

  function toggleModel(modelId: string) {
    setSelectedModels((current) =>
      current.includes(modelId) ? current.filter((item) => item !== modelId) : [...current, modelId]
    );
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Jemma SafeBrain Command</p>
          <h1>Mission Control</h1>
          <p className="hero-copy">
            Local Gemma benchmarking, live run telemetry, and public-demo-safe orchestration on the 5090 workstation.
          </p>
        </div>
        <div className="hero-meta">
          <span className={`badge ${health?.ok ? "badge-ok" : "badge-warn"}`}>
            Provider: {health?.ok ? "healthy" : "degraded"}
          </span>
          <span className="badge">Public demo: facade only</span>
        </div>
      </header>

      <nav className="tabs">
        {(["overview", "benchmarks", "jobs", "runs", "system"] as TabName[]).map((item) => (
          <button
            key={item}
            className={item === tab ? "tab active" : "tab"}
            onClick={() => setTab(item)}
            type="button"
          >
            {item}
          </button>
        ))}
        <button className="tab tab-refresh" onClick={() => void refreshAll()} type="button">
          refresh
        </button>
      </nav>

      {tab === "overview" && (
        <section className="grid two-up">
          <Card title="Health">
            <KeyValue label="Provider" value={health?.provider ?? "unknown"} />
            <KeyValue label="Detail" value={health?.detail ?? "unavailable"} />
            <KeyValue label="Discovered models" value={String(health?.models.length ?? 0)} />
          </Card>
          <Card title="System snapshot">
            <KeyValue label="Captured" value={system?.captured_at ?? "unknown"} />
            <KeyValue
              label="GPU telemetry"
              value={String(system?.gpu_runtime?.available ?? false)}
            />
            <KeyValue
              label="Process metrics"
              value={String(system?.process?.available ?? false)}
            />
          </Card>
          <Card title="Available models">
            <div className="chip-row">
              {models.map((model) => (
                <span key={model.model_id} className="chip">
                  {model.model_id}
                </span>
              ))}
            </div>
          </Card>
          <Card title="Preset suites">
            <ul className="list">
              {presets.map((preset) => (
                <li key={preset.name}>
                  <strong>{preset.name}</strong> - {preset.kind}
                </li>
              ))}
            </ul>
          </Card>
        </section>
      )}

      {tab === "benchmarks" && (
        <section className="grid two-up">
          <Card title="Launch benchmark">
            <form className="form" onSubmit={(event) => void handleSubmit(event)}>
              <label>
                Benchmark type
                <select value={benchmarkKind} onChange={(event) => setBenchmarkKind(event.target.value as typeof benchmarkKind)}>
                  <option value="stress">Stress (standard vs reasoning)</option>
                  <option value="solo">Solo</option>
                  <option value="pairwise">Pairwise</option>
                </select>
              </label>

              {(benchmarkKind === "stress" || benchmarkKind === "solo") && (
                <label>
                  Model pool
                  <div className="checkbox-grid">
                    {models.map((model) => (
                      <label key={model.model_id} className="checkbox-card">
                        <input
                          type="checkbox"
                          checked={selectedModels.includes(model.model_id)}
                          onChange={() => toggleModel(model.model_id)}
                        />
                        <span>{model.model_id}</span>
                      </label>
                    ))}
                  </div>
                </label>
              )}

              {benchmarkKind === "pairwise" && (
                <>
                  <label>
                    Left model
                    <select value={leftModel} onChange={(event) => setLeftModel(event.target.value)}>
                      {models.map((model) => (
                        <option key={model.model_id} value={model.model_id}>
                          {model.model_id}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Right model
                    <select value={rightModel} onChange={(event) => setRightModel(event.target.value)}>
                      {models.map((model) => (
                        <option key={model.model_id} value={model.model_id}>
                          {model.model_id}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              )}

              {benchmarkKind === "solo" && (
                <label>
                  Dataset path
                  <input value={soloDataset} onChange={(event) => setSoloDataset(event.target.value)} />
                </label>
              )}

              {benchmarkKind === "pairwise" && (
                <label>
                  Dataset path
                  <input value={pairwiseDataset} onChange={(event) => setPairwiseDataset(event.target.value)} />
                </label>
              )}

              {benchmarkKind === "stress" && (
                <>
                  <label>
                    Standard dataset
                    <input value={standardDataset} onChange={(event) => setStandardDataset(event.target.value)} />
                  </label>
                  <label>
                    Reasoning dataset
                    <input value={reasoningDataset} onChange={(event) => setReasoningDataset(event.target.value)} />
                  </label>
                </>
              )}

              <label>
                Repetitions
                <input
                  type="number"
                  min={1}
                  value={repetitions}
                  onChange={(event) => setRepetitions(Number(event.target.value))}
                />
              </label>
              <label>
                Warmup runs
                <input
                  type="number"
                  min={0}
                  value={warmupRuns}
                  onChange={(event) => setWarmupRuns(Number(event.target.value))}
                />
              </label>
              <button disabled={submitting} type="submit">
                {submitting ? "Submitting..." : "Start benchmark"}
              </button>
              {submitError && <p className="error">{submitError}</p>}
            </form>
          </Card>
          <Card title="Launch guidance">
            <ul className="list">
              <li>Keep Ollama private; expose only the web/demo facade publicly.</li>
              <li>Use stress mode to compare standard vs reasoning-style prompt suites.</li>
              <li>Start with quantized defaults, then add BF16 baselines for quality/latency tradeoffs.</li>
            </ul>
          </Card>
        </section>
      )}

      {tab === "jobs" && (
        <section className="grid two-up">
          <Card title="Jobs">
            <div className="table">
              {jobs.map((job) => (
                <button
                  key={job.job_id}
                  className={job.job_id === selectedJobId ? "row selected" : "row"}
                  onClick={() => {
                    setSelectedJobId(job.job_id);
                    setJobEvents([]);
                  }}
                  type="button"
                >
                  <span>{job.job_id}</span>
                  <span>{job.kind}</span>
                  <span>{job.status}</span>
                  <span>
                    {job.completed_steps}/{job.total_steps}
                  </span>
                </button>
              ))}
            </div>
          </Card>
          <Card title="Live job detail">
            {activeJob ? (
              <>
                <KeyValue label="Phase" value={activeJob.current_phase} />
                <KeyValue label="Models" value={activeJob.models.join(", ")} />
                <KeyValue label="Prompt style" value={activeJob.prompt_style} />
                <KeyValue
                  label="Progress"
                  value={`${activeJob.completed_steps}/${activeJob.total_steps}`}
                />
                <ProgressBar
                  value={
                    activeJob.total_steps > 0
                      ? Math.min(100, Math.round((activeJob.completed_steps / activeJob.total_steps) * 100))
                      : 0
                  }
                />
                <div className="event-log">
                  {jobEvents.length === 0 && <p>No live events yet.</p>}
                  {jobEvents.map((event) => (
                    <div key={`${event.sequence}-${event.type}`} className="event-row">
                      <strong>{event.type}</strong>
                      <code>{JSON.stringify(event.payload)}</code>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p>Select a job to inspect live progress.</p>
            )}
          </Card>
        </section>
      )}

      {tab === "runs" && (
        <section className="grid two-up">
          <Card title="Completed runs">
            <div className="table">
              {runs.map((run) => (
                <button
                  key={run.run_id}
                  className={run.run_id === selectedRunId ? "row selected" : "row"}
                  onClick={() => setSelectedRunId(run.run_id)}
                  type="button"
                >
                  <span>{run.name}</span>
                  <span>{run.kind}</span>
                  <span>{run.created_at}</span>
                </button>
              ))}
            </div>
          </Card>
          <Card title="Run summary">
            {selectedRunId ? (
              <>
                <KeyValue label="Run ID" value={selectedRunId} />
                <pre>{JSON.stringify(runSummary, null, 2)}</pre>
                <h3>Raw results preview</h3>
                <pre>{JSON.stringify(runResults?.slice(0, 5) ?? [], null, 2)}</pre>
              </>
            ) : (
              <p>Select a run to inspect its summary and results.</p>
            )}
          </Card>
        </section>
      )}

      {tab === "system" && (
        <section className="grid two-up">
          <Card title="Runtime telemetry">
            <pre>{JSON.stringify(system, null, 2)}</pre>
          </Card>
          <Card title="Optimization cues">
            <ul className="list">
              <li>Capture TTFT, avg latency, pass rate, and VRAM usage for every headline demo run.</li>
              <li>Compare q8/q4 defaults first, then BF16 baselines only where quality gains justify the cost.</li>
              <li>Use the public UI as a restricted facade; keep raw provider and LAN surfaces private.</li>
            </ul>
          </Card>
        </section>
      )}
    </div>
  );
}

function Card(props: { title: string; children: ReactNode }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>{props.title}</h2>
      </div>
      <div className="card-body">{props.children}</div>
    </div>
  );
}

function KeyValue(props: { label: string; value: string }) {
  return (
    <div className="kv">
      <span>{props.label}</span>
      <strong>{props.value}</strong>
    </div>
  );
}

function ProgressBar(props: { value: number }) {
  return (
    <div className="progress">
      <div className="progress-fill" style={{ width: `${props.value}%` }} />
    </div>
  );
}

