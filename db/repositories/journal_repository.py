"""Repository for journal entry persistence and event logging."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from db.models import Event, JournalEntry, JournalRevision, JournalSession


class JournalRepository:
    """Persist journal entries + matching append-only event rows."""

    def __init__(self, session: Session):
        self.session = session

    def create_entry(
        self,
        content: str,
        entry_type: str,
        session_id: Optional[uuid.UUID],
        metadata: dict[str, Any],
        created_by: str = "executor_note_capture",
    ) -> JournalEntry:
        """Create a legacy journal entry, event, and revision/session head (when session_id exists)."""
        metadata_payload = metadata or {}
        entry = JournalEntry(
            session_id=session_id,
            content=content,
            entry_type=entry_type,
            created_by=created_by,
        )
        self.session.add(entry)
        self.session.flush()

        if session_id is not None:
            self._upsert_session_revision(
                entry_id=entry.id,
                session_id=session_id,
                content=content,
                entry_type=entry_type,
                created_by=created_by,
                created_at=entry.created_at,
                metadata=metadata_payload,
            )

        event = Event(
            event_type="journal_entry_created",
            aggregate_type="journal_entry",
            aggregate_id=entry.id,
            payload={"content": content, "entry_type": entry_type},
            metadata_json=metadata_payload,
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def list_session_summaries(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return latest summary per non-null session (revisions-first, legacy fallback)."""
        revision_summaries = self._list_session_summaries_from_revisions(limit=limit)
        legacy_summaries = self._list_session_summaries_from_legacy_entries(limit=limit)

        if not revision_summaries:
            return legacy_summaries
        if not legacy_summaries:
            return revision_summaries

        seen_sessions = {
            item["session_id"]
            for item in revision_summaries
            if item.get("session_id") is not None
        }
        merged = list(revision_summaries)
        for item in legacy_summaries:
            if item.get("session_id") in seen_sessions:
                continue
            merged.append(item)
        merged.sort(
            key=lambda item: (
                item.get("latest_created_at") is not None,
                item.get("latest_created_at"),
            ),
            reverse=True,
        )
        return merged[:limit]

    def _list_session_summaries_from_revisions(
        self, limit: int
    ) -> list[dict[str, Any]]:
        stmt = (
            select(JournalSession, JournalRevision)
            .join(
                JournalRevision,
                JournalSession.head_revision_id == JournalRevision.id,
            )
            .where(JournalSession.head_revision_id.is_not(None))
            .order_by(JournalRevision.created_at.desc(), JournalRevision.id.desc())
            .limit(limit)
        )
        rows = self.session.execute(stmt).all()
        summaries: list[dict[str, Any]] = []
        for session_row, revision_row in rows:
            title = (session_row.title or "").strip() or "Untitled Session"
            summaries.append(
                {
                    "session_id": session_row.id,
                    "head_revision_id": revision_row.id,
                    "latest_entry_id": revision_row.id,
                    "latest_created_at": revision_row.created_at,
                    "latest_entry_type": revision_row.entry_type,
                    "latest_created_by": revision_row.created_by,
                    "latest_revision_kind": revision_row.revision_kind,
                    "title": title,
                }
            )
        return summaries

    def _list_session_summaries_from_legacy_entries(
        self, limit: int
    ) -> list[dict[str, Any]]:
        """Legacy summary path from journal_entries only."""
        latest_per_session = (
            select(
                JournalEntry.session_id.label("session_id"),
                func.max(JournalEntry.created_at).label("latest_created_at"),
            )
            .where(JournalEntry.session_id.is_not(None))
            .group_by(JournalEntry.session_id)
            .subquery()
        )

        stmt = (
            select(JournalEntry)
            .join(
                latest_per_session,
                and_(
                    JournalEntry.session_id == latest_per_session.c.session_id,
                    JournalEntry.created_at == latest_per_session.c.latest_created_at,
                ),
            )
            .order_by(JournalEntry.created_at.desc())
            .limit(limit)
        )

        entries = self.session.execute(stmt).scalars().all()
        entry_ids = [entry.id for entry in entries]
        events_by_entry = self._events_by_aggregate_id(entry_ids)

        summaries: list[dict[str, Any]] = []
        seen_sessions: set[uuid.UUID] = set()
        for entry in entries:
            if entry.session_id is None:
                continue
            if entry.session_id in seen_sessions:
                continue

            metadata = events_by_entry.get(entry.id, {}).get("metadata", {})
            title = str(metadata.get("title", "")).strip() or "Untitled Session"

            summaries.append(
                {
                    "session_id": entry.session_id,
                    "head_revision_id": entry.id,
                    "latest_entry_id": entry.id,
                    "latest_created_at": entry.created_at,
                    "latest_entry_type": entry.entry_type,
                    "latest_created_by": entry.created_by,
                    "latest_revision_kind": self._infer_revision_kind(entry.created_by),
                    "title": title,
                }
            )
            seen_sessions.add(entry.session_id)

        return summaries

    def get_latest_entry_by_session(
        self, session_id: uuid.UUID
    ) -> tuple[JournalRevision | JournalEntry, dict[str, Any]] | None:
        """Return latest revision/entry + metadata for a session."""
        if self._has_revisions_for_session(session_id):
            stmt = (
                select(JournalRevision)
                .where(JournalRevision.session_id == session_id)
                .order_by(JournalRevision.created_at.desc(), JournalRevision.id.desc())
                .limit(1)
            )
            revision = self.session.execute(stmt).scalars().first()
            if revision is None:
                return None
            return revision, revision.metadata_json or {}

        entries = self._list_legacy_entries_by_session(session_id=session_id, limit=1)
        if not entries:
            return None
        return entries[0]

    def list_entries_by_session(
        self,
        session_id: uuid.UUID,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[tuple[JournalRevision | JournalEntry, dict[str, Any]]]:
        """Return revisions/entries + metadata ordered by newest first."""
        if self._has_revisions_for_session(session_id):
            stmt = (
                select(JournalRevision)
                .where(JournalRevision.session_id == session_id)
                .order_by(JournalRevision.created_at.desc(), JournalRevision.id.desc())
                .limit(limit)
            )
            if before is not None:
                stmt = (
                    select(JournalRevision)
                    .where(
                        and_(
                            JournalRevision.session_id == session_id,
                            JournalRevision.created_at < before,
                        )
                    )
                    .order_by(
                        JournalRevision.created_at.desc(), JournalRevision.id.desc()
                    )
                    .limit(limit)
                )
            revisions = self.session.execute(stmt).scalars().all()
            return [(revision, revision.metadata_json or {}) for revision in revisions]
        return self._list_legacy_entries_by_session(
            session_id=session_id, limit=limit, before=before
        )

    def _list_legacy_entries_by_session(
        self,
        session_id: uuid.UUID,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[tuple[JournalEntry, dict[str, Any]]]:
        """Legacy journal_entries path ordered by newest first."""
        stmt = (
            select(JournalEntry)
            .where(JournalEntry.session_id == session_id)
            .order_by(JournalEntry.created_at.desc(), JournalEntry.id.desc())
            .limit(limit)
        )
        if before is not None:
            stmt = (
                select(JournalEntry)
                .where(
                    and_(
                        JournalEntry.session_id == session_id,
                        JournalEntry.created_at < before,
                    )
                )
                .order_by(JournalEntry.created_at.desc(), JournalEntry.id.desc())
                .limit(limit)
            )
        entries = self.session.execute(stmt).scalars().all()
        entry_ids = [entry.id for entry in entries]
        events_by_entry = self._events_by_aggregate_id(entry_ids)
        return [
            (entry, events_by_entry.get(entry.id, {}).get("metadata", {}))
            for entry in entries
        ]

    def _has_revision_rows(self) -> bool:
        return (
            self.session.execute(select(JournalRevision.id).limit(1)).first()
            is not None
        )

    def _has_revisions_for_session(self, session_id: uuid.UUID) -> bool:
        stmt = (
            select(JournalRevision.id)
            .where(JournalRevision.session_id == session_id)
            .limit(1)
        )
        return self.session.execute(stmt).first() is not None

    def _upsert_session_revision(
        self,
        *,
        entry_id: uuid.UUID,
        session_id: uuid.UUID,
        content: str,
        entry_type: str,
        created_by: str,
        created_at: datetime,
        metadata: dict[str, Any],
    ) -> None:
        title = str(metadata.get("title", "")).strip() or "Untitled Session"

        session_row = self.session.get(JournalSession, session_id)
        if session_row is None:
            session_row = JournalSession(
                id=session_id,
                title=title,
                created_at=created_at,
                created_by=created_by,
                updated_at=created_at,
                metadata_json={"source": metadata.get("source", created_by)},
            )
            self.session.add(session_row)
            parent_revision_id = None
        else:
            parent_revision_id = session_row.head_revision_id
            session_row.updated_at = created_at
            if title and title != "Untitled Session":
                session_row.title = title

        revision = JournalRevision(
            id=entry_id,
            session_id=session_id,
            parent_revision_id=parent_revision_id,
            content=content,
            content_format="html",
            entry_type=entry_type,
            revision_kind=self._infer_revision_kind(created_by),
            created_by=created_by,
            created_at=created_at,
            metadata_json=metadata,
        )
        self.session.add(revision)
        session_row.head_revision_id = revision.id

    @staticmethod
    def _infer_revision_kind(created_by: str) -> str:
        if created_by == "executor_note_capture":
            return "stt_append"
        if created_by == "ui_command":
            return "llm_edit"
        if created_by == "ui_manual":
            return "manual_edit"
        return "manual_edit"

    def _events_by_aggregate_id(
        self, aggregate_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, dict[str, Any]]:
        if not aggregate_ids:
            return {}

        event_stmt = (
            select(Event)
            .where(
                and_(
                    Event.aggregate_id.in_(aggregate_ids),
                    Event.event_type == "journal_entry_created",
                )
            )
            .order_by(Event.created_at.desc())
        )
        events = self.session.execute(event_stmt).scalars().all()

        by_aggregate_id: dict[uuid.UUID, dict[str, Any]] = {}
        for event in events:
            if event.aggregate_id in by_aggregate_id:
                continue
            by_aggregate_id[event.aggregate_id] = {
                "metadata": event.metadata_json or {},
                "payload": event.payload or {},
            }

        return by_aggregate_id
