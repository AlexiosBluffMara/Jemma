/* Jemma SafeBrain — TypeScript types */

export type ProviderHealth = {
  provider: string;
  ok: boolean;
  detail: string;
  models: string[];
};

export type ChatMessage = {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  images?: string[];  // base64-encoded images for multimodal
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

// --- Training types ---

export type TrainingStatus = {
  active: boolean;
  job_id?: string;
  model: string;
  method: string;
  current_step: number;
  total_steps: number;
  loss?: number;
  learning_rate?: number;
  elapsed_s?: number;
  eta_s?: number;
  logs: string[];
};

export type TrainingRequest = {
  base_model: string;
  dataset_path: string;
  method: "qlora" | "lora";
  max_steps: number;
  learning_rate: number;
  lora_rank: number;
  lora_alpha: number;
  batch_size: number;
  max_seq_length: number;
  output_name: string;
};

// --- Gemma 4 model catalog (static data for model cards) ---

export type Gemma4ModelInfo = {
  id: string;
  name: string;
  subtitle: string;
  params: string;
  effective_params?: string;
  architecture: string;
  modalities: string[];
  context_window: string;
  vram_q4: number;      // GB
  vram_q8: number;      // GB
  vram_bf16: number;    // GB
  ollama_tag: string;
};

export const GEMMA4_MODELS: Gemma4ModelInfo[] = [
  {
    id: "e2b",
    name: "Gemma 4 E2B",
    subtitle: "2.3B effective / 5.1B total",
    params: "5.1B",
    effective_params: "2.3B",
    architecture: "Dense",
    modalities: ["Text", "Vision", "Audio"],
    context_window: "128K",
    vram_q4: 7.2,
    vram_q8: 8.1,
    vram_bf16: 10,
    ollama_tag: "gemma4:2b",
  },
  {
    id: "e4b",
    name: "Gemma 4 E4B",
    subtitle: "4.5B effective / 8B total",
    params: "8B",
    effective_params: "4.5B",
    architecture: "Dense",
    modalities: ["Text", "Vision", "Audio"],
    context_window: "128K",
    vram_q4: 9.6,
    vram_q8: 12,
    vram_bf16: 16,
    ollama_tag: "gemma4:latest",
  },
  {
    id: "27b",
    name: "Gemma 4 27B MoE",
    subtitle: "3.8B active / 25.2B total · 128 experts",
    params: "25.2B",
    effective_params: "3.8B",
    architecture: "MoE (128 routed, 8 active + 1 shared)",
    modalities: ["Text", "Vision"],
    context_window: "256K",
    vram_q4: 18,
    vram_q8: 28,
    vram_bf16: 52,
    ollama_tag: "gemma4:27b",
  },
  {
    id: "31b",
    name: "Gemma 4 31B Dense",
    subtitle: "30.7B parameters",
    params: "30.7B",
    architecture: "Dense",
    modalities: ["Text", "Vision"],
    context_window: "256K",
    vram_q4: 20,
    vram_q8: 34,
    vram_bf16: 63,
    ollama_tag: "gemma4:31b",
  },
];

export const TOTAL_VRAM_GB = 32; // RTX 5090
