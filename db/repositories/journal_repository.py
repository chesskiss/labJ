"""Repository for journal entry persistence and event logging."""

from __future__ import annotations

import uuid
from typing import Any, Optional

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
