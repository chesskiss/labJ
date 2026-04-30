import { mkdirSync, rmSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
import process from "node:process";

const require = createRequire(import.meta.url);
const { ServiceSupervisor } = require("../serviceSupervisor.cjs");

const scriptPath = fileURLToPath(import.meta.url);
const scriptsDir = path.dirname(scriptPath);
const desktopRoot = path.resolve(scriptsDir, "..");
const repoRoot = path.resolve(desktopRoot, "..");

function run(command, args, cwd, envOverrides = {}) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: "inherit",
    shell: false,
    env: {
      ...process.env,
      ...envOverrides,
    },
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function detectResourcesRoot() {
  if (process.env.LABJ_SMOKE_RESOURCES_ROOT) {
    return process.env.LABJ_SMOKE_RESOURCES_ROOT;
  }
  if (process.platform === "win32") {
    return path.join(desktopRoot, "release", "win-unpacked", "resources");
  }
  if (process.platform === "darwin") {
    return path.join(desktopRoot, "release", "mac", "LabJ.app", "Contents", "Resources");
  }
  throw new Error(`Unsupported smoke-test platform: ${process.platform}`);
}

function detectPythonHome(runtimeRoot) {
  if (process.platform === "darwin") {
    return path.join(runtimeRoot, "python", "Python.framework", "Versions", "Current");
  }
  if (process.platform === "win32") {
    return path.join(runtimeRoot, "python");
  }
  return null;
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForStt(supervisor, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const status = supervisor.getStatus();
    if (status.serviceHealth.stt === true) {
      return status;
    }
    const sttService = status.services.stt;
    if (!sttService?.running) {
      throw new Error("STT service exited during packaged-runtime smoke test.");
    }
    await wait(1000);
  }
  throw new Error("STT service did not become healthy during packaged-runtime smoke test.");
}

async function main() {
  const resourcesRoot = detectResourcesRoot();
  const runtimeRoot = path.join(resourcesRoot, "labj_runtime");
  const sourceRoot = path.join(resourcesRoot, "labj_backend_src");
  const envFilePath = path.join(resourcesRoot, "labj_env", ".env");
  const bundledModelPath = path.join(runtimeRoot, "models", "faster-whisper-tiny");
  const bundledSitePackages = path.join(runtimeRoot, "site-packages");
  const bundledPythonExe = process.platform === "win32"
    ? path.join(runtimeRoot, "python", "python.exe")
    : path.join(runtimeRoot, "python", "bin", "python3");
  const pythonHome = detectPythonHome(runtimeRoot);
  const selfCheckScript = path.join(repoRoot, "desktop", "scripts", "runtime-self-check.py");

  const requiredPaths = [resourcesRoot, runtimeRoot, sourceRoot, envFilePath, bundledModelPath, bundledPythonExe];
  for (const targetPath of requiredPaths) {
    if (!existsSync(targetPath)) {
      throw new Error(`Packaged runtime smoke test missing path: ${targetPath}`);
    }
  }

  const pythonPath = [sourceRoot, bundledSitePackages].join(path.delimiter);
  run(bundledPythonExe, [selfCheckScript, runtimeRoot, bundledModelPath], repoRoot, {
    PYTHONPATH: pythonPath,
    ...(pythonHome ? { PYTHONHOME: pythonHome } : {}),
  });

  run(
    bundledPythonExe,
    [
      "-c",
      `from faster_whisper import WhisperModel; WhisperModel(r'''${bundledModelPath}''', device='cpu', compute_type='int8'); print('model_load_ok')`,
    ],
    repoRoot,
    {
      PYTHONPATH: pythonPath,
      ...(pythonHome ? { PYTHONHOME: pythonHome } : {}),
    },
  );

  const smokeRoot = path.join(desktopRoot, "release", "smoke-runtime");
  rmSync(smokeRoot, { recursive: true, force: true });
  mkdirSync(path.join(smokeRoot, "data"), { recursive: true });
  mkdirSync(path.join(smokeRoot, "logs"), { recursive: true });

  const supervisor = new ServiceSupervisor({
    sourceRoot,
    dataDir: path.join(smokeRoot, "data"),
    logsDir: path.join(smokeRoot, "logs"),
    envFilePath,
    runtimeRoot,
    packaged: true,
  });

  try {
    await supervisor.startAll();
    await waitForStt(supervisor, 120000);
  } finally {
    await supervisor.stopAll();
  }
}

await main();
