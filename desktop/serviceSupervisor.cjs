const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

function sqliteUrl(dbPath) {
  const normalized = dbPath.replace(/\\/g, "/");
  if (/^[A-Za-z]:\//.test(normalized)) {
    return `sqlite+pysqlite:///${normalized}`;
  }
  return `sqlite+pysqlite:////${normalized.replace(/^\/+/, "")}`;
}

function commandExists(command, args = ["--version"]) {
  const result = spawnSync(command, args, {
    stdio: "ignore",
    shell: process.platform === "win32",
  });
  return result.status === 0;
}

function killProcessTree(processRef) {
  if (!processRef || processRef.killed || !processRef.pid) {
    return;
  }

  if (process.platform === "win32") {
    try {
      spawnSync("taskkill", ["/pid", String(processRef.pid), "/t", "/f"], {
        stdio: "ignore",
        shell: true,
      });
      return;
    } catch {
      // fall through to direct kill
    }
  }

  try {
    processRef.kill("SIGKILL");
  } catch {
    // noop
  }
}

function parseDotEnvFile(envFilePath) {
  if (!envFilePath || !fs.existsSync(envFilePath)) {
    return {};
  }

  const raw = fs.readFileSync(envFilePath, "utf8");
  const lines = raw.split(/\r?\n/);
  const parsed = {};

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const index = trimmed.indexOf("=");
    if (index === -1) {
      continue;
    }

    const key = trimmed.slice(0, index).trim();
    let value = trimmed.slice(index + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    parsed[key] = value;
  }

  return parsed;
}

function isMalformedEnv(parsedEnv) {
  return Object.keys(parsedEnv).length === 0;
}

function resolvePythonRunner() {
  if (process.env.LABJ_UV_BIN && commandExists(process.env.LABJ_UV_BIN)) {
    return { command: process.env.LABJ_UV_BIN, useUv: true };
  }
  if (commandExists("uv")) {
    return { command: "uv", useUv: true };
  }

  const candidates = [
    process.env.LABJ_PYTHON_BIN,
    process.platform === "win32" ? "py" : "python3",
    "python",
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (commandExists(candidate, ["--version"])) {
      return { command: candidate, useUv: false };
    }
  }

  throw new Error("Could not find uv or python executable. Install uv or Python 3.10+.");
}

function resolveBundledPython(runtimeRoot) {
  if (!runtimeRoot) {
    return null;
  }
  const portablePythonPath =
    process.platform === "win32"
      ? path.join(runtimeRoot, "python", "python.exe")
      : path.join(runtimeRoot, "python", "bin", "python3");
  if (fs.existsSync(portablePythonPath)) {
    const pythonHome = process.platform === "darwin"
      ? resolveDarwinPythonHome(runtimeRoot)
      : process.platform === "win32"
        ? path.join(runtimeRoot, "python")
        : null;
    return {
      command: portablePythonPath,
      useUv: false,
      bundled: true,
      pythonPathEntries: [runtimeRoot, path.join(runtimeRoot, "site-packages")],
      pythonHome,
    };
  }
  return null;
}

function resolveDarwinPythonHome(runtimeRoot) {
  const currentVersionPath = path.join(
    runtimeRoot,
    "python",
    "Python.framework",
    "Versions",
    "Current",
  );
  if (fs.existsSync(currentVersionPath)) {
    return currentVersionPath;
  }

  const versionsDir = path.join(runtimeRoot, "python", "Python.framework", "Versions");
  if (!fs.existsSync(versionsDir)) {
    return null;
  }

  const versions = fs
    .readdirSync(versionsDir, { withFileTypes: true })
    .filter((entry) => entry.name !== "Current")
    .map((entry) => entry.name)
    .sort();

  return versions.length ? path.join(versionsDir, versions[0]) : null;
}

