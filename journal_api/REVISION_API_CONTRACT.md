# Journal API Revision Contract (Frozen v1)

This document defines API changes for moving from `journal_entries`-as-latest model
into session + revision model.

## Goals

- One UI sidebar row per `session_id`
- Current editor content comes from session head revision
- Full revision history is accessible and ordered
- Writes create new revisions (append-only)

## Existing Endpoints (Keep)

- `GET /health`
- `GET /journal/sessions`
- `GET /journal/sessions/{session_id}/latest`
- `GET /journal/sessions/{session_id}/history`
- `POST /journal/entries`

## New/Adjusted Contracts

### GET `/journal/sessions`

Response item should include:
- `session_id`
- `title`
- `head_revision_id`
- `latest_created_at`
- `latest_created_by`
- `latest_revision_kind`

### GET `/journal/sessions/{session_id}/latest`

Return current head revision:
- `revision_id`
- `session_id`
- `parent_revision_id`
- `title`
- `content`
- `content_format`
- `entry_type`
- `revision_kind`
- `created_by`
- `created_at`
- `metadata`

### GET `/journal/sessions/{session_id}/history?limit=&before=`

Return ordered revisions (newest first by default):
- `entries: RevisionResponse[]`

Optional future query params:
- `direction=asc|desc`
- `after=<cursor>`

### POST `/journal/entries` (active)

Request:
- `session_id`
- `base_revision_id` (optional)
- `title`
- `content`
- `entry_type`
- `source`
- `metadata`

Server behavior in revision model:
- creates a new `journal_revisions` row
- sets `parent_revision_id = current head`
- updates `journal_sessions.head_revision_id`
- emits existing `journal_entry_created` event for compatibility

Additional metadata to standardize:
- `operation` (`append`, `replace`, `insert_at_start`, ...)
- `base_revision_id`

Conflict rule:
- If request includes `base_revision_id` and it does not match current session head:
  - return HTTP `409`
  - error code `revision_conflict`

## Error Contract

All non-2xx responses return:
- `code: string`
- `message: string`
- `details: object`

Current codes:
- `session_not_found` (`404`)
- `revision_conflict` (`409`)
- `validation_error` (`422`)

### Optional new endpoint: POST `/journal/sessions/{session_id}/restore/{revision_id}`

Behavior:
- copies selected revision content into a new head revision
- does not mutate history in place

## Ordering Rule

Canonical revision ordering:
- `created_at DESC, revision_id DESC`

For deterministic parent chain construction:
- `created_at ASC, revision_id ASC`

## Non-Goals for this phase

- Delta storage
- Multi-branch merging
- Operational transform/CRDT
