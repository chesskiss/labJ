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