function runBundledRuntimeSelfCheck({ command, sourceRoot, runtimeRoot, pythonPathEntries, pythonHome, log }) {
  const packagedScriptPath = path.join(process.resourcesPath || "", "labj_runtime_tools", "runtime-self-check.py");
  const selfCheckScript = fs.existsSync(packagedScriptPath)
    ? packagedScriptPath
    : path.join(__dirname, "scripts", "runtime-self-check.py");
  const bundledModelPath = path.join(runtimeRoot, "models", "faster-whisper-tiny");
  const mergedEnv = {
    ...process.env,
    PYTHONPATH: [sourceRoot, ...(pythonPathEntries || [])].join(path.delimiter),
    ...(pythonHome ? { PYTHONHOME: pythonHome } : {}),
  };
  const result = spawnSync(
    command,
    [selfCheckScript, runtimeRoot, bundledModelPath],
    {
      cwd: sourceRoot,
      env: mergedEnv,
      shell: false,
      encoding: "utf8",
    }
  );

  if (log) {
    log("runtime:self_check", {
      status: result.status ?? null,
      stdout: (result.stdout || "").trim(),
      stderr: (result.stderr || "").trim(),
      command,
      runtimeRoot,
      bundledModelPath,
      pythonHome,
    });
  }

  if (result.status !== 0) {
    const stderr = (result.stderr || "").trim();
    const stdout = (result.stdout || "").trim();
    throw new Error(
      `Bundled runtime self-check failed.${stderr ? ` stderr: ${stderr}` : ""}${stdout ? ` stdout: ${stdout}` : ""}`
    );
  }
}

class ServiceSupervisor {
  constructor(config) {
    const {
      sourceRoot,
      dataDir,
      logsDir,
      envFilePath = null,
      runtimeRoot = null,
      packaged = false,
      runLogFile = null,
      envOverrides = {},
    } = config;

    this.sourceRoot = sourceRoot;
    this.dataDir = dataDir;
    this.logsDir = logsDir;
    this.envFilePath = envFilePath;
    this.runtimeRoot = runtimeRoot;
    this.packaged = packaged;
    this.runLogFile = runLogFile;
    this.envOverrides = envOverrides;
    this.services = new Map();
    this.supervisorLogFile = path.join(this.logsDir, "supervisor.log");
    this.envFromFile = parseDotEnvFile(envFilePath);
    const bundledPython = resolveBundledPython(runtimeRoot);
    this.runner = bundledPython ?? resolvePythonRunner();
    this._optionalWarmupPromise = null;
    this.status = {
      state: "stopped",
      services: {},
      serviceHealth: {},
      pendingServices: [],
      lastError: null,
      logsDir,
    };
  }

  getStatus() {
    return {
      ...this.status,
      services: Object.fromEntries(
        Array.from(this.services.entries()).map(([name, service]) => [name, {
          pid: service.process?.pid ?? null,
          running: !!service.process && !service.process.killed,
          port: service.port,
        }])
      ),
    };
  }

