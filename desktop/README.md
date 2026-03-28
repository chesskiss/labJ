# LabJ Desktop (Electron)

This desktop app starts LabJ backend services locally (no Docker) and then opens the UI.
For installer builds, it bundles a Python runtime (`desktop/runtime/.venv`) and ships `.env` from repo root.

## Runtime behavior
- Starts:
  - `stt.app:app` on `127.0.0.1:8001`
  - `orchestration_api.app:app` on `127.0.0.1:8000`
  - `journal_api.app:app` on `127.0.0.1:8002`
- Loads prebuilt UI from `ui/dist`.
- Mic flow stays unchanged: UI button calls `/mic/start` and `/mic/stop`.

## Prerequisites
- Node.js 18+
- Python 3.10+
- `uv` (required for `prepare:runtime` / installer builds)

## Run desktop app (dev)
```bash
cd desktop
npm install
npm run build:ui
npm start
```

## Build Windows package
```bash
cd desktop
npm install
npm run dist:win
```

## Build macOS package
```bash
cd desktop
npm install
npm run dist:mac
```

## Build both (run on matching build hosts/CI)
```bash
cd desktop
npm install
npm run dist:all
```

Artifacts are written to `desktop/release/`.

## One-click build scripts from repo root
- Windows: `Build Windows Installer.bat`
- macOS: `Build macOS Installer.command`

## Environment options
- `LABJ_REPO_ROOT`: override backend repo root path.
- `LABJ_UV_BIN`: override `uv` executable path.
- `LABJ_PYTHON_BIN`: override Python executable path if `uv` is unavailable.

## Secrets / .env
- Installer flow uses existing repo `.env` and bundles it in app resources.
- No key-entry prompt is shown in desktop app.
