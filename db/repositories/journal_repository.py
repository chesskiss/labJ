"""Repository for journal entry persistence and event logging."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from db.models import Event, JournalEntry


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
        """Create a journal entry and matching event record atomically."""
        entry = JournalEntry(
            session_id=session_id,
            content=content,
            entry_type=entry_type,
            created_by=created_by,
        )
        self.session.add(entry)
        self.session.flush()

        event = Event(
            event_type="journal_entry_created",
            aggregate_type="journal_entry",
            aggregate_id=entry.id,
            payload={"content": content, "entry_type": entry_type},
            metadata_json=metadata or {},
        )
        self.session.add(event)
        self.session.commit()
        self.session.refresh(entry)
        return entry

    def list_session_summaries(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return latest entry summary per non-null session."""
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
                    "latest_entry_id": entry.id,
                    "latest_created_at": entry.created_at,
                    "latest_entry_type": entry.entry_type,
                    "title": title,
                }
            )
            seen_sessions.add(entry.session_id)

        return summaries

    def get_latest_entry_by_session(
        self, session_id: uuid.UUID
    ) -> tuple[JournalEntry, dict[str, Any]] | None:
        """Return latest entry + event metadata for a session."""
        entries = self.list_entries_by_session(session_id=session_id, limit=1)
        if not entries:
            return None
        return entries[0]

    def list_entries_by_session(
        self,
        session_id: uuid.UUID,
        limit: int = 50,
        before: datetime | None = None,
    ) -> list[tuple[JournalEntry, dict[str, Any]]]:
        """Return entries + event metadata for a session ordered by newest first."""
        stmt = (
            select(JournalEntry)
            .where(JournalEntry.session_id == session_id)
            .order_by(JournalEntry.created_at.desc())
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
                .order_by(JournalEntry.created_at.desc())
                .limit(limit)
            )

        entries = self.session.execute(stmt).scalars().all()
        entry_ids = [entry.id for entry in entries]
        events_by_entry = self._events_by_aggregate_id(entry_ids)

        return [
            (entry, events_by_entry.get(entry.id, {}).get("metadata", {}))
            for entry in entries
        ]

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
