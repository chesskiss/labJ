# mock_runtime_contract

Stable in-memory runtime state contract for modular execution-stage development.

## Purpose

This package formalizes the mocked runtime state used before real DB-backed adapters exist.
It lets tools and executor-stage tests rely on explicit, typed state without coupling to UI or persistence.

## Why It Exists Before DB Integration

- Keeps module contracts stable while persistence is still evolving.
- Enables deterministic tests for runtime behavior and future pipeline integration.
- Decouples execution semantics from storage technology.

## What State It Simulates

- Active session state (`active_session_exists`, `active_session_id`, `active_session_title`)
- Calculator slots (`calculator_slots`)
- Journal entries (`journal_entries`)
- Protocol index (`protocol_index`)
- Observation log (`observations`)
- Session context snapshot fields (`session_context_summary`, `recent_entities`, `recent_results`)
- Future-safe placeholders (`open_sessions`, `historical_session_summaries`, `scratch_state`)

## Input / Output Contract

Input:
- Factory helper parameters (session metadata, slot values, protocol content, summary text)
- Optional existing `MockRuntimeState` to derive updated copies

Output:
- `MockRuntimeState` pydantic model (fully serializable)

## What It Does Not Do Yet

- No real DB access
- No network calls
- No execution logic
- No tool dispatch
- No UI integration

## Run Tests

```bash
uv run pytest mock_runtime_contract/tests -q
```

