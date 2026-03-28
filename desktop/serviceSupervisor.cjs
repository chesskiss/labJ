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
  const pythonPath =
    process.platform === "win32"
      ? path.join(runtimeRoot, ".venv", "Scripts", "python.exe")
      : path.join(runtimeRoot, ".venv", "bin", "python");
  return fs.existsSync(pythonPath) ? pythonPath : null;
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
    } = config;

    this.sourceRoot = sourceRoot;
    this.dataDir = dataDir;
    this.logsDir = logsDir;
    this.envFilePath = envFilePath;
    this.runtimeRoot = runtimeRoot;
    this.packaged = packaged;
    this.services = new Map();
    this.supervisorLogFile = path.join(this.logsDir, "supervisor.log");
    this.envFromFile = parseDotEnvFile(envFilePath);
    const bundledPython = resolveBundledPython(runtimeRoot);
    this.runner = bundledPython
      ? { command: bundledPython, useUv: false, bundled: true }
      : resolvePythonRunner();
    this.status = {
      state: "stopped",
      services: {},
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
    if (this.status.state === "starting" || this.status.state === "running") {
      return;
    }

    this.status.state = "starting";
    this.status.lastError = null;
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

    fs.mkdirSync(this.logsDir, { recursive: true });
    fs.mkdirSync(this.dataDir, { recursive: true });

    const dbPath = path.join(this.dataDir, "journal.sqlite");
    const databaseUrl = sqliteUrl(dbPath);

    try {
      this._spawnService({
        name: "stt",
        module: "stt.app:app",
        port: 8001,
        env: {},
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

      await this._waitForHealthy();
      this.status.state = "running";
      this._log("startAll:running");
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
    this._log("stopAll:begin");

    const killPromises = Array.from(this.services.values()).map((service) =>
      new Promise((resolve) => {
        if (!service.process || service.process.killed) {
          resolve();
          return;
        }

        const processRef = service.process;
        const timeout = setTimeout(() => {
          try {
            processRef.kill("SIGKILL");
          } catch {
            // noop
          }
          resolve();
        }, 3000);

        processRef.once("exit", () => {
          clearTimeout(timeout);
          resolve();
        });

        try {
          processRef.kill("SIGTERM");
        } catch {
          clearTimeout(timeout);
          resolve();
        }
      })
    );

    await Promise.allSettled(killPromises);
    this.services.clear();
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
      ...env,
      PYTHONUNBUFFERED: "1",
    };
    if (!this.runner.bundled) {
      mergedEnv.PYTHONPATH = this.sourceRoot;
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
    });
    child.stderr.on("data", (chunk) => {
      logStream.write(chunk);
    });
    child.on("exit", (code) => {
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

  async _waitForHealthy() {
    const targets = [
      "http://127.0.0.1:8000/health",
      "http://127.0.0.1:8002/health",
      "http://127.0.0.1:8001/health",
    ];

    const startedAt = Date.now();
    const timeoutMs = 60000;

    while (Date.now() - startedAt < timeoutMs) {
      const checks = await Promise.all(
        targets.map(async (url) => {
          try {
            const response = await fetch(url);
            return response.ok;
          } catch {
            return false;
          }
        })
      );
      this._log("health:poll", {
        checks,
        elapsedMs: Date.now() - startedAt,
      });

      if (checks.every(Boolean)) {
        this._log("health:ready");
        return;
      }

      await new Promise((resolve) => setTimeout(resolve, 800));
    }

    throw new Error("Services did not become healthy in time.");
  }

  _log(message, context = {}) {
    const line = `[${new Date().toISOString()}] [supervisor] ${message} ${
      Object.keys(context).length ? JSON.stringify(context) : ""
    }\n`;
    try {
      fs.mkdirSync(this.logsDir, { recursive: true });
      fs.appendFileSync(this.supervisorLogFile, line);
    } catch {
      // ignore log write errors
    }
    process.stdout.write(line);
  }
}

module.exports = {
  ServiceSupervisor,
};
