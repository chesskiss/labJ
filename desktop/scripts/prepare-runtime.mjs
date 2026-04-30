import { cpSync, existsSync, mkdirSync, readlinkSync, readdirSync, rmSync, symlinkSync, unlinkSync, lstatSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";
import process from "node:process";

const scriptPath = fileURLToPath(import.meta.url);
const desktopRoot = path.resolve(path.dirname(scriptPath), "..");
const repoRoot = path.resolve(desktopRoot, "..");
const runtimeRoot = path.join(desktopRoot, "runtime");
const bundledPythonDir = path.join(runtimeRoot, "python");
const bundledPythonExe = process.platform === "win32"
  ? path.join(bundledPythonDir, "python.exe")
  : path.join(bundledPythonDir, "bin", "python3");
const bundledSitePackages = path.join(runtimeRoot, "site-packages");
const bundledModelsDir = path.join(runtimeRoot, "models");
const bundledTinyModelDir = path.join(bundledModelsDir, "faster-whisper-tiny");

function getBundledPythonEnvOverrides() {
  if (process.platform === "darwin") {
    return {
      PYTHONHOME: path.join(bundledPythonDir, "Python.framework", "Versions", "Current"),
    };
  }
  return {};
}

function run(command, args, cwd = repoRoot, envOverrides = {}) {
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

function commandExists(command, args = ["--version"]) {
  const result = spawnSync(command, args, {
    stdio: "ignore",
    shell: false,
  });
  return result.status === 0;
}

function getPreferredPythonFromEnv() {
  const explicit = process.env.LABJ_PYTHON_BIN;
  if (explicit) {
    return explicit;
  }

  const pythonLocation = process.env.pythonLocation;
  if (!pythonLocation) {
    return null;
  }

  const candidate = process.platform === "win32"
    ? path.join(pythonLocation, "python.exe")
    : path.join(pythonLocation, "bin", "python3");
  return existsSync(candidate) ? candidate : null;
}

function resolvePythonCommand() {
  const candidates = [
    getPreferredPythonFromEnv(),
    process.platform === "win32" ? "python" : "python3",
    "python",
    process.platform === "win32" ? "py" : null,
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (commandExists(candidate)) {
      return candidate;
    }
  }

  return null;
}

function readCommandOutput(command, args) {
  const result = spawnSync(command, args, {
    cwd: repoRoot,
    stdio: ["ignore", "pipe", "inherit"],
    shell: false,
    env: process.env,
    encoding: "utf8",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
  return (result.stdout || "").trim();
}

function readPythonInfo(pythonCommand) {
  const raw = readCommandOutput(pythonCommand, [
    "-c",
    "import json, sys; print(json.dumps({'major': sys.version_info.major, 'minor': sys.version_info.minor, 'micro': sys.version_info.micro, 'base_prefix': sys.base_prefix}))",
  ]);
  return JSON.parse(raw);
}

function assertSupportedPython(pythonCommand) {
  const info = readPythonInfo(pythonCommand);
  const version = `${info.major}.${info.minor}`;
  const expected = process.env.LABJ_EXPECTED_PYTHON_VERSION?.trim();

  if (expected) {
    if (version !== expected) {
      console.error(
        `[prepare-runtime] Expected Python ${expected} but resolved ${version} from ${pythonCommand}.`,
      );
      process.exit(1);
    }
  } else if (info.major !== 3 || info.minor < 10) {
    console.error(
      `[prepare-runtime] Desktop packaging requires Python 3.10+; resolved ${version} from ${pythonCommand}.`,
    );
    process.exit(1);
  }

  console.log(
    `[prepare-runtime] using Python ${info.major}.${info.minor}.${info.micro} from ${pythonCommand}...`,
  );
  return info;
}

function copyPythonHome(pythonInfo) {
  if (process.platform === "darwin") {
    copyDarwinPythonFramework(pythonInfo);
    return;
  }

  const pythonHome = pythonInfo.base_prefix;
  if (!pythonHome) {
    console.error("[prepare-runtime] Could not resolve Python base_prefix for desktop runtime.");
    process.exit(1);
  }

  console.log(`[prepare-runtime] copying Python home from ${pythonHome}...`);
  cpSync(pythonHome, bundledPythonDir, {
    recursive: true,
    force: true,
    filter: (source) => {
      const normalized = source.replace(/\\/g, "/");
      return (
        !normalized.includes("/site-packages/") &&
        !normalized.endsWith("/python3.exe")
      );
    },
  });
}

function rewriteAbsoluteSymlinks(rootDir, sourcePrefix, destPrefix) {
  const stack = [rootDir];
  while (stack.length) {
    const current = stack.pop();
    const entries = readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      const entryPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(entryPath);
        continue;
      }
      if (!entry.isSymbolicLink()) {
        continue;
      }

      const target = readlinkSync(entryPath);
      if (!path.isAbsolute(target) || !target.startsWith(sourcePrefix)) {
        continue;
      }

      const remappedTarget = path.join(destPrefix, path.relative(sourcePrefix, target));
      const relativeTarget = path.relative(path.dirname(entryPath), remappedTarget);
      unlinkSync(entryPath);
      symlinkSync(relativeTarget, entryPath);
    }
  }
}

function copyDarwinPythonFramework(pythonInfo) {
  const version = `${pythonInfo.major}.${pythonInfo.minor}`;
  const sourceVersionDir = pythonInfo.base_prefix;
  const sourceFrameworkRoot = path.resolve(sourceVersionDir, "..", "..");
  const destFrameworkRoot = path.join(bundledPythonDir, "Python.framework");
  const destVersionDir = path.join(destFrameworkRoot, "Versions", version);

  console.log(`[prepare-runtime] copying macOS Python framework from ${sourceFrameworkRoot}...`);
  cpSync(sourceFrameworkRoot, destFrameworkRoot, {
    recursive: true,
    force: true,
  });

  rewriteAbsoluteSymlinks(destFrameworkRoot, sourceFrameworkRoot, destFrameworkRoot);

  const destBinDir = path.join(bundledPythonDir, "bin");
  mkdirSync(destBinDir, { recursive: true });
  const launcherPath = path.join(destBinDir, "python3");
  rmSync(launcherPath, { force: true });
  symlinkSync(
    path.relative(destBinDir, path.join(destVersionDir, "bin", `python${version}`)),
    launcherPath,
  );

  const pythonBinary = path.join(destVersionDir, "bin", `python${version}`);
  const frameworkBinary = path.join(destVersionDir, "Python");
  const sourceFrameworkBinary = path.join(sourceVersionDir, "Python");

  console.log("[prepare-runtime] retargeting macOS Python binary to bundled framework...");
  run("install_name_tool", [
    "-id",
    "@rpath/Python",
    frameworkBinary,
  ]);
  run("install_name_tool", [
    "-change",
    sourceFrameworkBinary,
    "@executable_path/../Python",
    pythonBinary,
  ]);

  console.log("[prepare-runtime] ad-hoc signing rewritten macOS Python binaries...");
  run("codesign", ["--force", "--sign", "-", frameworkBinary]);
  run("codesign", ["--force", "--sign", "-", pythonBinary]);
}

function installTargetedPackages(pythonExe) {
  const envOverrides = getBundledPythonEnvOverrides();

  console.log("[prepare-runtime] bootstrapping pip...");
  run(pythonExe, ["-m", "ensurepip", "--upgrade"], repoRoot, envOverrides);

  console.log("[prepare-runtime] upgrading pip tooling...");
  run(
    pythonExe,
    ["-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
    repoRoot,
    envOverrides,
  );

  mkdirSync(bundledSitePackages, { recursive: true });
  console.log("[prepare-runtime] installing LabJ package + dependencies into bundled site-packages...");
  run(
    pythonExe,
    ["-m", "pip", "install", "--target", bundledSitePackages, "."],
    repoRoot,
    envOverrides,
  );
}

function bundleTinyWhisperModel(pythonExe) {
  mkdirSync(bundledModelsDir, { recursive: true });
  console.log("[prepare-runtime] pre-downloading faster-whisper-tiny model...");
  const script = [
    "from huggingface_hub import snapshot_download",
    `snapshot_download(repo_id='Systran/faster-whisper-tiny', local_dir=r'''${bundledTinyModelDir}''', local_dir_use_symlinks=False)`,
  ].join("\n");
  run(
    pythonExe,
    ["-c", script],
    repoRoot,
    {
      HF_HOME: path.join(runtimeRoot, "huggingface-build-cache"),
      HF_HUB_DISABLE_XET: "1",
      HF_HUB_DISABLE_SYMLINKS_WARNING: "1",
      PYTHONPATH: bundledSitePackages,
      ...getBundledPythonEnvOverrides(),
    },
  );
}

if (existsSync(runtimeRoot)) {
  rmSync(runtimeRoot, { recursive: true, force: true });
}
mkdirSync(runtimeRoot, { recursive: true });

const pythonCommand = resolvePythonCommand();
if (!pythonCommand) {
  console.error(
    "[prepare-runtime] Could not find Python 3.10+ on PATH. Install Python or set LABJ_PYTHON_BIN.",
  );
  process.exit(1);
}

const pythonInfo = assertSupportedPython(pythonCommand);
copyPythonHome(pythonInfo);
installTargetedPackages(bundledPythonExe);
bundleTinyWhisperModel(bundledPythonExe);

console.log("[prepare-runtime] runtime ready at", runtimeRoot);
