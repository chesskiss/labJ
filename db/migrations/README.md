# DB Migrations (Draft Plan)

These SQL files are ordered drafts for moving from the current `journal_entries` model
into a snapshot-per-revision model.

## Order

1. `001_create_journal_sessions.sql`
2. `002_create_journal_revisions.sql`
3. `003_backfill_from_journal_entries.sql`

## Notes

- These drafts target PostgreSQL first (`gen_random_uuid`, `jsonb`, CTE ordering).
- They are **not** auto-applied by code yet.
- Review and adapt for SQLite separately if needed.
- Backfill is additive and non-destructive: existing `journal_entries` remains intact.
