-- 003_backfill_from_journal_entries.sql
-- Purpose: Backfill sessions + revisions from existing journal_entries rows.
-- Strategy:
-- 1) Ensure every legacy row has a session id (generate for NULL)
-- 2) Create missing sessions
-- 3) Insert revisions in chronological order
-- 4) Link parent_revision_id chain
-- 5) Set head_revision_id per session

-- 1) Fill NULL legacy session IDs with deterministic one-row-per-entry session.
UPDATE journal_entries
SET session_id = id
WHERE session_id IS NULL;

-- 2) Seed sessions from distinct session_id values in legacy table.
-- Title is chosen from the latest entry's event metadata.title if present.
INSERT INTO journal_sessions (id, title, created_at, created_by, updated_at, metadata)
SELECT
    s.session_id AS id,
    COALESCE(
        (
            SELECT NULLIF(TRIM(ev.metadata ->> 'title'), '')
            FROM journal_entries je2
            LEFT JOIN events ev
                ON ev.aggregate_id = je2.id
               AND ev.event_type = 'journal_entry_created'
            WHERE je2.session_id = s.session_id
            ORDER BY je2.created_at DESC, je2.id DESC
            LIMIT 1
        ),
        'Untitled Session'
    ) AS title,
    (
        SELECT MIN(je3.created_at)
        FROM journal_entries je3
        WHERE je3.session_id = s.session_id
    ) AS created_at,
    COALESCE(
        (
            SELECT je4.created_by
            FROM journal_entries je4
            WHERE je4.session_id = s.session_id
            ORDER BY je4.created_at ASC, je4.id ASC
            LIMIT 1
        ),
        'system_migration'
    ) AS created_by,
    (
        SELECT MAX(je5.created_at)
        FROM journal_entries je5
        WHERE je5.session_id = s.session_id
    ) AS updated_at,
    jsonb_build_object('source', 'journal_entries_backfill') AS metadata
FROM (
    SELECT DISTINCT session_id
    FROM journal_entries
    WHERE session_id IS NOT NULL
) AS s
ON CONFLICT (id) DO NOTHING;

-- 3) Insert revisions if they were not inserted yet (idempotent by primary key).
INSERT INTO journal_revisions (
    id,
    session_id,
    parent_revision_id,
    content,
    content_format,
    entry_type,
    revision_kind,
    created_by,
    created_at,
    metadata
)
SELECT
    je.id,
    je.session_id,
    NULL,
    je.content,
    'html',
    je.entry_type,
    CASE
        WHEN je.created_by = 'executor_note_capture' THEN 'stt_append'
        WHEN je.created_by = 'ui_command' THEN 'llm_edit'
        ELSE 'manual_edit'
    END AS revision_kind,
    je.created_by,
    je.created_at,
    jsonb_build_object(
        'source_table', 'journal_entries',
        'entry_type', je.entry_type
    )
FROM journal_entries je
LEFT JOIN journal_revisions jr ON jr.id = je.id
WHERE je.session_id IS NOT NULL
  AND jr.id IS NULL;

-- 4) Build parent links by session timeline.
WITH ordered AS (
    SELECT
        id,
        session_id,
        created_at,
        LAG(id) OVER (
            PARTITION BY session_id
            ORDER BY created_at ASC, id ASC
        ) AS prev_id
    FROM journal_revisions
)
UPDATE journal_revisions r
SET parent_revision_id = ordered.prev_id
FROM ordered
WHERE r.id = ordered.id;

-- 5) Set current head per session to latest revision.
WITH latest AS (
    SELECT DISTINCT ON (session_id)
        session_id,
        id AS revision_id,
        created_at
    FROM journal_revisions
    ORDER BY session_id, created_at DESC, id DESC
)
UPDATE journal_sessions s
SET head_revision_id = latest.revision_id,
    updated_at = latest.created_at
FROM latest
WHERE s.id = latest.session_id;
