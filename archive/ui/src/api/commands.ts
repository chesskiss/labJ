import { apiPost } from "./client";

export async function sendCommand(text: string) {
  return apiPost("/commands", { text });
}
