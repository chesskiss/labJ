# LabJ Architecture

This document describes the current runtime architecture and planned data/agent direction.

## Current Runtime (as implemented)

LabJ currently runs as modular stages plus STT service:

1. `stt/STT-module` service (`FastAPI` in Docker): audio-to-text transcription (`/health`, `/transcribe`).
2. `orchestration_api` (`FastAPI`): thin integration entrypoint (`/health`, `/process_text`, `/runtime_state`).
3. `context_action_plan`: transcript -> structured parsed output.
4. `plan_validation`: parsed output -> validated/non-executable classification.
5. `executor_runtime`: validated plans over mocked/runtime tools.
6. `db/` + `tools/`: first persistence slice (journal entries + events).

The previous unified backend (`agents/controller.py`) is archived under `archive/legacy/agents/`.

## Visual Architecture

```mermaid
flowchart LR
    U[User Speech] --> C[STTClient\nstt/STT-module/stt.py]
    C -->|POST /transcribe| S[STT API Service\nstt/STT-module/app.py]
    S -->|transcribed text| C
    C -->|text input| O[Orchestration API\norchestration_api/app.py]
    O -->|parse| P[Context -> ActionPlan Parser\ncontext_action_plan/]
    P --> V[Plan Validator + Registry\nplan_validation/]
    V --> E[Executor Runtime (mocked)\nexecutor_runtime/]
    E --> D[DB Layer\n db/ + tools/]
    D --> M[(SQLite now / Postgres target)]
    UI[React UI\nui/] -.can post text to /process_text .- O
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
│ Orchestration API                    │
│ orchestration_api/app.py             │
└───────────────┬──────────────────────┘
                │ process_text
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
3. Text is posted to `orchestration_api` `/process_text`.
4. Transcript is parsed into a structured `ParsedOutput` (`context_action_plan`).
5. Parsed output is validated against tool contracts (`plan_validation`).
6. `executor_runtime` executes validated plans against mocked tools/state.
7. `db/` and `tools/` provide persistence for first real write slice (`journal_entries`, `events`).
8. Archived backend API path is retained in `archive/legacy/` for reference only.

## Repository Structure (Architecture-Relevant)

```text
labJ/
├── archive/
│   └── legacy/
│       ├── agents/           # Archived former backend runtime
│       ├── ai-lab-journal - open source/
│       └── papers/
├── context_action_plan/      # Transcript -> ParsedOutput
├── plan_validation/          # ParsedOutput -> ValidationResult
├── executor_runtime/         # Validated execution runtime
├── orchestration_api/        # Thin backend integration entrypoint
├── mock_runtime_contract/    # Runtime state contract schemas/factories
├── db/                       # DB layer + repositories + migrations
├── tools/                    # Tool facades (e.g., journal write tool)
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

## Current State Note

- Unified backend API entrypoint is `orchestration_api.app:app`.
- Legacy backend is archived under `archive/legacy/agents/`.
- UI remains in repo and can integrate via `POST /process_text`.

## Planned Direction (Data + Retrieval)

For richer workflow memory and protocol retrieval, roadmap direction is:

1. Move to PostgreSQL.
2. Add event-oriented tables for actions/tool outcomes.
3. Add vector-enabled retrieval (`pgvector`) for protocol/doc chunks.
4. Keep tool execution server-side and deterministic (LLM does not execute SQL directly).
