# agents/models.py
from sqlalchemy import Column, Integer, Text, String
from .db import Base


class Session(Base):
    """
    Existing 'sessions' table:

    id          INTEGER PRIMARY KEY
    started_at  TEXT NOT NULL
    ended_at    TEXT NULL
    title       TEXT NULL
    metadata    TEXT NULL
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    started_at = Column(Text, nullable=False)
    ended_at = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    # 'metadata' is reserved by SQLAlchemy's Base, so we map the column
    # named "metadata" to a Python attribute with a different name:
    metadata_json = Column("metadata", Text, nullable=True)
    created_at = Column(Text, nullable=False)


class Utterance(Base):
    """
    Existing 'utterances' table:

    id             INTEGER PRIMARY KEY
    session_id     INTEGER NOT NULL
    start_time     TEXT NOT NULL
    end_time       TEXT NOT NULL
    sequence_index INTEGER NOT NULL
    text           TEXT NOT NULL
    source         TEXT NOT NULL DEFAULT 'stt'
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    """
    __tablename__ = "utterances"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, nullable=False, index=True)
    start_time = Column(Text, nullable=False)
    end_time = Column(Text, nullable=False)
    sequence_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)


class Action(Base):
    """
    Existing 'actions' table:

    id          INTEGER PRIMARY KEY
    session_id  INTEGER NOT NULL
    time        TEXT NOT NULL
    action_type TEXT NOT NULL
    raw_text    TEXT NULL
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    """
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(Integer, nullable=False, index=True)
    time = Column(Text, nullable=False)
    action_type = Column(Text, nullable=False)
    raw_text = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)
