import { apiGet } from "./client";

export async function fetchSessions() {
  return apiGet("/sessions");
}

export async function fetchNotebook() {
  return apiGet("/notebook");
}
