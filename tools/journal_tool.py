"""Journal write tool backed by repository persistence."""

from __future__ import annotations

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