  async startAll() {
    if (
      this.status.state === "starting" ||
      this.status.state === "running" ||
      this.status.state === "degraded"
    ) {
      return;
    }

    this.status.state = "starting";
    this.status.lastError = null;
    this.status.serviceHealth = {};
    this.status.pendingServices = [];
    this._log("startAll:begin", {
      sourceRoot: this.sourceRoot,
      dataDir: this.dataDir,
      envFilePath: this.envFilePath,
      runtimeRoot: this.runtimeRoot,
      runner: this.runner,
      packaged: this.packaged,
    });

    if (this.envFilePath && !fs.existsSync(this.envFilePath)) {
      this._log("startAll:error_missing_env", { envFilePath: this.envFilePath });
      throw new Error(`Missing .env file at ${this.envFilePath}`);
    }
    if (this.envFilePath && isMalformedEnv(this.envFromFile)) {
      this._log("startAll:error_malformed_env", { envFilePath: this.envFilePath });
      throw new Error(`Malformed .env file at ${this.envFilePath}`);
    }
    if (this.packaged && this.runner.bundled !== true) {
      this._log("startAll:error_missing_bundled_runtime", { runtimeRoot: this.runtimeRoot });
      throw new Error("Bundled runtime not found. Rebuild installer with `npm run prepare:runtime`.");
    }
    if (this.packaged) {
      runBundledRuntimeSelfCheck({
        command: this.runner.command,
        sourceRoot: this.sourceRoot,
        runtimeRoot: this.runtimeRoot,
        pythonPathEntries: this.runner.pythonPathEntries,
        pythonHome: this.runner.pythonHome,
        log: this._log.bind(this),
      });
    }

    fs.mkdirSync(this.logsDir, { recursive: true });
    fs.mkdirSync(this.dataDir, { recursive: true });
    const hfHomeDir = path.join(this.dataDir, "huggingface");
    fs.mkdirSync(hfHomeDir, { recursive: true });

    const dbPath = path.join(this.dataDir, "journal.sqlite");
    const databaseUrl = sqliteUrl(dbPath);
    const targets = [
      { name: "orchestration_api", url: "http://127.0.0.1:8000/health" },
      { name: "journal_api", url: "http://127.0.0.1:8002/health" },
      { name: "stt", url: "http://127.0.0.1:8001/health" },
    ];

    try {
      this._spawnService({
        name: "stt",
        module: "stt.app:app",
        port: 8001,
        env: {
          HF_HOME: hfHomeDir,
          HF_HUB_DISABLE_SYMLINKS_WARNING: "1",
          HF_HUB_DISABLE_XET: "1",
        },
      });

      this._spawnService({
        name: "journal_api",
        module: "journal_api.app:app",
        port: 8002,
        env: {
          DATABASE_URL: databaseUrl,
          JOURNAL_API_CORS_ORIGINS: "*",
        },
      });

      this._spawnService({
        name: "orchestration_api",
        module: "orchestration_api.app:app",
        port: 8000,
        env: {
          DATABASE_URL: databaseUrl,
          STT_API_URL: "http://127.0.0.1:8001/transcribe",
          ORCHESTRATION_API_CORS_ORIGINS: "*",
        },
      });

      await this._waitForHealthy({
        targets,
        requiredNames: ["orchestration_api", "journal_api"],
        timeoutMs: this.packaged ? 180000 : 60000,
        phase: "required",
      });
      const sttReady = this.status.serviceHealth.stt === true;
      this.status.state = sttReady ? "running" : "degraded";
      this.status.lastError = sttReady ? null : "STT is still warming up.";
      this.status.pendingServices = sttReady ? [] : ["stt"];
      this._log("startAll:core_ready", {
        state: this.status.state,
        pendingServices: this.status.pendingServices,
      });

      if (!sttReady) {
        const warmupPromise = this._waitForHealthy({
          targets,
          requiredNames: ["stt"],
          timeoutMs: this.packaged ? 300000 : 180000,
          phase: "optional_stt",
        });
        this._optionalWarmupPromise = warmupPromise;
        warmupPromise
          .then(() => {
            if (this._optionalWarmupPromise !== warmupPromise) {
              return;
            }
            this.status.state = "running";
            this.status.lastError = null;
            this.status.pendingServices = [];
            this._log("startAll:stt_ready");
          })
          .catch((error) => {
            if (this._optionalWarmupPromise !== warmupPromise) {
              return;
            }
            const message = error instanceof Error ? error.message : String(error);
            this.status.state = "degraded";
            this.status.lastError = message;
            this.status.pendingServices = ["stt"];
            this._log("startAll:stt_warmup_timeout", { message });
          });
      }
    } catch (error) {
      this.status.state = "error";
      this.status.lastError = error instanceof Error ? error.message : String(error);
      this._log("startAll:error", { message: this.status.lastError });
      await this.stopAll();
      throw error;
    }
  }

  async stopAll() {
    this.status.state = "stopping";
    this.status.pendingServices = [];
    this._optionalWarmupPromise = null;
    this._log("stopAll:begin");

    const killPromises = Array.from(this.services.values()).map((service) =>
      new Promise((resolve) => {
        if (!service.process || service.process.killed) {
          resolve();
          return;
        }

        const processRef = service.process;
        const timeout = setTimeout(() => {
          killProcessTree(processRef);
          resolve();
        }, 3000);

        processRef.once("exit", () => {
          clearTimeout(timeout);
          resolve();
        });

        try {
          if (process.platform === "win32") {
            killProcessTree(processRef);
          } else {
            processRef.kill("SIGTERM");
          }
        } catch {
          clearTimeout(timeout);
          resolve();
        }
      })
    );

    await Promise.allSettled(killPromises);
    this.services.clear();
    this.status.serviceHealth = {};
    this.status.state = "stopped";
    this._log("stopAll:done");
  }

  async restartAll() {
    await this.stopAll();
    await this.startAll();
    return this.getStatus();
  }

