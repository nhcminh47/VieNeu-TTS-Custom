export type HealthInfo = {
  ok: boolean;
  service: string;
  version: string;
};

export type RuntimeInfo = {
  backend: string;
  device: string;
  gpu_name: string | null;
  compute_capability: number[] | null;
  dtype: string;
  lmdeploy_enabled: boolean;
  flash_attn_enabled: boolean;
  torch_compile_enabled: boolean;
  reason: string;
};

export type ModelInfo = {
  id: string;
  default: boolean;
};

export type VoiceInfo = {
  id: string;
  description: string;
  text: string | null;
  default: boolean;
};

export type JobStatus = "queued" | "running" | "completed" | "failed";

export type JobCreateResponse = {
  job_id: string;
  status: JobStatus;
};

export type JobRecord = {
  job_id: string;
  status: JobStatus;
  progress: number;
  audio_url: string | null;
  error: string | null;
};

export type JobCreatePayload = {
  text: string;
  model_id: string;
  voice_reference_id: string | null;
  voice_reference_path: string | null;
  format: "wav";
};

export type ChapterSegment = {
  index: number;
  paragraph_index: number;
  paragraph_segment_index: number;
  paragraph_segment_count: number;
  text_length: number;
  status: JobStatus;
  progress: number;
  audio_path: string | null;
  error: string | null;
};

export type ChapterJobRecord = JobRecord & {
  title: string;
  paragraph_count: number;
  segment_count: number;
  completed_segments: number;
  failed_segments: number;
  manifest_path: string | null;
  segments: ChapterSegment[];
};

export type ChapterJobCreatePayload = JobCreatePayload & {
  title: string | null;
};

export type JobEvent = {
  type: "job.status" | "job.completed" | "job.failed" | "chapter.status" | "chapter.completed" | "chapter.failed";
  job_id: string;
  status: JobStatus;
  progress: number;
  message?: string;
  audio_url?: string | null;
  error?: string;
};

function cleanBaseUrl(baseUrl: string) {
  return baseUrl.replace(/\/$/, "");
}

function httpUrl(baseUrl: string, path: string) {
  return `${cleanBaseUrl(baseUrl)}${path}`;
}

function wsUrl(baseUrl: string, path: string) {
  const explicitWsBase = process.env.NEXT_PUBLIC_VIENEU_WS_BASE;
  const candidate = explicitWsBase || (baseUrl.startsWith("/") ? "" : baseUrl);
  const url = new URL(path, candidate || window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}

async function request<T>(baseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(httpUrl(baseUrl, path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {})
    }
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      // Keep HTTP status text.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function fetchHealth(baseUrl: string) {
  return request<HealthInfo>(baseUrl, "/health");
}

export function fetchRuntime(baseUrl: string) {
  return request<RuntimeInfo>(baseUrl, "/runtime");
}

export function fetchModels(baseUrl: string) {
  return request<ModelInfo[]>(baseUrl, "/models");
}

export function fetchModelVoices(baseUrl: string, modelId: string) {
  return request<VoiceInfo[]>(baseUrl, `/models/${modelId}/voices`);
}

export function createJob(baseUrl: string, payload: JobCreatePayload) {
  return request<JobCreateResponse>(baseUrl, "/tts/jobs", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function createChapterJob(baseUrl: string, payload: ChapterJobCreatePayload) {
  return request<JobCreateResponse>(baseUrl, "/tts/chapter-jobs", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function fetchJob(baseUrl: string, jobId: string) {
  return request<JobRecord>(baseUrl, `/tts/jobs/${jobId}`);
}

export function fetchChapterJob(baseUrl: string, jobId: string) {
  return request<ChapterJobRecord>(baseUrl, `/tts/chapter-jobs/${jobId}`);
}

export function jobAudioUrl(baseUrl: string, jobId: string) {
  return httpUrl(baseUrl, `/tts/jobs/${jobId}/audio`);
}

export function chapterAudioUrl(baseUrl: string, jobId: string) {
  return httpUrl(baseUrl, `/tts/chapter-jobs/${jobId}/audio`);
}

export function openJobSocket(baseUrl: string, jobId: string) {
  return new WebSocket(wsUrl(baseUrl, `/ws/jobs/${jobId}`));
}

export function openChapterJobSocket(baseUrl: string, jobId: string) {
  return new WebSocket(wsUrl(baseUrl, `/ws/chapter-jobs/${jobId}`));
}
