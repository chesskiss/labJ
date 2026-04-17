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

function commandExists(command, args = ["--version"]) {
  const result = spawnSync(command, args, {
    stdio: "ignore",
    shell: process.platform === "win32",
  });
  return result.status === 0;
}

function resolvePythonCommand() {
  const candidates = [
    process.env.LABJ_PYTHON_BIN,
    process.platform === "win32" ? "py" : "python3",
    "python",
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (commandExists(candidate)) {
      return candidate;
    }
  }

  return null;
}

if (existsSync(runtimeRoot)) {
  rmSync(runtimeRoot, { recursive: true, force: true });
}
mkdirSync(runtimeRoot, { recursive: true });

const uvCommand = process.env.LABJ_UV_BIN || "uv";

if (commandExists(uvCommand)) {
  console.log("[prepare-runtime] creating venv with uv...");
  run(uvCommand, ["venv", venvDir]);

  console.log("[prepare-runtime] installing LabJ package + dependencies with uv...");
  run(uvCommand, ["pip", "install", "--python", venvPython, "."]);
} else {
  const pythonCommand = resolvePythonCommand();
  if (!pythonCommand) {
    console.error(
      "[prepare-runtime] Could not find uv or Python 3.10+. Install Python or set LABJ_PYTHON_BIN.",
    );
    process.exit(1);
  }

  const venvArgs = process.platform === "win32" && pythonCommand === "py"
    ? ["-3", "-m", "venv", venvDir]
    : ["-m", "venv", venvDir];
  const pipArgs = ["-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"];

  console.log(`[prepare-runtime] creating venv with ${pythonCommand}...`);
  run(pythonCommand, venvArgs);

  console.log("[prepare-runtime] upgrading pip tooling...");
  run(venvPython, pipArgs);

  console.log("[prepare-runtime] installing LabJ package + dependencies with pip...");
  run(venvPython, ["-m", "pip", "install", "."]);
}

console.log("[prepare-runtime] runtime ready at", venvDir);
