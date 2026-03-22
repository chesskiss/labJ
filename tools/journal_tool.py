"""Journal write tool backed by repository persistence."""

from __future__ import annotations

import html
import uuid
from typing import Any, Optional

from db.connection import create_session_factory
from db.repositories.journal_repository import JournalRepository


class JournalWriteTool:
    """Tool facade for writing journal entries via repository."""

    def __init__(self, database_url: Optional[str] = None):
        self.session_factory = create_session_factory(database_url)

    def write_entry(
        self,
        content: str,
        entry_type: str,
        metadata: dict[str, Any],
        session_id: Optional[uuid.UUID] = None,
    ) -> dict[str, str]:
        """Persist a journal entry and return stable success payload."""
        with self.session_factory() as session:
            repo = JournalRepository(session)
            entry = repo.create_entry(
                content=content,
                entry_type=entry_type,
                session_id=session_id,
                metadata=metadata,
            )
            return {
                "status": "success",
                "entry_id": str(entry.id),
                "entry_type": entry.entry_type,
            }

    def get_latest_session_id(self) -> uuid.UUID | None:
        """Return latest non-null session id from persisted journal entries."""
        with self.session_factory() as session:
            repo = JournalRepository(session)
            summaries = repo.list_session_summaries(limit=1)
            if not summaries:
                return None
            raw_session_id = summaries[0].get("session_id")
            if isinstance(raw_session_id, uuid.UUID):
                return raw_session_id
            if isinstance(raw_session_id, str) and raw_session_id.strip():
                try:
                    return uuid.UUID(raw_session_id)
                except ValueError:
                    return None
            return None

    def get_latest_entry_content(self, session_id: uuid.UUID) -> str | None:
        """Return latest content for a session, or None when absent."""
        with self.session_factory() as session:
            repo = JournalRepository(session)
            latest = repo.get_latest_entry_by_session(session_id)
            if latest is None:
                return None
            entry, _metadata = latest
            content = getattr(entry, "content", "")
            if isinstance(content, str):
                return content
            return str(content)


def append_note_to_content(existing_content: str | None, note_text: str) -> str:
    """Append note text onto existing snapshot content (plain text or HTML)."""
    note = note_text.strip()
    if not note:
        return existing_content or ""

    current = (existing_content or "").strip()
    if not current:
        return note

    looks_html = "<" in current and ">" in current
    if looks_html:
        return f"{current}<div>{html.escape(note)}</div>"
    return f"{current}\n{note}"
