"""Tool-level examples for repository-backed journal writes."""

from __future__ import annotations

import os

from sqlalchemy.exc import OperationalError

from db.connection import create_db_engine
from db.models import Base
from tools.journal_tool import JournalWriteTool


def resolve_database_url() -> str:
    """Return DATABASE_URL or local SQLite fallback."""
    return os.getenv("DATABASE_URL", "sqlite+pysqlite:///data/journal.sqlite")


def run_tool_example() -> dict[str, str]:
    """Initialize schema and write one journal entry through the tool."""
    database_url = resolve_database_url()
    engine = create_db_engine(database_url)
    try:
        Base.metadata.create_all(engine, checkfirst=True)
    except OperationalError as exc:
        # Defensive fallback for repeated local SQLite runs with pre-existing tables.
        if "already exists" not in str(exc).lower():
            raise

    tool = JournalWriteTool(database_url=database_url)
    result = tool.write_entry(
        content="Tool example: write through JournalWriteTool",
        entry_type="general",
        metadata={"source": "tools.examples"},
    )
    return result


if __name__ == "__main__":
    print(run_tool_example())
