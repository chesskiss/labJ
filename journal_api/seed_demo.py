"""Seed demo journal data through the Journal API entrypoint.

Usage:
  uv run python -m journal_api.seed_demo

Optional env vars:
  JOURNAL_SEED_RESET=1   # deletes existing rows before seeding
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient
from sqlalchemy import delete

from db.connection import create_db_engine, create_session_factory
from db.models import Base, Event, JournalEntry, JournalRevision, JournalSession
from journal_api.app import app, resolve_database_url


@dataclass(frozen=True)
class SeedRow:
    session_id: uuid.UUID
    title: str
    content: str
    source: str
    entry_type: str


def _reset_if_requested() -> None:
    if os.getenv("JOURNAL_SEED_RESET", "0") != "1":
        return

    database_url = resolve_database_url()
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine, checkfirst=True)
    session_factory = create_session_factory(database_url)

    with session_factory() as session:
        session.execute(delete(Event))
        session.execute(delete(JournalRevision))
        session.execute(delete(JournalSession))
        session.execute(delete(JournalEntry))
        session.commit()


def _rows() -> list[SeedRow]:
    session_a = uuid.uuid4()
    session_b = uuid.uuid4()

    return [
        SeedRow(
            session_id=session_a,
            title="Observation Window",
            content="<p>Culture OD600 measured every 20 min after media shift.</p>",
            source="ui_manual",
            entry_type="general",
        ),
        SeedRow(
            session_id=session_a,
            title="Observation Window",
            content="Flask A stable at 0.44. Flask B climbed from 0.41 to 0.49.",
            source="ui_command",
            entry_type="observation",
        ),
        SeedRow(
            session_id=session_a,
            title="Observation Window",
            content="<p>Adjusted incubation from 30C to 28C.</p>",
            source="ui_command",
            entry_type="general",
        ),
        SeedRow(
            session_id=session_b,
            title="Enzyme Titration",
            content="<p>Baseline run complete. Preparing dilution 1:5.</p>",
            source="ui_manual",
            entry_type="general",
        ),
        SeedRow(
            session_id=session_b,
            title="Enzyme Titration",
            content="Sample 6 remained clear after reagent addition.",
            source="ui_command",
            entry_type="observation",
        ),
    ]


def main() -> None:
    _reset_if_requested()

    rows = _rows()
    created = 0
    with TestClient(app) as client:
        for row in rows:
            response = client.post(
                "/journal/entries",
                json={
                    "session_id": str(row.session_id),
                    "title": row.title,
                    "content": row.content,
                    "entry_type": row.entry_type,
                    "source": row.source,
                    "metadata": {"seed": True},
                },
            )
            response.raise_for_status()
            created += 1

    print(
        f"Seeded {created} entries across {len({r.session_id for r in rows})} sessions"
    )
    for session_id in sorted({r.session_id for r in rows}, key=str):
        print(f"- session_id={session_id}")


if __name__ == "__main__":
    main()
