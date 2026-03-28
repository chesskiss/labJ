const ORCHESTRATION_API_BASE_URL =
  (import.meta.env.VITE_ORCHESTRATION_API_URL as string | undefined) ?? "/api/orch";
const STT_API_URL_FOR_MIC =
  (import.meta.env.VITE_STT_API_URL as string | undefined) ?? "http://localhost:8001";

function buildUrl(path: string): string {
  const normalizedBase = ORCHESTRATION_API_BASE_URL.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

export interface ProcessAudioResult {
  transcription?: {
    text?: string;
  };
  parsed?: Record<string, unknown>;
  validation?: Record<string, unknown>;
  execution?: Record<string, unknown>;
}

export interface MicControlResponse {
  ok: boolean;
  message: string;
  running: boolean;
  full_text?: string | null;
}

interface MicStartRequest {
  language: string;
  stt_api_url: string;
  silence_duration: number;
  silence_threshold: number;
}

async function parseOrchestrationResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      if (payload?.detail?.message) {
        detail = String(payload.detail.message);
      } else if (payload?.detail) {
        detail = String(payload.detail);
      }
    } catch {
      // ignore non-json response body
    }
    throw new Error(`Orchestration API ${response.status}: ${detail}`);
  }
  return (await response.json()) as T;
}

export async function micStart(
  payload: MicStartRequest = {
    language: "en",
    stt_api_url: STT_API_URL_FOR_MIC,
    silence_duration: 0.8,
    silence_threshold: 0.01,
  }
): Promise<MicControlResponse> {
  const response = await fetch(buildUrl("/mic/start"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseOrchestrationResponse<MicControlResponse>(response);
}

export async function micStop(): Promise<MicControlResponse> {
  const response = await fetch(buildUrl("/mic/stop"), {
    method: "POST",
  });
  return parseOrchestrationResponse<MicControlResponse>(response);
}
