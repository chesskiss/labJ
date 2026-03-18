# LabJ Setup

## Current State

The previous unified backend (`agents/controller.py`) is archived under `archive/legacy/agents/`.
Current unified backend entrypoint is `orchestration_api.app:app`.

## Prerequisites

- Python 3.10+
- Node.js 18+
- `uv`
- Docker + Docker Compose (for STT service)

## Install

```bash
# from repo root
uv sync
cd ui && npm install
```

## Run STT Service

```bash
cd stt/STT-module
docker compose up --build -d
```

Health check:

```bash
curl http://localhost:8001/health
```

## Run Frontend

```bash
cd ui && npm run dev
```

## Run Orchestration API

```bash
uv run uvicorn orchestration_api.app:app --reload --host 0.0.0.0 --port 8000
```

## Run Active Module Test Suites

```bash
# from repo root
uv run pytest context_action_plan/tests plan_validation/tests executor_runtime/tests mock_runtime_contract/tests db/tests tools/tests orchestration_api/tests -q
```

## Direct DB Notes

Legacy SQLite file:

- `data/journal.sqlite`

Use `sqlite3` for direct local inspection:

```bash
sqlite3 data/journal.sqlite
```

## Legacy Archive

Archived directories:

- `archive/legacy/agents/`
- `archive/legacy/ai-lab-journal - open source/`
- `archive/legacy/papers/`

See `archive/legacy/README.md` for rationale and restore instructions.
