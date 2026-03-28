const { app, BrowserWindow, dialog, ipcMain, shell } = require("electron");
const fs = require("node:fs");
const path = require("node:path");
const { ServiceSupervisor } = require("./serviceSupervisor.cjs");

const PORTS = {
  orchestration: 8000,
  journal: 8002,
  stt: 8001,
};

let mainWindow = null;
let supervisor = null;
let mainLogFile = null;

function logMain(message, context = {}) {
  const line = `[${new Date().toISOString()}] [main] ${message} ${
    Object.keys(context).length ? JSON.stringify(context) : ""
  }\n`;
  try {
    if (mainLogFile) {
      fs.appendFileSync(mainLogFile, line);
    }
  } catch {
    // ignore log write errors
  }
  process.stdout.write(line);
}

function resolvePaths() {
  if (process.env.LABJ_REPO_ROOT) {
    const root = process.env.LABJ_REPO_ROOT;
    return {
      sourceRoot: root,
      uiIndexPath: path.join(root, "ui", "dist", "index.html"),
      dataDir: path.join(root, "data"),
      envFilePath: path.join(root, ".env"),
      runtimeRoot: path.join(root, "desktop", "runtime"),
      packaged: false,
    };
  }

  if (app.isPackaged) {
    return {
      sourceRoot: path.join(process.resourcesPath, "labj_backend_src"),
      uiIndexPath: path.join(process.resourcesPath, "labj_ui", "index.html"),
      dataDir: path.join(process.resourcesPath, "labj_data"),
      envFilePath: path.join(process.resourcesPath, "labj_env", ".env"),
      runtimeRoot: path.join(process.resourcesPath, "labj_runtime"),
      packaged: true,
    };
  }

  const root = path.resolve(__dirname, "..");
  return {
    sourceRoot: root,
    uiIndexPath: path.join(root, "ui", "dist", "index.html"),
    dataDir: path.join(root, "data"),
    envFilePath: path.join(root, ".env"),
    runtimeRoot: path.join(root, "desktop", "runtime"),
    packaged: false,
  };
}

function readEnvValue(envFilePath, key) {
  if (!fs.existsSync(envFilePath)) {
    return null;
  }
  const raw = fs.readFileSync(envFilePath, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const index = trimmed.indexOf("=");
    if (index === -1) {
      continue;
    }
    const currentKey = trimmed.slice(0, index).trim();
    if (currentKey !== key) {
      continue;
    }
    let value = trimmed.slice(index + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    return value;
  }
  return null;
}

function upsertEnvValue(envFilePath, key, value) {
  const nextLine = `${key}=${value}`;
  const original = fs.existsSync(envFilePath) ? fs.readFileSync(envFilePath, "utf8") : "";
  const lines = original.length ? original.split(/\r?\n/) : [];
  let replaced = false;
  const updated = lines.map((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      return line;
    }
    const index = trimmed.indexOf("=");
    if (index === -1) {
      return line;
    }
    const currentKey = trimmed.slice(0, index).trim();
    if (currentKey !== key) {
      return line;
    }
    replaced = true;
    return nextLine;
  });

  if (!replaced) {
    if (updated.length && updated[updated.length - 1].trim().length) {
      updated.push("");
    }
    updated.push(nextLine);
  }

  fs.writeFileSync(envFilePath, updated.join("\n"));
}

async function promptForLlmApiKey() {
  return new Promise((resolve) => {
    let settled = false;
    const promptWindow = new BrowserWindow({
      width: 520,
      height: 280,
      show: false,
      resizable: false,
      minimizable: false,
      maximizable: false,
      modal: true,
      parent: mainWindow ?? undefined,
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false,
      },
    });

    const channel = `llm-key:${Date.now()}:${Math.random().toString(16).slice(2)}`;
    const settle = (value) => {
      if (settled) {
        return;
      }
      settled = true;
      resolve(value);
    };
    const cleanup = () => {
      ipcMain.removeAllListeners(channel);
      if (!promptWindow.isDestroyed()) {
        promptWindow.close();
      }
    };

    ipcMain.on(channel, (_event, payload) => {
      const action = payload?.action;
      if (action === "save") {
        const value = typeof payload.value === "string" ? payload.value.trim() : "";
        cleanup();
        settle(value.length ? value : null);
        return;
      }
      cleanup();
      settle(null);
    });

    promptWindow.on("closed", () => {
      ipcMain.removeAllListeners(channel);
      settle(null);
    });

    const html = `
      <html>
        <body style="font-family: sans-serif; padding: 20px; display:flex; flex-direction:column; gap:12px;">
          <h3 style="margin:0;">LLM API key required</h3>
          <p style="margin:0;">Enter <code>LLM_API_KEY</code> to enable LLM parsing.</p>
          <input id="keyInput" type="password" placeholder="gsk_..." style="padding:8px; font-size:14px;" autofocus />
          <div style="display:flex; gap:8px; justify-content:flex-end;">
            <button id="cancelBtn" style="padding:8px 12px;">Cancel</button>
            <button id="saveBtn" style="padding:8px 12px;">Save & Continue</button>
          </div>
          <script>
            const { ipcRenderer } = require("electron");
            const channel = ${JSON.stringify(channel)};
            const keyInput = document.getElementById("keyInput");
            document.getElementById("cancelBtn").addEventListener("click", () => {
              ipcRenderer.send(channel, { action: "cancel" });
            });
            document.getElementById("saveBtn").addEventListener("click", () => {
              ipcRenderer.send(channel, { action: "save", value: keyInput.value });
            });
            keyInput.addEventListener("keydown", (event) => {
              if (event.key === "Enter") {
                ipcRenderer.send(channel, { action: "save", value: keyInput.value });
              }
            });
          </script>
        </body>
      </html>
    `;

    promptWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
    promptWindow.once("ready-to-show", () => promptWindow.show());
  });
}

