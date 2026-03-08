# LabJ Architecture

This document describes the current runtime architecture and planned data/agent direction.

## Current Runtime (as implemented)

LabJ currently runs as a two-service system:

1. `labJ` backend (`FastAPI`): orchestration, command handling, UI APIs, session/utterance persistence.
2. `stt/STT-module` service (`FastAPI` in Docker): audio-to-text transcription (`/health`, `/transcribe`).

The backend receives text from `STTClient`, routes it through an LLM context layer, applies fallback keyword triggers, executes actions, and persists session data for the UI.

## Visual Architecture

```mermaid
flowchart LR
    U[User Speech] --> C[STTClient\nstt/STT-module/stt.py]
    C -->|POST /transcribe| S[STT API Service\nstt/STT-module/app.py]
    S -->|transcribed text| C
    C -->|callback text| P[Context -> ActionPlan Parser\ncontext_action_plan/]
    P --> V[Plan Validator + Registry\nplan_validation/]
    V --> E[Executor Runtime (mocked)\nexecutor_runtime/]
    E -->|next stage| W[DB Writes / Repositories\nplanned]
    C -->|current integration path| B[Backend Controller\nagents/controller.py]
    B --> X[ContextProcessor\nstt/context.py]
    X -->|tool calls| H[Command Handler\nhandle_stt_commands]
    X -->|enhanced text| T[Utterance Writer\nhandle_stt_text]
    B -->|fallback when no LLM commands| K[TriggerEvaluator\nstt/trigger.py]
    H --> M[(SQLite data/journal.sqlite)]
    T --> M
    W --> M
    B -->|/sessions /notebook /subwindows /commands| UI[React UI\nui/]
    UI -->|polling + command posts| B
```

### Box Diagram (ASCII)

```text
┌──────────────────────────────┐
│ User Speech / Microphone     │
└───────────────┬──────────────┘
                │
                v
┌──────────────────────────────┐
│ STTClient                    │
│ stt/STT-module/stt.py        │
└───────────────┬──────────────┘
                │ POST /transcribe
                v
┌──────────────────────────────┐
│ STT API Service              │
│ stt/STT-module/app.py        │
└───────────────┬──────────────┘
                │ transcribed text
                v
┌──────────────────────────────────────┐
│ Context -> ActionPlan Parser         │
│ context_action_plan/                 │
└───────────────┬──────────────────────┘
                │ ParsedOutput
                v
┌──────────────────────────────────────┐
│ Plan Validator + Tool Registry       │
│ plan_validation/                     │
└───────────────┬──────────────────────┘
                │ ValidatedPlan (next stage input)
                v
┌──────────────────────────────────────┐
│ Executor Runtime (isolated module)   │
│ executor_runtime/                     │
└───────────────┬──────────────────────┘
                │ tool calls + runtime results
                v
┌──────────────────────────────┐      ┌──────────────────┐
│ DB Writes / State Updates    │<---->│ React UI (ui/)   │
│ SQLite now, Postgres later   │ APIs │ polls endpoints  │
└──────────────────────────────┘      └──────────────────┘
```

## Request/Control Flow

1. User speaks into microphone.
2. `STTClient` segments speech by silence and calls STT API `/transcribe`.
3. Transcript is parsed into a structured `ParsedOutput` (`context_action_plan`).
4. Parsed output is validated against tool contracts (`plan_validation`).
5. `executor_runtime` executes validated plans against mocked tools/state.
6. Next stage (planned): executor writes state/events to DB via repository layer.
7. UI polls backend endpoints and renders notebook/session/subwindow state.

## Repository Structure (Architecture-Relevant)

```text
labJ/
├── agents/
│   ├── controller.py         # Main orchestration + API endpoints
│   ├── db.py                 # SQLAlchemy engine/session setup
│   └── models.py             # ORM models (sessions, utterances, actions)
├── stt/
│   ├── context.py            # LLM context processing + tool schemas
│   ├── trigger.py            # Deterministic keyword fallback
│   └── STT-module/           # Dockerized STT service + client
│       ├── app.py            # /health and /transcribe
│       ├── stt.py            # STTClient mic capture + HTTP transcription
│       └── docker-compose.yml
├── ui/
│   └── src/                  # React app consuming backend APIs
├── data/
│   └── journal.sqlite        # Current persistence file
├── README.md                 # User/dev quick start
└── ARCHITECTURE.md           # This document
```

## Data and State

Current persistence:

- `sessions`
- `utterances`
- `actions` (present in model layer; action logging strategy can be expanded)

State model:

- DB is source of truth.
- `SESSION_CACHE` and `SUBWINDOW_CACHE` provide runtime projections for fast UI reads.

## Command System: LLM + Fallback

Primary mechanism:

- LLM tool-calling in `stt/context.py` (MCP-style function schema).

Fallback mechanism:

- `stt/trigger.py` keyword evaluator when LLM does not emit commands.

This gives both flexibility (natural language) and deterministic safety backup.

## Planned Direction (Data + Retrieval)

For richer workflow memory and protocol retrieval, roadmap direction is:

1. Move to PostgreSQL.
2. Add event-oriented tables for actions/tool outcomes.
3. Add vector-enabled retrieval (`pgvector`) for protocol/doc chunks.
4. Keep tool execution server-side and deterministic (LLM does not execute SQL directly).
