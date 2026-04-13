import { FormEvent, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

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
  getTrainingStatus,
  sendChat,
  startTraining,
  stopTraining,
  streamChat,
  submitPairwiseBenchmark,
  submitSoloBenchmark,
  submitStressBenchmark,
  subscribeJobEvents,
} from "./api";
import type {
  BenchmarkPreset,
  ChatMessage,
  ChatResponse,
  Gemma4ModelInfo,
  JobEvent,
  JobRecord,
  ModelSpec,
  ProviderHealth,
  RunRecord,
  SystemPayload,
  TrainingStatus,
} from "./types";
import { GEMMA4_MODELS, TOTAL_VRAM_GB } from "./types";

// ===========================================================================
// Tab types
// ===========================================================================

type TabName = "models" | "chat" | "train" | "bench";

// ===========================================================================
// Main App
// ===========================================================================

export default function App() {
  const [tab, setTab] = useState<TabName>("models");
  const [health, setHealth] = useState<ProviderHealth | null>(null);
  const [models, setModels] = useState<ModelSpec[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [presets, setPresets] = useState<BenchmarkPreset[]>([]);
  const [system, setSystem] = useState<SystemPayload | null>(null);

  const refreshAll = useCallback(async () => {
    const [h, m, j, r, p, s] = await Promise.all([
      getHealth(),
      getModels(),
      getJobs(),
      getRuns(),
      getPresets(),
      getSystem(),
    ]);
    setHealth(h.provider);
    setModels(m.models);
    setJobs(j.jobs);
    setRuns(r.runs);
    setPresets(p.presets);
    setSystem(s);
  }, []);

  useEffect(() => {
    void refreshAll();
  }, [refreshAll]);

  const healthStatus = health?.ok ? "healthy" : health ? "degraded" : "offline";

  return (
    <div className="app-shell">
      {/* --- Top bar --- */}
      <header className="top-bar">
        <div className="top-bar-logo" />
        <h1>Jemma SafeBrain</h1>
        <div className="top-bar-status">
          <span className={`status-dot ${healthStatus === "healthy" ? "" : healthStatus}`} />
          <span className="status-label">
            {health?.provider ?? "connecting"} Â· {healthStatus}
          </span>
        </div>
      </header>

      {/* --- Tab navigation --- */}
      <nav className="tab-nav">
        {(["models", "chat", "train", "bench"] as TabName[]).map((t) => (
          <button
            key={t}
            className={t === tab ? "tab-btn active" : "tab-btn"}
            onClick={() => setTab(t)}
            type="button"
          >
            {t === "models" ? "Models" : t === "chat" ? "Chat" : t === "train" ? "Train" : "Bench"}
          </button>
        ))}
      </nav>

      {/* --- Tab content --- */}
      {tab === "models" && <ModelsTab models={models} health={health} system={system} />}
      {tab === "chat" && <ChatTab models={models} />}
      {tab === "train" && <TrainTab models={models} />}
      {tab === "bench" && (
        <BenchTab
          models={models}
          jobs={jobs}
          runs={runs}
          presets={presets}
          onRefresh={refreshAll}
          setJobs={setJobs}
          setRuns={setRuns}
        />
      )}
    </div>
  );
}

// ===========================================================================
// Models Tab
// ===========================================================================

function ModelsTab(props: {
  models: ModelSpec[];
  health: ProviderHealth | null;
  system: SystemPayload | null;
}) {
  const { models, health } = props;
  const loadedModels = health?.models ?? [];

  return (
    <section>
      {/* VRAM overview */}
      <div className="card mb-16">
        <div className="card-header">
          <h2>RTX 5090 Â· {TOTAL_VRAM_GB} GB VRAM</h2>
        </div>
        <div className="card-body">
          <VramBar usedGb={0} totalGb={TOTAL_VRAM_GB} />
          <div className="text-sm text-variant mt-12">
            {models.length} registered models Â· {loadedModels.length} loaded in Ollama
          </div>
        </div>
      </div>

      {/* Gemma 4 catalog */}
      <div className="grid three-up">
        {GEMMA4_MODELS.map((info) => {
          const isLoaded = loadedModels.some(
            (m) => m === info.ollama_tag || m.startsWith(info.ollama_tag.split(":")[0])
          );
          return <ModelCard key={info.id} info={info} loaded={isLoaded} />;
        })}
      </div>

      {/* Registered models from config */}
      {models.length > 0 && (
        <div className="card mt-16">
          <div className="card-header">
            <h2>Registered Models (config)</h2>
          </div>
          <div className="card-body">
            <div className="chip-row">
              {models.map((m) => (
                <span key={m.model_id} className="chip">
                  {m.model_id} Â· {m.provider}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function ModelCard(props: { info: Gemma4ModelInfo; loaded: boolean }) {
  const { info, loaded } = props;
  const vramPercent = (info.vram_q4 / TOTAL_VRAM_GB) * 100;
  const fits = info.vram_q4 <= TOTAL_VRAM_GB;

  return (
    <div className="model-card">
      <div className="model-card-header">
        <div>
          <h3 className="model-card-name">{info.name}</h3>
          <p className="model-card-subtitle">{info.subtitle}</p>
        </div>
        <span className={`model-badge ${loaded ? "badge-loaded" : "badge-available"}`}>
          {loaded ? "Loaded" : "Available"}
        </span>
      </div>

      <div className="chip-row">
        {info.modalities.map((m) => (
          <span key={m} className="chip">{m}</span>
        ))}
        <span className="chip">{info.context_window} ctx</span>
        <span className="chip">{info.architecture}</span>
      </div>

      <div className="vram-bar-container">
        <div className="vram-bar-label">
          <span>Q4_K_M: {info.vram_q4} GB</span>
          <span>Q8: {info.vram_q8} GB</span>
          <span>BF16: {info.vram_bf16} GB</span>
        </div>
        <div className="vram-bar">
          <div
            className={`vram-bar-fill ${vramPercent > 85 ? "warning" : ""}`}
            style={{ width: `${Math.min(100, vramPercent)}%` }}
          />
        </div>
        <div className="vram-bar-label">
          <span>{fits ? "âœ“ Fits in VRAM (Q4)" : "âš  Requires offload"}</span>
          <span>{TOTAL_VRAM_GB} GB total</span>
        </div>
      </div>

      <code className="model-card-cmd">
        ollama run {info.ollama_tag}
      </code>
    </div>
  );
}

// ===========================================================================
// Chat Tab
// ===========================================================================

type UiMessage = {
  role: "user" | "assistant";
  content: string;
  images?: string[];
  meta?: { model: string; durationMs: number | null; tokens: number | null };
};

function ChatTab(props: { models: ModelSpec[] }) {
  const { models } = props;
  const [chatModel, setChatModel] = useState(models[0]?.model_id ?? "gemma4:latest");
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const [imageData, setImageData] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (models.length > 0 && !models.find((m) => m.model_id === chatModel)) {
      setChatModel(models[0].model_id);
    }
  }, [models, chatModel]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamContent]);

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;

    const userMsg: UiMessage = { role: "user", content: text, images: imageData ? [imageData] : undefined };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setImageData(null);
    setSending(true);
    setStreamContent("");

    const apiMessages: ChatMessage[] = [...messages, userMsg].map((m) => ({
      role: m.role,
      content: m.content,
      images: m.images,
    }));

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await streamChat(
        chatModel,
        apiMessages,
        (token) => setStreamContent((prev) => prev + token),
        controller.signal,
      );

      setStreamContent("");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.content,
          meta: {
            model: response.model,
            durationMs: response.total_duration_ms ?? null,
            tokens: response.eval_count ?? null,
          },
        },
      ]);
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setStreamContent("");
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${(err as Error).message}` },
        ]);
      }
    } finally {
      setSending(false);
      abortRef.current = null;
    }
  }

  function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    // Validate file type
    if (!file.type.startsWith("image/")) return;
    // Limit to 10MB
    if (file.size > 10 * 1024 * 1024) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Extract base64 data after the comma
      setImageData(result.split(",")[1] ?? result);
    };
    reader.readAsDataURL(file);
    // Reset the input so the same file can be selected again
    e.target.value = "";
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  return (
    <div className="chat-container">
      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 && !streamContent && (
          <div className="empty-state">
            <div className="empty-state-icon">ðŸ’¬</div>
            <p>Start a conversation with Gemma 4</p>
            <p className="text-sm">Supports text, images, and multimodal prompts</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <div className="chat-msg-avatar">
              {msg.role === "assistant" ? "G" : "U"}
            </div>
            <div>
              <div className="chat-msg-bubble">
                {msg.images?.length ? (
                  <img
                    className="chat-image-preview"
                    src={`data:image/jpeg;base64,${msg.images[0]}`}
                    alt="uploaded"
                  />
                ) : null}
                {msg.content}
              </div>
              {msg.meta && (
                <div className="chat-msg-meta">
                  {msg.meta.model}
                  {msg.meta.durationMs != null && ` Â· ${msg.meta.durationMs}ms`}
                  {msg.meta.tokens != null && ` Â· ${msg.meta.tokens} tokens`}
                </div>
              )}
            </div>
          </div>
        ))}
        {streamContent && (
          <div className="chat-msg assistant">
            <div className="chat-msg-avatar">G</div>
            <div>
              <div className="chat-msg-bubble">{streamContent}â–Š</div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        <div className="chat-toolbar">
          <select
            className="model-select"
            value={chatModel}
            onChange={(e) => setChatModel(e.target.value)}
            title="Select model"
          >
            {models.map((m) => (
              <option key={m.model_id} value={m.model_id}>{m.model_id}</option>
            ))}
            {models.length === 0 && <option value="gemma4:latest">gemma4:latest</option>}
          </select>
          <button
            className="icon-btn"
            onClick={() => fileInputRef.current?.click()}
            title="Attach image"
            type="button"
          >
            ðŸ“Ž
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleImageUpload}
            title="Upload image"
          />
          {sending && (
            <button
              className="icon-btn"
              onClick={() => abortRef.current?.abort()}
              title="Stop generation"
              type="button"
            >
              â¹
            </button>
          )}
        </div>

        {imageData && (
          <div className="chat-image-thumb mb-8">
            <img src={`data:image/jpeg;base64,${imageData}`} alt="preview" />
            <button className="chat-image-remove" onClick={() => setImageData(null)} type="button">
              âœ•
            </button>
          </div>
        )}

        <div className="chat-input-row">
          <textarea
            className="chat-input"
            placeholder="Message Gemma 4..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
          />
          <button
            className="icon-btn primary"
            onClick={() => void handleSend()}
            disabled={sending || !input.trim()}
            title="Send"
            type="button"
          >
            â†‘
          </button>
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// Train Tab
// ===========================================================================

function TrainTab(props: { models: ModelSpec[] }) {
  const { models } = props;
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const [baseModel, setBaseModel] = useState("gemma4:latest");
  const [dataset, setDataset] = useState("datasets/prompts/safety-benchmark.jsonl");
  const [method, setMethod] = useState<"qlora" | "lora">("qlora");
  const [maxSteps, setMaxSteps] = useState(200);
  const [lr, setLr] = useState(0.0002);
  const [loraRank, setLoraRank] = useState(32);
  const [loraAlpha, setLoraAlpha] = useState(8);
  const [batchSize, setBatchSize] = useState(2);
  const [maxSeqLen, setMaxSeqLen] = useState(8192);
  const [outputName, setOutputName] = useState("jemma-safety-e4b");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Poll training status
  useEffect(() => {
    const interval = setInterval(() => {
      getTrainingStatus()
        .then(setStatus)
        .catch(() => setStatus(null));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  async function handleStart() {
    setStarting(true);
    setError(null);
    try {
      await startTraining({
        base_model: baseModel,
        dataset_path: dataset,
        method,
        max_steps: maxSteps,
        learning_rate: lr,
        lora_rank: loraRank,
        lora_alpha: loraAlpha,
        batch_size: batchSize,
        max_seq_length: maxSeqLen,
        output_name: outputName,
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setStarting(false);
    }
  }

  async function handleStop() {
    try {
      await stopTraining();
    } catch {
      // ignore
    }
  }

  const isActive = status?.active ?? false;
  const progress = status && status.total_steps > 0
    ? Math.round((status.current_step / status.total_steps) * 100)
    : 0;

  return (
    <div className="train-layout">
      {/* Sidebar â€” config */}
      <div className="train-sidebar">
        <div className="card">
          <div className="card-header"><h2>Training Config</h2></div>
          <div className="card-body">
            <div className="form">
              <label>
                Base Model
                <select value={baseModel} onChange={(e) => setBaseModel(e.target.value)}>
                  {models.map((m) => (
                    <option key={m.model_id} value={m.model_id}>{m.model_id}</option>
                  ))}
                  {models.length === 0 && <option>gemma4:latest</option>}
                </select>
              </label>
              <label>
                Dataset
                <input value={dataset} onChange={(e) => setDataset(e.target.value)} />
              </label>
              <label>
                Method
                <select value={method} onChange={(e) => setMethod(e.target.value as "qlora" | "lora")}>
                  <option value="qlora">Unsloth QLoRA (4-bit)</option>
                  <option value="lora">Standard LoRA</option>
                </select>
              </label>
              <label>
                Max Steps
                <input type="number" min={1} value={maxSteps} onChange={(e) => setMaxSteps(Number(e.target.value))} />
              </label>
              <label>
                Learning Rate
                <input type="number" step={0.00001} value={lr} onChange={(e) => setLr(Number(e.target.value))} />
              </label>
              <label>
                LoRA Rank
                <input type="number" min={1} value={loraRank} onChange={(e) => setLoraRank(Number(e.target.value))} />
              </label>
              <label>
                LoRA Alpha
                <input type="number" min={1} value={loraAlpha} onChange={(e) => setLoraAlpha(Number(e.target.value))} />
              </label>
              <label>
                Batch Size
                <input type="number" min={1} value={batchSize} onChange={(e) => setBatchSize(Number(e.target.value))} />
              </label>
              <label>
                Max Seq Length
                <input type="number" min={128} value={maxSeqLen} onChange={(e) => setMaxSeqLen(Number(e.target.value))} />
              </label>
              <label>
                Output Name
                <input value={outputName} onChange={(e) => setOutputName(e.target.value)} />
              </label>

              {!isActive ? (
                <button className="btn btn-primary" onClick={() => void handleStart()} disabled={starting} type="button">
                  {starting ? "Starting..." : "Start Training"}
                </button>
              ) : (
                <button className="btn btn-outlined" onClick={() => void handleStop()} type="button">
                  Stop Training
                </button>
              )}
              {error && <p className="error">{error}</p>}
            </div>
          </div>
        </div>
      </div>

      {/* Main â€” metrics + logs */}
      <div className="train-main">
        {/* Metrics */}
        <div className="train-metric-grid">
          <div className="train-metric">
            <div className="train-metric-value">{status?.current_step ?? 0}</div>
            <div className="train-metric-label">Step</div>
          </div>
          <div className="train-metric">
            <div className="train-metric-value">{status?.loss?.toFixed(4) ?? "â€”"}</div>
            <div className="train-metric-label">Loss</div>
          </div>
          <div className="train-metric">
            <div className="train-metric-value">{status?.learning_rate?.toExponential(2) ?? "â€”"}</div>
            <div className="train-metric-label">LR</div>
          </div>
          <div className="train-metric">
            <div className="train-metric-value">
              {status?.eta_s != null ? `${Math.round(status.eta_s / 60)}m` : "â€”"}
            </div>
            <div className="train-metric-label">ETA</div>
          </div>
        </div>

        {/* Progress */}
        {isActive && (
          <div className="card">
            <div className="card-header">
              <h2>Progress Â· {progress}%</h2>
            </div>
            <div className="card-body">
              <div className="progress">
                <div className="progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <div className="text-sm text-variant">
                {status?.method} Â· {status?.model} Â· step {status?.current_step}/{status?.total_steps}
              </div>
            </div>
          </div>
        )}

        {/* Logs */}
        <div className="card flex-1">
          <div className="card-header"><h2>Training Log</h2></div>
          <div className="card-body">
            <div className="train-log">
              {status?.logs?.length ? (
                status.logs.map((line, i) => <div key={i}>{line}</div>)
              ) : (
                <div className="text-outline">
                  No training in progress. Configure parameters and click Start Training.
                  {"\n\n"}Tip: For notebook-driven training, use the Unsloth notebook:
                  {"\n"}  gemma4-31b-unsloth-local-5090.ipynb
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// Bench Tab (restyled from original)
// ===========================================================================

function BenchTab(props: {
  models: ModelSpec[];
  jobs: JobRecord[];
  runs: RunRecord[];
  presets: BenchmarkPreset[];
  onRefresh: () => Promise<void>;
  setJobs: React.Dispatch<React.SetStateAction<JobRecord[]>>;
  setRuns: React.Dispatch<React.SetStateAction<RunRecord[]>>;
}) {
  const { models, jobs, runs, presets, onRefresh, setJobs, setRuns } = props;
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
  const [soloDataset, setSoloDataset] = useState("datasets/prompts/smoke.jsonl");
  const [pairwiseDataset, setPairwiseDataset] = useState("datasets/prompts/qa.jsonl");
  const [standardDataset, setStandardDataset] = useState("datasets/prompts/stress-standard.jsonl");
  const [reasoningDataset, setReasoningDataset] = useState("datasets/prompts/stress-reasoning.jsonl");
  const [repetitions, setRepetitions] = useState(1);
  const [warmupRuns, setWarmupRuns] = useState(1);

  useEffect(() => {
    if (models.length > 0 && selectedModels.length === 0) {
      setSelectedModels(models.slice(0, Math.min(3, models.length)).map((m) => m.model_id));
      setLeftModel(models[0]?.model_id ?? "");
      setRightModel(models[1]?.model_id ?? models[0]?.model_id ?? "");
    }
  }, [models, selectedModels.length]);

  useEffect(() => {
    if (!selectedJobId) return undefined;
    const unsubscribe = subscribeJobEvents(selectedJobId, (event) => {
      setJobEvents((prev) => [...prev, event].slice(-200));
      void getJob(selectedJobId).then((r) => {
        setJobs((prev) => prev.map((j) => (j.job_id === r.job.job_id ? r.job : j)));
      });
      void getRuns().then((r) => setRuns(r.runs));
    });
    return unsubscribe;
  }, [selectedJobId, setJobs, setRuns]);

  useEffect(() => {
    if (!selectedRunId) return;
    void Promise.all([getRun(selectedRunId), getRunResults(selectedRunId)])
      .then(([runResp, resultResp]) => {
        setRunSummary(runResp.summary);
        setRunResults(resultResp.results);
      })
      .catch(() => {
        setRunSummary(null);
        setRunResults(null);
      });
  }, [selectedRunId]);

  const activeJob = useMemo(
    () => jobs.find((j) => j.job_id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );

  function toggleModel(modelId: string) {
    setSelectedModels((cur) =>
      cur.includes(modelId) ? cur.filter((m) => m !== modelId) : [...cur, modelId],
    );
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
          options: { temperature: 0 },
        });
      } else if (benchmarkKind === "pairwise") {
        response = await submitPairwiseBenchmark({
          name: "web-pairwise-benchmark",
          left_model: leftModel,
          right_model: rightModel,
          dataset_path: pairwiseDataset,
          repetitions,
          warmup_runs: warmupRuns,
          options: { temperature: 0 },
        });
      } else {
        response = await submitStressBenchmark({
          name: "web-stress-benchmark",
          models: selectedModels,
          standard_dataset_path: standardDataset,
          reasoning_dataset_path: reasoningDataset,
          repetitions,
          warmup_runs: warmupRuns,
          options: { temperature: 0 },
        });
      }
      setSelectedJobId(response.job.job_id);
      setJobEvents([]);
      await onRefresh();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSubmitting(false);
    }
  }

  // Build chart data from run summary
  const chartData = useMemo(() => {
    if (!runSummary) return [];
    const data: Array<Record<string, unknown>> = [];
    // Try to extract per-model latency data
    for (const [key, val] of Object.entries(runSummary)) {
      if (typeof val === "object" && val !== null && "avg_latency_ms" in (val as Record<string, unknown>)) {
        const v = val as Record<string, unknown>;
        data.push({
          model: key,
          avg_latency_ms: v.avg_latency_ms,
          p95_latency_ms: v.p95_latency_ms ?? 0,
          tokens_per_sec: v.tokens_per_sec ?? 0,
        });
      }
    }
    return data;
  }, [runSummary]);

  return (
    <section>
      <div className="grid two-up">
        {/* Left: Launch */}
        <Card title="Launch Benchmark">
          <form className="form" onSubmit={(e) => void handleSubmit(e)}>
            <label>
              Benchmark type
              <select value={benchmarkKind} onChange={(e) => setBenchmarkKind(e.target.value as typeof benchmarkKind)}>
                <option value="stress">Stress (standard + reasoning)</option>
                <option value="solo">Solo</option>
                <option value="pairwise">Pairwise</option>
              </select>
            </label>

            {(benchmarkKind === "stress" || benchmarkKind === "solo") && (
              <label>
                Model pool
                <div className="checkbox-grid">
                  {models.map((m) => (
                    <label key={m.model_id} className="checkbox-card">
                      <input
                        type="checkbox"
                        checked={selectedModels.includes(m.model_id)}
                        onChange={() => toggleModel(m.model_id)}
                      />
                      <span>{m.model_id}</span>
                    </label>
                  ))}
                </div>
              </label>
            )}

            {benchmarkKind === "pairwise" && (
              <>
                <label>
                  Left model
                  <select value={leftModel} onChange={(e) => setLeftModel(e.target.value)}>
                    {models.map((m) => (
                      <option key={m.model_id} value={m.model_id}>{m.model_id}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Right model
                  <select value={rightModel} onChange={(e) => setRightModel(e.target.value)}>
                    {models.map((m) => (
                      <option key={m.model_id} value={m.model_id}>{m.model_id}</option>
                    ))}
                  </select>
                </label>
              </>
            )}

            {benchmarkKind === "solo" && (
              <label>
                Dataset path
                <input value={soloDataset} onChange={(e) => setSoloDataset(e.target.value)} />
              </label>
            )}

            {benchmarkKind === "pairwise" && (
              <label>
                Dataset path
                <input value={pairwiseDataset} onChange={(e) => setPairwiseDataset(e.target.value)} />
              </label>
            )}

            {benchmarkKind === "stress" && (
              <>
                <label>
                  Standard dataset
                  <input value={standardDataset} onChange={(e) => setStandardDataset(e.target.value)} />
                </label>
                <label>
                  Reasoning dataset
                  <input value={reasoningDataset} onChange={(e) => setReasoningDataset(e.target.value)} />
                </label>
              </>
            )}

            <label>
              Repetitions
              <input type="number" min={1} value={repetitions} onChange={(e) => setRepetitions(Number(e.target.value))} />
            </label>
            <label>
              Warmup runs
              <input type="number" min={0} value={warmupRuns} onChange={(e) => setWarmupRuns(Number(e.target.value))} />
            </label>
            <button className="btn btn-primary" disabled={submitting} type="submit">
              {submitting ? "Submitting..." : "Start Benchmark"}
            </button>
            {submitError && <p className="error">{submitError}</p>}
          </form>
        </Card>

        {/* Right: Job detail or chart */}
        <div className="flex-col">
          {/* Active job */}
          <Card title="Live Job">
            {activeJob ? (
              <>
                <KeyValue label="Phase" value={activeJob.current_phase} />
                <KeyValue label="Models" value={activeJob.models.join(", ")} />
                <KeyValue label="Status" value={activeJob.status} />
                <div className="progress">
                  <div
                    className="progress-fill"
                    style={{
                      width: `${activeJob.total_steps > 0 ? Math.min(100, Math.round((activeJob.completed_steps / activeJob.total_steps) * 100)) : 0}%`,
                    }}
                  />
                </div>
                <div className="event-log">
                  {jobEvents.length === 0 && <p className="text-outline">Waiting for events...</p>}
                  {jobEvents.slice(-10).map((ev) => (
                    <div key={`${ev.sequence}-${ev.type}`} className="event-row">
                      <strong>{ev.type}</strong> <code>{JSON.stringify(ev.payload)}</code>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-outline">Launch a benchmark to see live progress.</p>
            )}
          </Card>

          {/* Results chart */}
          {chartData.length > 0 && (
            <Card title="Results">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--md-sys-color-outline-variant)" />
                  <XAxis dataKey="model" />
                  <YAxis />
                  <Tooltip
                    contentStyle={{
                      background: "var(--md-sys-color-surface-container)",
                      border: "1px solid var(--md-sys-color-outline-variant)",
                      borderRadius: 8,
                    }}
                  />
                  <Legend />
                  <Bar dataKey="avg_latency_ms" fill="var(--md-sys-color-primary)" name="Avg Latency (ms)" />
                  <Bar dataKey="tokens_per_sec" fill="var(--md-sys-color-tertiary)" name="Tokens/sec" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}
        </div>
      </div>

      {/* Jobs + Runs tables */}
      <div className="grid two-up mt-16">
        <Card title={`Jobs (${jobs.length})`}>
          <div className="table">
            {jobs.map((job) => (
              <button
                key={job.job_id}
                className={job.job_id === selectedJobId ? "row selected" : "row"}
                onClick={() => { setSelectedJobId(job.job_id); setJobEvents([]); }}
                type="button"
              >
                <span>{job.job_id.slice(0, 8)}</span>
                <span>{job.kind}</span>
                <span>{job.status}</span>
                <span>{job.completed_steps}/{job.total_steps}</span>
              </button>
            ))}
            {jobs.length === 0 && <p className="text-outline">No jobs yet.</p>}
          </div>
        </Card>

        <Card title={`Runs (${runs.length})`}>
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
                <span>â†’</span>
              </button>
            ))}
            {runs.length === 0 && <p className="text-outline">No runs yet.</p>}
          </div>
          {selectedRunId && runSummary && (
            <div className="mt-12">
              <pre>{JSON.stringify(runSummary, null, 2)}</pre>
            </div>
          )}
        </Card>
      </div>

      {/* Presets */}
      {presets.length > 0 && (
        <div className="card mt-16">
          <div className="card-header"><h2>Preset Suites</h2></div>
          <div className="card-body">
            <div className="chip-row">
              {presets.map((p) => (
                <span key={p.name} className="chip">{p.name} ({p.kind})</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

// ===========================================================================
// Shared Components
// ===========================================================================

function Card(props: { title: string; children: ReactNode }) {
  return (
    <div className="card">
      <div className="card-header"><h2>{props.title}</h2></div>
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

function VramBar(props: { usedGb: number; totalGb: number }) {
  const pct = Math.min(100, (props.usedGb / props.totalGb) * 100);
  return (
    <div className="vram-bar-container">
      <div className="vram-bar-label">
        <span>{props.usedGb.toFixed(1)} GB used</span>
        <span>{props.totalGb} GB total</span>
      </div>
      <div className="vram-bar">
        <div className={`vram-bar-fill ${pct > 85 ? "warning" : ""}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
