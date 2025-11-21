import { apiGet, apiPut } from "./client";

export async function fetchSessions() {
  return apiGet("/sessions");
}

export async function fetchNotebook() {
  return apiGet("/notebook");
}

export async function searchSessions(query: string) {
  const params = new URLSearchParams({ q: query });
  return apiGet(`/search?${params.toString()}`);
}

export async function updateSessionTitle(sessionId: number | string, title: string) {
  return apiPut(`/sessions/${sessionId}/title`, { title });
}
