# LabJ Desktop (Electron)

This desktop app starts LabJ backend services locally (no Docker) and then opens the UI.
For installer builds, it creates a clean app-specific Python runtime and ships `.env` from repo root.

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
- Packaged startup runs a bundled-runtime self-check before service launch so bad Python/module/model layouts fail early with clearer logs.

## Prerequisites
- Node.js 18+
- Python 3.10+
- `uv` is not required for installer builds.
- For release CI, desktop packaging is pinned to exact Python `3.11`.

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

## Runtime smoke test
After `npm run dist:win` or `npm run dist:mac`, you can verify the packaged runtime locally:

```bash
cd desktop
npm run smoke:runtime
```

This smoke test checks the packaged resources rather than the repo dev environment:
- bundled Python exists
- critical native modules import
- bundled `faster-whisper-tiny` model exists
- `WhisperModel(...)` can load the bundled model
- supervisor can start `journal_api`, `orchestration_api`, and `stt`

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
- Exact Python: `3.11`
- Placeholder environment file: repo-root `.env` containing `LLM_API_KEY=`
- Artifact: `labj-windows-installer`
- Includes packaged-runtime smoke test before artifact upload

Use this when you want a Windows-built installer without maintaining a local Windows VM. After the workflow completes, download the artifact from GitHub Actions and send the generated installer `.exe` to the Windows user.

## macOS CI build
- Workflow: `.github/workflows/build-macos.yml`
- Runner: `macos-latest`
- Exact Python: `3.11`
- Placeholder environment file: repo-root `.env` containing `LLM_API_KEY=`
- Artifact: `labj-macos-installer`
- Includes packaged-runtime smoke test before artifact upload

## Environment options
- `LABJ_REPO_ROOT`: override backend repo root path.
- `LABJ_UV_BIN`: override `uv` executable path.
- `LABJ_PYTHON_BIN`: override Python executable path for runtime packaging.
- `LABJ_EXPECTED_PYTHON_VERSION`: require an exact Python major/minor version during runtime packaging.

## Secrets / .env
- Installer flow uses existing repo `.env` and bundles it in app resources.
- If `LLM_API_KEY` is empty or missing, desktop startup prompts for it.
- Entered key is applied immediately and persisted back to `.env` when writable.