function createBootWindow() {
  logMain("createBootWindow:start");
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const bootHtml = `
    <html>
      <body style="font-family: sans-serif; padding: 24px;">
        <h2>Starting LabJ runtime...</h2>
        <p>Launching STT, orchestration API, and journal API.</p>
      </body>
    </html>
  `;
  mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(bootHtml)}`);
  mainWindow.once("ready-to-show", () => {
    logMain("createBootWindow:ready-to-show");
    mainWindow.show();
  });

  mainWindow.webContents.on("did-finish-load", () => {
    logMain("webContents:did-finish-load", { url: mainWindow.webContents.getURL() });
  });
  mainWindow.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL) => {
    logMain("webContents:did-fail-load", { errorCode, errorDescription, validatedURL });
  });
  mainWindow.webContents.on("console-message", (_event, level, message, line, sourceId) => {
    logMain("webContents:console-message", { level, message, line, sourceId });
  });
  mainWindow.webContents.on("render-process-gone", (_event, details) => {
    logMain("webContents:render-process-gone", details || {});
  });
}

async function loadUi() {
  const paths = resolvePaths();
  logMain("loadUi:start", { uiIndexPath: paths.uiIndexPath });
  await mainWindow.loadFile(paths.uiIndexPath);
  logMain("loadUi:done", { uiIndexPath: paths.uiIndexPath });
}

async function startRuntimeAndUi() {
  const paths = resolvePaths();
  const logsDir = path.join(app.getPath("userData"), "logs");
  fs.mkdirSync(logsDir, { recursive: true });
  mainLogFile = path.join(logsDir, "main.log");
  logMain("startRuntimeAndUi:paths", {
    packaged: paths.packaged,
    sourceRoot: paths.sourceRoot,
    dataDir: paths.dataDir,
    envFilePath: paths.envFilePath,
    runtimeRoot: paths.runtimeRoot,
    logsDir,
  });

  if (!fs.existsSync(paths.envFilePath)) {
    logMain("startup:error_missing_env", { envFilePath: paths.envFilePath });
    await dialog.showMessageBox({
      type: "error",
      title: "Missing .env",
      message: "LabJ activation file is missing.",
      detail: `Expected .env at: ${paths.envFilePath}`,
    });
    return;
  }

  let llmApiKey = readEnvValue(paths.envFilePath, "LLM_API_KEY");
  if (!llmApiKey || !llmApiKey.trim().length) {
    logMain("startup:llm_api_key_missing_prompt");
    llmApiKey = await promptForLlmApiKey();
    if (!llmApiKey) {
      logMain("startup:error_no_llm_api_key_provided");
      await dialog.showMessageBox({
        type: "error",
        title: "LLM_API_KEY required",
        message: "Startup cancelled because no LLM API key was provided.",
        detail: "Set LLM_API_KEY in .env or provide it in the prompt.",
      });
      return;
    }
    try {
      upsertEnvValue(paths.envFilePath, "LLM_API_KEY", llmApiKey);
      logMain("startup:llm_api_key_saved_to_env");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      logMain("startup:warn_failed_to_persist_llm_api_key", { message });
    }
  }

  supervisor = new ServiceSupervisor({
    sourceRoot: paths.sourceRoot,
    dataDir: paths.dataDir,
    logsDir,
    envFilePath: paths.envFilePath,
    runtimeRoot: paths.runtimeRoot,
    packaged: paths.packaged,
    envOverrides: {
      LLM_API_KEY: llmApiKey,
    },
  });

  ipcMain.handle("runtime:getStatus", async () => supervisor.getStatus());
  ipcMain.handle("runtime:restartServices", async () => supervisor.restartAll());
  ipcMain.handle("runtime:openLogsFolder", async () => shell.openPath(logsDir));

  try {
    logMain("supervisor:startAll:begin");
    await supervisor.startAll();
    logMain("supervisor:startAll:done");
    await loadUi();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logMain("startup:error", { message });
    const details = [
      `Failed to start LabJ runtime: ${message}`,
      `\nExpected ports:\n- ${PORTS.stt} (STT)\n- ${PORTS.orchestration} (orchestration_api)\n- ${PORTS.journal} (journal_api)`,
      `\nCheck logs in: ${logsDir}`,
    ].join("\n");

    await dialog.showMessageBox({
      type: "error",
      title: "LabJ startup failed",
      message: "LabJ could not start required services.",
      detail: details,
    });

    const failHtml = `
      <html>
        <body style="font-family: sans-serif; padding: 24px;">
          <h2>LabJ startup failed</h2>
          <pre style="white-space: pre-wrap;">${details}</pre>
        </body>
      </html>
    `;
    await mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(failHtml)}`);
  }
}

app.whenReady().then(async () => {
  logMain("app:whenReady");
  createBootWindow();
  await startRuntimeAndUi();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createBootWindow();
      void startRuntimeAndUi();
    }
  });
});

app.on("before-quit", async (event) => {
  logMain("app:before-quit");
  if (supervisor) {
    event.preventDefault();
    try {
      await supervisor.stopAll();
    } finally {
      supervisor = null;
      app.exit(0);
    }
  }
});

app.on("window-all-closed", () => {
  logMain("app:window-all-closed");
  if (process.platform !== "darwin") {
    app.quit();
  }
});
