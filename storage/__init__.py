# storage/__init__.py

from typing import Optional, Any
from datetime import datetime


class TranscriptRepository:
    """Abstract interface for storing and retrieving transcripts."""

    def start_session(self, title: Optional[str] = None,
                      metadata: Optional[dict] = None) -> int:
        """Create a new session row and return its id."""
        raise NotImplementedError

    def end_session(self, session_id: int,
                    ended_at: Optional[datetime] = None) -> None:
        """Mark session as ended."""
        raise NotImplementedError

    def save_utterance(
        self,
        session_id: int,
        start_time: datetime,
        end_time: datetime,
        text: str,
        source: str = "stt",
    ) -> int:
        """Persist one utterance and return its id."""
        raise NotImplementedError

    def save_action(
        self,
        session_id: int,
        time: datetime,
        action_type: str,
        raw_text: Optional[str] = None,
    ) -> int:
        """Persist one control action and return its id."""
        raise NotImplementedError

    # Optional later: list_sessions, list_utterances, etc.
