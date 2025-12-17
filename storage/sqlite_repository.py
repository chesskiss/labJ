# storage/sqlite_repository.py

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from storage import TranscriptRepository
from config import DB_PATH


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _to_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string in UTC-ish form."""
    # For now assume dt is already UTC or treat as such
    return dt.strftime(ISO_FORMAT)


class SQLiteTranscriptRepository(TranscriptRepository):
    """
    SQLite-based implementation of TranscriptRepository.

    - Uses a single .sqlite file.
    - Initializes schema on first use.
    - safe for simple, single-process usage.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DB_PATH)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._enable_wal()
        self._init_schema()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _enable_wal(self) -> None:
        """Enable WAL mode for better concurrency (1 writer, many readers)."""
        cur = self.conn.cursor()
        cur.execute("PRAGMA journal_mode = WAL;")
        self.conn.commit()

    def _init_schema(self) -> None:
        """Create tables if they don't exist yet."""
        cur = self.conn.cursor()

        # sessions
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at   TEXT NOT NULL,
                ended_at     TEXT,
                title        TEXT,
                metadata     TEXT,
                created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # utterances
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS utterances (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      INTEGER NOT NULL
                                REFERENCES sessions(id) ON DELETE CASCADE,
                start_time      TEXT NOT NULL,
                end_time        TEXT NOT NULL,
                sequence_index  INTEGER NOT NULL,
                text            TEXT NOT NULL,
                source          TEXT NOT NULL DEFAULT 'stt',
                created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_utterances_session_time
                ON utterances(session_id, start_time);
            """
        )

        # actions
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS actions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL
                            REFERENCES sessions(id) ON DELETE CASCADE,
                time        TEXT NOT NULL,
                action_type TEXT NOT NULL,
                raw_text    TEXT,
                created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_actions_session_time
                ON actions(session_id, time);
            """
        )

        self.conn.commit()

    # ------------------------------------------------------------------
    # API implementation
    # ------------------------------------------------------------------
    def start_session(
        self,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        now = datetime.now(timezone.utc)
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO sessions (started_at, title, metadata, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                _to_iso(now),
                title,
                json.dumps(metadata or {}),
                _to_iso(now),
            ),
        )
        self.conn.commit()
        session_id = cur.lastrowid
        return int(session_id)

    def end_session(self, session_id: int,
                    ended_at: Optional[datetime] = None) -> None:
        ended = ended_at or datetime.now(timezone.utc)
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE sessions
               SET ended_at = ?
             WHERE id = ?
            """,
            (_to_iso(ended), session_id),
        )
        self.conn.commit()

    def _get_next_sequence_index(self, session_id: int) -> int:
        """Compute next sequence_index for this session."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT COALESCE(MAX(sequence_index), -1) AS max_seq "
            "FROM utterances WHERE session_id = ?",
            (session_id,),
        )
        row = cur.fetchone()
        max_seq = row["max_seq"] if row is not None else -1
        return int(max_seq) + 1

    def save_utterance(
        self,
        session_id: int,
        start_time: datetime,
        end_time: datetime,
        text: str,
        source: str = "stt",
    ) -> int:
        seq = self._get_next_sequence_index(session_id)
        cur = self.conn.cursor()
        iso_start = _to_iso(start_time)
        iso_end = _to_iso(end_time)
        now = datetime.now(timezone.utc)

        cur.execute(
            """
            INSERT INTO utterances (
                session_id, start_time, end_time,
                sequence_index, text, source, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                iso_start,
                iso_end,
                seq,
                text,
                source,
                _to_iso(now),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def save_action(
        self,
        session_id: int,
        time: datetime,
        action_type: str,
        raw_text: Optional[str] = None,
    ) -> int:
        cur = self.conn.cursor()
        iso_time = _to_iso(time)
        now = datetime.now(timezone.utc)

        cur.execute(
            """
            INSERT INTO actions (
                session_id, time, action_type, raw_text, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                iso_time,
                action_type,
                raw_text,
                _to_iso(now),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
