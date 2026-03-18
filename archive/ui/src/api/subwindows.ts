import type { SubWindow } from "../types";

const API_BASE = "http://localhost:8000";

export async function fetchSubWindows(): Promise<SubWindow[]> {
  const res = await fetch(`${API_BASE}/subwindows`);
  if (!res.ok) throw new Error("Failed to fetch sub-windows");
  return res.json();
}

export async function updateSubWindow(
  windowId: string,
  updates: Partial<SubWindow>
): Promise<void> {
  const res = await fetch(`${API_BASE}/subwindows/${windowId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!res.ok) throw new Error("Failed to update sub-window");
}

export async function closeSubWindow(windowId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/subwindows/${windowId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to close sub-window");
}
