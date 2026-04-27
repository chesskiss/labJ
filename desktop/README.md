# LabJ Desktop (Electron)

This desktop app starts LabJ backend services locally (no Docker) and then opens the UI.
For installer builds, it bundles a Python runtime and ships `.env` from repo root.

## Runtime behavior
- Starts:
  - `stt.app:app` on `127.0.0.1:8001`
  - `orchestration_api.app:app` on `127.0.0.1:8000`
  - `journal_api.app:app` on `127.0.0.1:8002`
- Loads prebuilt UI from `ui/dist`.
- Mic flow stays unchanged: UI button calls `/mic/start` and `/mic/stop`.
- Packaged startup waits for `journal_api` and `orchestration_api` first, then lets `stt` continue warming up in the background.
- Windows installer builds pre-bundle the `faster-whisper-tiny` model so packaged STT does not need to download it on first launch.
- When `WHISPER_MODEL` is not set in packaged mode, desktop defaults to the bundled `tiny` model path when available.

## Prerequisites
- Node.js 18+
- Python 3.10+
- `uv` optional. If present, non-Windows installer builds use it. Windows installer builds bundle a copied Python runtime plus packaged `site-packages` so the installed app does not depend on a relocatable virtualenv.

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

## Startup debug log
- On every desktop app launch, `labj_run.log` is recreated in project root.
- This file includes main-process, supervisor, and backend stdout/stderr lines.
- If startup fails on Windows/macOS, send `labj_run.log`.

## One-click build scripts from repo root
- Windows: `Build Windows Installer.bat`
- macOS: `Build macOS Installer.command`

These are source-build scripts for developers. End users should run the generated installer artifact from `desktop/release/`, not these scripts.

## Windows CI build
- Workflow: `.github/workflows/build-windows.yml`
- Runner: `windows-latest`
- Placeholder environment file: repo-root `.env` containing `LLM_API_KEY=`
- Artifact: `labj-windows-installer`

Use this when you want a Windows-built installer without maintaining a local Windows VM. After the workflow completes, download the artifact from GitHub Actions and send the generated installer `.exe` to the Windows user.

## Environment options
- `LABJ_REPO_ROOT`: override backend repo root path.
- `LABJ_UV_BIN`: override `uv` executable path.
- `LABJ_PYTHON_BIN`: override Python executable path if `uv` is unavailable.

## Secrets / .env
- Installer flow uses existing repo `.env` and bundles it in app resources.
- If `LLM_API_KEY` is empty or missing, desktop startup prompts for it.
- Entered key is applied immediately and persisted back to `.env` when writable.
