-- 002_create_journal_revisions.sql
-- Purpose: Snapshot-per-revision chain per session.
-- Postgres prerequisite: CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS journal_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES journal_sessions(id) ON DELETE CASCADE,
    parent_revision_id UUID NULL REFERENCES journal_revisions(id) ON DELETE SET NULL,

    content TEXT NOT NULL,
    content_format TEXT NOT NULL DEFAULT 'html',
    entry_type TEXT NOT NULL DEFAULT 'general',

    revision_kind TEXT NOT NULL DEFAULT 'manual_edit',
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_journal_revisions_session_created_desc
    ON journal_revisions (session_id, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS ix_journal_revisions_parent
    ON journal_revisions (parent_revision_id);

CREATE INDEX IF NOT EXISTS ix_journal_revisions_created_at
    ON journal_revisions (created_at DESC);

-- Add FK after revisions table exists.
ALTER TABLE journal_sessions
    ADD CONSTRAINT fk_journal_sessions_head_revision
    FOREIGN KEY (head_revision_id)
    REFERENCES journal_revisions(id)
    ON DELETE SET NULL;
