# Runtime Cleanup TODO

## Scope
This cleanup keeps the current runtime architecture:
- Backend: `agents/controller.py`
- STT service: `stt/STT-module/*` over HTTP
- Command layer: `stt/context.py` with `stt/trigger.py` fallback
- UI: `ui/*`

## Future implementation milestones:
- For semantic search (Asking LLM to remind me/pull up a protocol) - add a Vector (embeddings) DB, e.g. quandrant or just use postgress

## DB Milestones (Deferred)
- [ ] Add `journal_sessions` table as canonical session registry (`id`, `title`, `head_revision_id`, timestamps).
- [ ] Add `journal_revisions` table for snapshot-per-revision chain (`session_id`, `parent_revision_id`, `content`, `created_by`, `created_at`, `metadata`).
- [ ] Backfill migration from current `journal_entries` into revision chain and preserve IDs for traceability.
- [ ] Add revision restore endpoint (`POST /journal/sessions/{id}/restore/{revision_id}`) that creates a new head revision.
- [ ] Add optional history pagination/sort contract (`asc`/`desc`, cursor-based).
- [ ] Add revision metadata standard (`operation`, `base_revision_id`, `source`) across UI/manual/STT/LLM writes.
- [ ] Add storage compaction strategy (periodic keyframe snapshots + optional delta payloads).
- [ ] Add persistent undo/redo semantics across sessions/devices (server-side revision cursor model).


## Milestone 1 - Stabilize Current Runtime
- [ ] Add STT readiness check in backend startup (`/health` poll before starting live mic loop).
- [ ] Add exponential backoff + retry around STT HTTP failures in `stt/STT-module/stt.py`.
- [ ] Add structured logging for context processor failures and fallback trigger usage.
- [ ] Validate DB metadata persistence shape for failed/successful context processing.

## Milestone 2 - Rebuild Tests for Current Flow
- [ ] Create tests for `on_transcription_callback` covering:
  - Context returns commands
  - Context fails and trigger fallback fires
  - Context returns journal text only
- [ ] Add endpoint tests for `/sessions`, `/notebook`, `/subwindows`, `/commands`.
- [ ] Add integration smoke test for STT service contract:
  - `GET /health`
  - `POST /transcribe` with test fixture audio

## Milestone 3 - Documentation Alignment
- [ ] Rewrite `README.md` architecture/data-flow diagram to match current stack.
- [ ] Rewrite `SETUP.md` startup steps for two-process mode:
  - STT docker service
  - backend uvicorn
- [ ] Document env vars explicitly:
  - `STT_API_URL`
  - `LLM_API_KEY`
  - any context toggles.

## Milestone 4 - Dependency and Packaging Cleanup
- [ ] Prune `pyproject.toml` dependencies that were only needed for removed modules.
- [ ] Re-lock dependencies (`uv.lock`) after pruning.
- [ ] Add a minimal `make`/script target for local start + health validation.

## Milestone 5 - Optional Future Features (Reintroduction Gate)
Only reintroduce removed modules if they have a concrete owner, tests, and acceptance criteria.

Candidates removed in this cleanup:
- Local audio capture stack (`audio/*`)
- Legacy transcriber pipeline (`stt/transcriber.py`, `stt/base.py`)
- Legacy NLP/utility/storage scaffolding (`agents/nlp/*`, `utils/*`, `storage/*`)
- Legacy tests and archive scaffolding