  _spawnService({ name, module, port, env }) {
    const logFile = path.join(this.logsDir, `${name}.log`);
    const logStream = fs.createWriteStream(logFile, { flags: "a" });

    const args = this.runner.useUv
      ? ["run", "uvicorn", module, "--host", "127.0.0.1", "--port", String(port)]
      : ["-m", "uvicorn", module, "--host", "127.0.0.1", "--port", String(port)];

    const mergedEnv = {
      ...process.env,
      ...this.envFromFile,
      ...this.envOverrides,
      ...env,
      PYTHONUNBUFFERED: "1",
    };
    if (!this.runner.bundled) {
      mergedEnv.PYTHONPATH = this.sourceRoot;
    } else if (Array.isArray(this.runner.pythonPathEntries) && this.runner.pythonPathEntries.length) {
      mergedEnv.PYTHONPATH = [this.sourceRoot, ...this.runner.pythonPathEntries].join(path.delimiter);
      if (this.runner.pythonHome) {
        mergedEnv.PYTHONHOME = this.runner.pythonHome;
      }
    }

    const child = spawn(this.runner.command, args, {
      cwd: this.sourceRoot,
      env: mergedEnv,
      shell: process.platform === "win32",
    });
    this._log("service:spawned", {
      name,
      module,
      port,
      command: this.runner.command,
      args,
      cwd: this.sourceRoot,
      pid: child.pid ?? null,
      logFile,
    });

    child.stdout.on("data", (chunk) => {
      logStream.write(chunk);
      this._appendRunLogBuffer(name, "stdout", chunk);
    });
    child.stderr.on("data", (chunk) => {
      logStream.write(chunk);
      this._appendRunLogBuffer(name, "stderr", chunk);
    });
    child.on("exit", (code) => {
      this.status.serviceHealth[name] = false;
      this.status.pendingServices = Array.from(new Set([...this.status.pendingServices, name]));
      this._log("service:exit", { name, code: code ?? null });
      logStream.write(`\n[${new Date().toISOString()}] exited with code ${code}\n`);
      logStream.end();
    });

    this.services.set(name, {
      name,
      module,
      port,
      logFile,
      process: child,
    });
  }

  async _waitForHealthy({ targets, requiredNames, timeoutMs, phase }) {
    const startedAt = Date.now();

    while (Date.now() - startedAt < timeoutMs) {
      const checks = await Promise.all(
        targets.map(async ({ name, url }) => {
          try {
            const response = await fetch(url);
            return { name, ok: response.ok };
          } catch {
            return { name, ok: false };
          }
        })
      );
      const checkMap = Object.fromEntries(checks.map(({ name, ok }) => [name, ok]));
      const pendingNames = requiredNames.filter((name) => !checkMap[name]);
      this.status.serviceHealth = {
        ...this.status.serviceHealth,
        ...checkMap,
      };
      this.status.pendingServices = pendingNames;
      this._log("health:poll", {
        phase,
        checks: checkMap,
        pendingServices: pendingNames,
        elapsedMs: Date.now() - startedAt,
      });

      if (pendingNames.length === 0) {
        this._log("health:ready", { phase });
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, 800));
    }

    const pendingNames = requiredNames.filter((name) => this.status.serviceHealth[name] !== true);
    this._log("health:timeout", {
      phase,
      timeoutMs,
      pendingServices: pendingNames,
      checks: this.status.serviceHealth,
    });
    throw new Error(
      `Services did not become healthy in time. Pending: ${pendingNames.join(", ")}`
    );
  }

  _log(message, context = {}) {
    const line = `[${new Date().toISOString()}] [supervisor] ${message} ${
      Object.keys(context).length ? JSON.stringify(context) : ""
    }\n`;
    try {
      fs.mkdirSync(this.logsDir, { recursive: true });
      fs.appendFileSync(this.supervisorLogFile, line);
      if (this.runLogFile) {
        fs.appendFileSync(this.runLogFile, line);
      }
    } catch {
      // ignore log write errors
    }
    process.stdout.write(line);
  }

  _appendRunLogBuffer(serviceName, streamName, chunk) {
    if (!this.runLogFile) {
      return;
    }
    try {
      const text = Buffer.isBuffer(chunk) ? chunk.toString("utf8") : String(chunk);
      const prefixed = text
        .split(/\r?\n/)
        .filter((line) => line.length > 0)
        .map((line) => `[${new Date().toISOString()}] [${serviceName}:${streamName}] ${line}\n`)
        .join("");
      if (prefixed.length) {
        fs.appendFileSync(this.runLogFile, prefixed);
      }
    } catch {
      // ignore run-log write errors
    }
  }
}

module.exports = {
  ServiceSupervisor,
};
