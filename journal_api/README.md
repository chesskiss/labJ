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

## Contract (Frozen For Integration)

### POST `/journal/entries` request

- `session_id` (UUID, required)
- `base_revision_id` (UUID, optional)
- `title` (string, required)
- `content` (string HTML, required)
- `entry_type` (`general | observation | value`)
- `source` (`ui_manual | ui_command`)
- `metadata` (object, optional)

If `base_revision_id` is provided and does not match current session head revision,
the API returns `409 revision_conflict`.

### Error payload format

All non-2xx responses use:

- `code` (string)
- `message` (string)
- `details` (object)

Examples:
- `404 session_not_found`
- `409 revision_conflict`
- `422 validation_error`

## Notes

- Uses existing `journal_entries` and `events` tables.
- Writes stay append-only snapshots.
- Every write emits `journal_entry_created` event with `metadata.source` and `metadata.title`.
