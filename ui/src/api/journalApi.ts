const JOURNAL_API_BASE_URL =
  (import.meta.env.VITE_JOURNAL_API_URL as string | undefined) ?? "http://localhost:8002";

const JOURNAL_API_DEBUG =
  (import.meta.env.VITE_JOURNAL_API_DEBUG as string | undefined) === "true" ||
  import.meta.env.DEV;

function logDebug(message: string, context?: Record<string, unknown>) {
  if (!JOURNAL_API_DEBUG) {
    return;
  }
  if (context) {
    console.info(`[journalApi] ${message}`, context);
    return;
  }
  console.info(`[journalApi] ${message}`);
}

function logError(message: string, context?: Record<string, unknown>) {
  if (context) {
    console.error(`[journalApi] ${message}`, context);
    return;
  }
  console.error(`[journalApi] ${message}`);
}

export interface JournalSessionSummary {
  session_id: string;
  title: string;
  latest_created_at: string;
  latest_entry_id: string;
  latest_entry_type: string;
}

export interface JournalEntryRecord {
  entry_id: string;
  session_id: string;
  title: string;
  content: string;
  entry_type: string;
  created_by: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface JournalEntryWriteRequest {
  session_id: string;
  title: string;
  content: string;
  entry_type?: "general" | "observation" | "value";
  source: "ui_manual" | "ui_command";
  metadata?: Record<string, unknown>;
}

interface SessionListResponse {
  sessions: JournalSessionSummary[];
}

interface HistoryResponse {
  entries: JournalEntryRecord[];
}

function buildUrl(path: string): string {
  const normalizedBase = JOURNAL_API_BASE_URL.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = buildUrl(path);
  const method = init?.method ?? "GET";
  const startedAt = performance.now();
  logDebug("request:start", { method, url });

  try {
    const response = await fetch(url, init);
    const elapsedMs = Math.round(performance.now() - startedAt);
    logDebug("request:response", {
      method,
      url,
      status: response.status,
      ok: response.ok,
      elapsedMs,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        if (body && typeof body.detail === "string") {
          detail = body.detail;
        }
      } catch {
        // ignore malformed JSON in error response
      }
      const apiError = new Error(`Journal API ${response.status}: ${detail}`);
      logError("request:api_error", {
        method,
        url,
        status: response.status,
        detail,
        elapsedMs,
      });
      throw apiError;
    }

    return (await response.json()) as T;
  } catch (error) {
    const elapsedMs = Math.round(performance.now() - startedAt);
    const errorMessage = error instanceof Error ? error.message : String(error);
    logError("request:network_error", {
      method,
      url,
      elapsedMs,
      error: errorMessage,
    });
    throw error;
  }
}

export async function fetchSessionSummaries(limit = 100): Promise<JournalSessionSummary[]> {
  const payload = await fetchJson<SessionListResponse>(`/journal/sessions?limit=${limit}`);
  return payload.sessions;
}

export async function fetchLatestSessionEntry(sessionId: string): Promise<JournalEntryRecord> {
  return fetchJson<JournalEntryRecord>(`/journal/sessions/${sessionId}/latest`);
}

export async function fetchSessionHistory(
  sessionId: string,
  limit = 50,
  before?: string
): Promise<JournalEntryRecord[]> {
  const query = before
    ? `/journal/sessions/${sessionId}/history?limit=${limit}&before=${encodeURIComponent(before)}`
    : `/journal/sessions/${sessionId}/history?limit=${limit}`;
  const payload = await fetchJson<HistoryResponse>(query);
  return payload.entries;
}

export async function appendJournalEntry(
  payload: JournalEntryWriteRequest,
  options?: { keepalive?: boolean }
): Promise<JournalEntryRecord> {
  return fetchJson<JournalEntryRecord>("/journal/entries", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: options?.keepalive,
  });
}
