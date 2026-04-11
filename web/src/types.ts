export type ProviderHealth = {
  provider: string;
  ok: boolean;
  detail: string;
  models: string[];
};

export type ChatMessage = {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
};

export type ChatRequest = {
  model?: string;
  system?: string;
  messages: ChatMessage[];
  options?: Record<string, unknown>;
  response_format?: "json" | null;
  timeout_s?: number;
};

export type ChatResponse = {
  model: string;
  content: string;
  raw: Record<string, unknown>;
  total_duration_ms?: number | null;
  prompt_eval_count?: number | null;
  eval_count?: number | null;
};

export type CapabilityDescriptor = {
  name: string;
  actions: string[];
  allowlisted_targets: string[];
  require_confirmation: boolean;
  summary: string;
};

export type ModelSpec = {
  model_id: string;
  provider: string;
  remote_name: string;
  context_window: number;
  quantization?: string | null;
  tags: string[];
};

export type JobRecord = {
  job_id: string;
  kind: string;
  status: string;
  visibility: string;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  current_phase: string;
  total_steps: number;
  completed_steps: number;
  models: string[];
  run_ids: string[];
  prompt_style: string;
  error?: string | null;
  summary: Record<string, unknown>;
};

export type RunRecord = {
  run_id: string;
  kind: string;
  name: string;
  created_at: string;
  artifact_dir: string;
};

export type JobEvent = {
  sequence: number;
  type: string;
  created_at: string;
  payload: Record<string, unknown>;
};

export type BenchmarkPreset = {
  name: string;
  kind: string;
  manifest_path: string;
};

export type SystemPayload = {
  captured_at: string;
  system_probe: Record<string, unknown>;
  process?: Record<string, unknown>;
  gpu_runtime?: Record<string, unknown>;
};

