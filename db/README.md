# DB Persistence Slice

This folder contains the first real persistence slice:

- `journal_entries` table (user-facing notebook content)
- `events` table (append-only system log)
- SQLAlchemy models/repository
- runnable examples

## Quick Run

From repo root:

```bash
# Option A: run DB-level example (creates tables, writes 2 entries, prints counts)
uv run python -m db.examples

# Option B: run tool-level example (writes 1 entry through JournalWriteTool)
uv run python -m tools.examples
```

### Revision/Session Sanity Check

Run a consistency check for `journal_sessions`, `journal_revisions`, `journal_entries`, and
`journal_entry_created` events:

```bash
uv run python -m db.sanity_check
```

Exit code:
- `0` = no hard consistency errors
- `1` = at least one error detected

If `DATABASE_URL` is not set, examples default to:

```text
sqlite+pysqlite:///data/journal.sqlite
```

To use PostgreSQL:

```bash
export DATABASE_URL="postgresql+psycopg://USER:PASS@HOST:5432/DBNAME"
uv run python -m db.examples
```

## Access the DB Directly

### SQLite (local file)

```bash
sqlite3 data/journal.sqlite
```

Inside `sqlite3`:

```sql
.tables
select id, entry_type, created_at from journal_entries order by created_at desc limit 5;
select event_type, aggregate_type, created_at from events order by created_at desc limit 5;
.quit
```

To inspect full content written by examples:

```sql
select id, entry_type, content, created_by, created_at
from journal_entries
order by created_at desc
limit 10;

select event_type, aggregate_type, aggregate_id, payload, metadata, created_at
from events
order by created_at desc
limit 10;
```

### PostgreSQL

Use `psql` with plain postgres URL format:

```bash
export PSQL_URL="${DATABASE_URL/postgresql+psycopg/postgresql}"
psql "$PSQL_URL"
```

Inside `psql`:

```sql
\dt
select id, entry_type, created_at from journal_entries order by created_at desc limit 5;
select event_type, aggregate_type, created_at from events order by created_at desc limit 5;
\q
```

To inspect full content written by examples:

```sql
select id, entry_type, content, created_by, created_at
from journal_entries
order by created_at desc
limit 1;

select event_type, aggregate_type, aggregate_id, payload, metadata, created_at
from events
order by created_at desc
limit 10;
```

## Table Visualization

```text
┌──────────────────────────────────────────────────────┐
│ journal_entries (user-facing notebook content)       │
├───────────────┬──────────────────────────────────────┤
│ id (UUID)     │ primary key                          │
│ session_id    │ nullable UUID                        │
│ content       │ text                                 │
│ entry_type    │ text (observation/value/general/...) │
│ created_at    │ timestamptz                          │
│ created_by    │ text                                 │
└───────┬───────────────────────────────────────────────┘
        │ emits event per insert
        v
┌──────────────────────────────────────────────────────┐
│ events (append-only system log)                      │
├───────────────┬──────────────────────────────────────┤
│ id (UUID)     │ primary key                          │
│ event_type    │ text                                 │
│ aggregate_type│ text                                 │
│ aggregate_id  │ UUID                                 │
│ payload       │ JSON/JSONB                           │
│ metadata      │ JSON/JSONB                           │
│ created_at    │ timestamptz                          │
└──────────────────────────────────────────────────────┘
```

## Example Rows

### journal_entries

| id | entry_type | content | created_by |
|---|---|---|---|
| `4a...` | `observation` | `Sample observation: solution turned cloudy.` | `executor_note_capture` |
| `91...` | `value` | `Sample value: 5.2 mL` | `executor_note_capture` |

### events

| event_type | aggregate_type | payload (example) | metadata (example) |
|---|---|---|---|
| `journal_entry_created` | `journal_entry` | `{"content":"Sample value: 5.2 mL","entry_type":"value"}` | `{"source":"db_example","stage":"persistence_slice"}` |
| `calculator_command_requested` *(future example)* | `calculator_command` | `{"command":"add_constant","operand":2}` | `{"source":"voice","session":"active"}` |
| `protocol_search_requested` *(future example)* | `protocol_query` | `{"query":"PCR cleanup"}` | `{"source":"voice","session":"active"}` |

