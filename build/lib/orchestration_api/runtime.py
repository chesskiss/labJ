"""Runtime factory helpers for orchestration API."""

from __future__ import annotations

import os

from db.connection import create_db_engine
from db.models import Base
from executor_runtime.mock_state import MockRuntime
from tools.journal_tool import JournalWriteTool

DEFAULT_SQLITE_URL = "sqlite+pysqlite:///data/journal.sqlite"

_RUNTIME_SINGLETON: MockRuntime | None = None


def resolve_database_url() -> str:
    """Resolve DB URL with local SQLite fallback."""
    return os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)


def get_runtime() -> MockRuntime:
    """Return process-wide runtime singleton configured with journal tool."""
    global _RUNTIME_SINGLETON
    if _RUNTIME_SINGLETON is None:
        runtime = MockRuntime()
        database_url = resolve_database_url()
        engine = create_db_engine(database_url)
        Base.metadata.create_all(engine, checkfirst=True)
        runtime.journal_write_tool = JournalWriteTool(database_url=database_url)
        _RUNTIME_SINGLETON = runtime
    return _RUNTIME_SINGLETON


def reset_runtime_for_tests() -> None:
    """Reset singleton runtime (test-only helper)."""
    global _RUNTIME_SINGLETON
    _RUNTIME_SINGLETON = None
