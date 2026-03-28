import { existsSync, mkdirSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import process from "node:process";

const scriptPath = fileURLToPath(import.meta.url);
const desktopRoot = path.resolve(path.dirname(scriptPath), "..");
const repoRoot = path.resolve(desktopRoot, "..");
const runtimeRoot = path.join(desktopRoot, "runtime");
const venvDir = path.join(runtimeRoot, ".venv");
const venvPython = process.platform === "win32"
  ? path.join(venvDir, "Scripts", "python.exe")
  : path.join(venvDir, "bin", "python");

function run(command, args, cwd = repoRoot) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: "inherit",
    shell: process.platform === "win32",
    env: process.env,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

const uvCommand = process.env.LABJ_UV_BIN || "uv";

const uvCheck = spawnSync(uvCommand, ["--version"], {
  stdio: "ignore",
  shell: process.platform === "win32",
});

if (uvCheck.status !== 0) {
  console.error("[prepare-runtime] uv not found. Install uv or set LABJ_UV_BIN.");
  process.exit(1);
}

if (existsSync(runtimeRoot)) {
  rmSync(runtimeRoot, { recursive: true, force: true });
}
mkdirSync(runtimeRoot, { recursive: true });

console.log("[prepare-runtime] creating venv...");
run(uvCommand, ["venv", venvDir]);

console.log("[prepare-runtime] installing LabJ package + dependencies...");
run(uvCommand, ["pip", "install", "--python", venvPython, "."]);

console.log("[prepare-runtime] runtime ready at", venvDir);
