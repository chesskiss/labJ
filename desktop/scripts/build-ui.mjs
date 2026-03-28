import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import process from "node:process";

const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(scriptPath), "../..");
const uiDir = path.join(repoRoot, "ui");

const env = {
  ...process.env,
  VITE_ORCHESTRATION_API_URL: "http://127.0.0.1:8000",
  VITE_JOURNAL_API_URL: "http://127.0.0.1:8002",
  VITE_STT_API_URL: "http://127.0.0.1:8001",
};

const child = spawn("npm", ["run", "build", "--", "--base=./"], {
  cwd: uiDir,
  env,
  stdio: "inherit",
  shell: process.platform === "win32",
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
