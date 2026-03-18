# Journal API (Standalone, DB-Only)

This service exposes manual journal read/write endpoints for the UI without using `orchestration_api`.

## Run

From repo root:

```bash
uv run uvicorn journal_api.app:app --host 0.0.0.0 --port 8002 --reload
```

## Environment

- `DATABASE_URL` (optional)
  - default: `sqlite+pysqlite:///data/journal.sqlite`
- `JOURNAL_API_CORS_ORIGINS` (optional)
  - default: `*`

## Endpoints

- `GET /health`
- `GET /journal/sessions`
- `GET /journal/sessions/{session_id}/latest`
- `GET /journal/sessions/{session_id}/history?limit=&before=`
- `POST /journal/entries`

## Notes

- Uses existing `journal_entries` and `events` tables.
- Writes stay append-only snapshots.
- Every write emits `journal_entry_created` event with `metadata.source` and `metadata.title`.
