-- 001_create_journal_sessions.sql
-- Purpose: Canonical session registry for one sidebar row per session.
-- Postgres prerequisite: CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS journal_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL DEFAULT 'Untitled Session',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT 'system_migration',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    head_revision_id UUID NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_journal_sessions_updated_at ON journal_sessions (updated_at DESC);
