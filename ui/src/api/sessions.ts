import { apiGet } from "./client";

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
