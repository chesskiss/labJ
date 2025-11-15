# tests/test_storage.py

from datetime import datetime, timezone
import sqlite3

import pytest

from storage.sqlite_repository import SQLiteTranscriptRepository


def test_start_session_creates_row(tmp_path):
    db_file = tmp_path / "journal.sqlite"
    repo = SQLiteTranscriptRepository(db_path=db_file)

    session_id = repo.start_session(title="Test session", metadata={"foo": "bar"})
    assert isinstance(session_id, int)

    cur = repo.conn.cursor()
    cur.execute("SELECT id, title, metadata FROM sessions")
    rows = cur.fetchall()
    assert len(rows) == 1

    row = rows[0]
    assert row["id"] == session_id
    assert row["title"] == "Test session"
    # metadata is stored as JSON string
    assert '"foo": "bar"' in row["metadata"]


def test_save_utterance_sequence_increments(tmp_path):
    db_file = tmp_path / "journal.sqlite"
    repo = SQLiteTranscriptRepository(db_path=db_file)

    session_id = repo.start_session()
    now = datetime.now(timezone.utc)

    repo.save_utterance(session_id, now, now, "first")
    repo.save_utterance(session_id, now, now, "second")

    cur = repo.conn.cursor()
    cur.execute(
        """
        SELECT text, sequence_index
        FROM utterances
        WHERE session_id = ?
        ORDER BY sequence_index
        """,
        (session_id,),
    )
    rows = cur.fetchall()
    texts = [r["text"] for r in rows]
    seqs = [r["sequence_index"] for r in rows]

    assert texts == ["first", "second"]
    assert seqs == [0, 1]


def test_save_action_persists_action(tmp_path):
    db_file = tmp_path / "journal.sqlite"
    repo = SQLiteTranscriptRepository(db_path=db_file)

    session_id = repo.start_session()
    now = datetime.now(timezone.utc)

    action_id = repo.save_action(
        session_id, now, "pause_transcription", raw_text="please stop"
    )
    assert isinstance(action_id, int)

    cur = repo.conn.cursor()
    cur.execute(
        "SELECT action_type, raw_text FROM actions WHERE id = ?",
        (action_id,),
    )
    row = cur.fetchone()
    assert row is not None
    assert row["action_type"] == "pause_transcription"
    assert row["raw_text"] == "please stop"


def test_end_session_sets_ended_at(tmp_path):
    db_file = tmp_path / "journal.sqlite"
    repo = SQLiteTranscriptRepository(db_path=db_file)

    session_id = repo.start_session()
    repo.end_session(session_id)

    cur = repo.conn.cursor()
    cur.execute(
        "SELECT ended_at FROM sessions WHERE id = ?",
        (session_id,),
    )
    row = cur.fetchone()
    assert row is not None
    assert row["ended_at"] is not None
