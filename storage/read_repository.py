# storage/read_repository.py

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from env_config import DB_PATH


@dataclass
class SessionSummary:
    id: int
    started_at: str
    ended_at: Optional[str]
    title: Optional[str]


@dataclass
class UtteranceView:
    id: int
    session_id: int
    start_time: str
    end_time: str
    sequence_index: int
    text: str
    source: str


@dataclass
class ActionView:
    id: int
    session_id: int
    time: str
    action_type: str
    raw_text: Optional[str]


class JournalReadRepository:
    """Read-only access to journal data for GUI / analytics."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DB_PATH)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    # --- Sessions ---

    def list_sessions(self) -> List[SessionSummary]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, started_at, ended_at, title
            FROM sessions
            ORDER BY started_at DESC
            """
        )
        rows = cur.fetchall()
        return [
            SessionSummary(
                id=row["id"],
                started_at=row["started_at"],
                ended_at=row["ended_at"],
                title=row["title"],
            )
            for row in rows
        ]

    def get_session(self, session_id: int) -> Optional[SessionSummary]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, started_at, ended_at, title
            FROM sessions
            WHERE id = ?
            """,
            (session_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return SessionSummary(
            id=row["id"],
            started_at=row["started_at"],
            ended_at=row["ended_at"],
            title=row["title"],
        )

    # --- Utterances ---

    def get_utterances(self, session_id: int) -> List[UtteranceView]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, session_id, start_time, end_time,
                   sequence_index, text, source
            FROM utterances
            WHERE session_id = ?
            ORDER BY sequence_index
            """,
            (session_id,),
        )
        rows = cur.fetchall()
        return [
            UtteranceView(
                id=row["id"],
                session_id=row["session_id"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                sequence_index=row["sequence_index"],
                text=row["text"],
                source=row["source"],
            )
            for row in rows
        ]

    # --- Actions ---

    def get_actions(self, session_id: int) -> List[ActionView]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, session_id, time, action_type, raw_text
            FROM actions
            WHERE session_id = ?
            ORDER BY time
            """,
            (session_id,),
        )
        rows = cur.fetchall()
        return [
            ActionView(
                id=row["id"],
                session_id=row["session_id"],
                time=row["time"],
                action_type=row["action_type"],
                raw_text=row["raw_text"],
            )
            for row in rows
        ]

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