Notes:
- Only `journal_entry_created` is implemented in this slice.
- Other event types above are examples of planned event taxonomy.

## DB Change Impact Map

When schema changes are introduced (new column, rename, drop, constraints), use this map to
estimate blast radius.

### Core DB Layer (always impacted)

- `db/models.py`
  - ORM column definitions and defaults.
- `db/repositories/journal_repository.py`
  - Read/write behavior and event metadata mapping.
- `db/migrations.sql` and `db/migrations/*.sql`
  - SQL migration scripts.
- `db/tests/*`
  - Repository and DB consistency tests.
- `db/sanity_check.py`
  - Validation rules for head/session/revision consistency.

### Tool Layer (usually impacted)

- `tools/journal_tool.py`
  - `write_entry`, latest-session/content readers.
- `tools/tests/test_journal_tool.py`
  - Tool-level persistence expectations.

### Runtime / Orchestration (impacted if write contract changes)

- `executor_runtime/executor.py`
  - Note-capture metadata and snapshot content behavior.
- `executor_runtime/mock_state.py`
  - Runtime context fields used by executor.
- `executor_runtime/tests/*`
  - Note-capture and execution semantics tests.
- `orchestration_api/app.py`
  - Request parsing (`session_id`, `metadata`) and pipeline context.
- `orchestration_api/tests/*`
  - End-to-end persistence checks.

### Journal API / UI (impacted if API contract changes)

- `journal_api/schemas.py`, `journal_api/app.py`, `journal_api/tests/*`
  - Public read/write contract and error semantics.
- `ui/src/api/journalApi.ts`
  - Frontend type + request/response contract.
- `ui/src/components/AppShell.tsx` and workspace components
  - Save flow, conflict handling, revision history rendering.
- `ui/src/components/AppShell.test.tsx`
  - UI integration coverage.

### What usually keeps working without changes

- STT transcription module (`stt/`) when schema changes are persistence-only.
- Parser/validator logic (`context_action_plan`, `plan_validation`) if parsed shapes do not change.

## Safe Schema Change Playbook

### 1) Additive column (recommended default)

Use when adding new optional data.

- Add column as nullable or with a safe default.
- Update ORM model + repository writes.
- Backfill data in migration if needed.
- Update API contract only if field is externally visible.
- Update tests + run sanity check.

This is low risk and usually backward compatible.

### 2) Required column / non-null without default

Higher risk.

- Add as nullable first.
- Backfill all existing rows.
- Switch writes to populate it.
- Then enforce non-null constraint.

Do **not** flip to non-null in one step on live data.

### 3) Rename/drop column

Highest risk.

- Add new column first.
- Dual-write old+new during transition.
- Migrate reads to new column.
- Backfill and verify.
- Drop old column only after all callers are migrated.

## Is DB Evolution Easy Enough Right Now?

Short answer: **yes for additive changes**, **moderate risk for breaking changes**.

Why:

- Good:
  - Single repository write path (`JournalRepository`) reduces change surface.
  - Tests exist at DB/tool/executor/orchestrator/journal_api/UI layers.
  - `db.sanity_check` provides quick regression detection.
- Needs improvement for faster future changes:
  - No migration runner (manual SQL application).
  - Contract docs exist, but automated contract checks are still limited.
  - Legacy/transitional tables (`journal_entries` + `journal_revisions`) require careful sync checks.

## Recommended Improvements Before Major DB Refactors

1. Adopt a migration runner (for example Alembic) and make migrations part of CI.
2. Add a small "contract test" suite that validates `journal_api` response fields against fixtures.
3. Add a `make`/script target to run:
   - migrations (or migration check)
   - `db.sanity_check`
   - DB/tool/runtime/orchestrator test slices
4. Keep schema changes additive-first wherever possible.
