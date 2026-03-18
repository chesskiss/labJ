"""DB slice examples: create schema, write sample data, inspect counts."""

from __future__ import annotations

import os
from typing import Any

from sqlalchemy import text

from db.connection import create_db_engine
from db.models import Base
from tools.journal_tool import JournalWriteTool


def resolve_database_url() -> str:
    """Return DATABASE_URL or a local SQLite default for quick examples."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    return "sqlite+pysqlite:///data/journal.sqlite"


def run_db_example() -> dict[str, Any]:
    """Create tables, write sample entries, and return summary metrics."""
    database_url = resolve_database_url()
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)

    tool = JournalWriteTool(database_url=database_url)
    write_1 = tool.write_entry(
        content="Sample observation: solution turned cloudy.",
        entry_type="observation",
        metadata={"source": "db_example", "stage": "persistence_slice"},
    )
    write_2 = tool.write_entry(
        content="Sample value: 5.2 mL",
        entry_type="value",
        metadata={"source": "db_example", "stage": "persistence_slice"},
    )

    with engine.connect() as conn:
        journal_count = conn.execute(
            text("select count(*) from journal_entries")
        ).scalar_one()
        event_count = conn.execute(text("select count(*) from events")).scalar_one()
        latest_journal = conn.execute(
            text(
                "select id, entry_type, created_at "
                "from journal_entries order by created_at desc limit 3"
            )
        ).fetchall()
        latest_events = conn.execute(
            text(
                "select event_type, aggregate_type, created_at "
                "from events order by created_at desc limit 3"
            )
        ).fetchall()

    return {
        "database_url": database_url,
        "writes": [write_1, write_2],
        "counts": {"journal_entries": journal_count, "events": event_count},
        "latest_journal_entries": [tuple(row) for row in latest_journal],
        "latest_events": [tuple(row) for row in latest_events],
    }


if __name__ == "__main__":
    summary = run_db_example()
    print("DB example complete")
    print(f"database_url: {summary['database_url']}")
    print(f"counts: {summary['counts']}")
    print("writes:")
    for item in summary["writes"]:
        print(" ", item)
    print("latest_journal_entries:")
    for row in summary["latest_journal_entries"]:
        print(" ", row)
    print("latest_events:")
    for row in summary["latest_events"]:
        print(" ", row)
