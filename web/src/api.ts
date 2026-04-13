/* Jemma SafeBrain — API client */

import type {
  BenchmarkPreset,
  CapabilityDescriptor,
  ChatMessage,
  ChatResponse,
  JobEvent,
  JobRecord,
  ModelSpec,
  ProviderHealth,
  RunRecord,
  SystemPayload,
  TrainingRequest,
  TrainingStatus,
} from "./types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function jsonFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Health / Models / System
// ---------------------------------------------------------------------------

export function getHealth(): Promise<{ ok: boolean; provider: ProviderHealth }> {
  return jsonFetch("/api/health");
}

export function getModels(): Promise<{ models: ModelSpec[] }> {
  return jsonFetch("/api/models");
}

export function getSystem(): Promise<SystemPayload> {
  return jsonFetch("/api/system");
}

export function getCapabilities(): Promise<{ capabilities: CapabilityDescriptor[] }> {
  return jsonFetch("/api/capabilities");
}

// ---------------------------------------------------------------------------
// Chat (non-streaming, existing endpoint)
// ---------------------------------------------------------------------------

export function sendChat(payload: {
  model?: string;
  system?: string;
  messages: ChatMessage[];
  options?: Record<string, unknown>;
  response_format?: "json" | null;
  timeout_s?: number;
}): Promise<ChatResponse> {
  return jsonFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// Streaming chat via Ollama directly (bypasses FastAPI for real-time tokens)
// Falls back to /api/chat if Ollama is unreachable.
// ---------------------------------------------------------------------------

export async function streamChat(
  model: string,
  messages: Array<{ role: string; content: string; images?: string[] }>,
  onToken: (token: string) => void,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const ollamaUrl = "/ollama/api/chat";

  try {
    const response = await fetch(ollamaUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model, messages, stream: true }),
      signal,
    });

    if (!response.ok || !response.body) {
      throw new Error("Ollama stream unavailable");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = "";
    let lastRaw: Record<string, unknown> = {};

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      // Ollama streams newline-delimited JSON
      for (const line of chunk.split("\n")) {
        if (!line.trim()) continue;
        try {
          const parsed = JSON.parse(line);
          const token = parsed.message?.content ?? "";
          if (token) {
            fullContent += token;
            onToken(token);
          }
          if (parsed.done) {
            lastRaw = parsed;
          }
        } catch {
          // skip malformed lines
        }
      }
    }

    const totalDuration = lastRaw.total_duration;
    return {
      model,
      content: fullContent,
      raw: lastRaw,
      total_duration_ms: typeof totalDuration === "number" ? Math.round(totalDuration / 1e6) : null,
      prompt_eval_count: (lastRaw.prompt_eval_count as number) ?? null,
      eval_count: (lastRaw.eval_count as number) ?? null,
    };
  } catch {
    // Fallback to non-streaming
    const result = await sendChat({ model, messages });
    onToken(result.content);
    return result;
  }
}

// ---------------------------------------------------------------------------
// Jobs / Runs / Benchmarks
// ---------------------------------------------------------------------------

export function getJobs(): Promise<{ jobs: JobRecord[] }> {
  return jsonFetch("/api/jobs");
}

export function getJob(jobId: string): Promise<{ job: JobRecord }> {
  return jsonFetch(`/api/jobs/${encodeURIComponent(jobId)}`);
}

export function getRuns(): Promise<{ runs: RunRecord[] }> {
  return jsonFetch("/api/runs");
}

export function getRun(runId: string): Promise<{ run: RunRecord; summary: Record<string, unknown> | null }> {
  return jsonFetch(`/api/runs/${encodeURIComponent(runId)}`);
}

export function getRunResults(runId: string): Promise<{ run_id: string; results: unknown[] }> {
  return jsonFetch(`/api/runs/${encodeURIComponent(runId)}/results`);
}

export function getPresets(): Promise<{ presets: BenchmarkPreset[] }> {
  return jsonFetch("/api/benchmarks/presets");
}

export function submitSoloBenchmark(payload: Record<string, unknown>): Promise<{ job: JobRecord }> {
  return jsonFetch("/api/jobs/benchmark/solo", { method: "POST", body: JSON.stringify(payload) });
}

export function submitPairwiseBenchmark(payload: Record<string, unknown>): Promise<{ job: JobRecord }> {
  return jsonFetch("/api/jobs/benchmark/pairwise", { method: "POST", body: JSON.stringify(payload) });
}

export function submitStressBenchmark(payload: Record<string, unknown>): Promise<{ job: JobRecord }> {
  return jsonFetch("/api/jobs/benchmark/stress", { method: "POST", body: JSON.stringify(payload) });
}

export function subscribeJobEvents(jobId: string, onEvent: (event: JobEvent) => void): () => void {
  const source = new EventSource(`/api/jobs/${encodeURIComponent(jobId)}/events`);
  source.onmessage = (event) => {
    onEvent(JSON.parse(event.data) as JobEvent);
  };
  return () => source.close();
}

// ---------------------------------------------------------------------------
// Training (POST to start, GET for status)
// ---------------------------------------------------------------------------

export function startTraining(payload: TrainingRequest): Promise<{ job_id: string }> {
  return jsonFetch("/api/training/start", { method: "POST", body: JSON.stringify(payload) });
}

export function getTrainingStatus(): Promise<TrainingStatus> {
  return jsonFetch("/api/training/status");
}

export function stopTraining(): Promise<{ stopped: boolean }> {
  return jsonFetch("/api/training/stop", { method: "POST" });
}
