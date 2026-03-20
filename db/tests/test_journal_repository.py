import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from db.models import Base, Event, JournalEntry, JournalRevision, JournalSession
from db.repositories.journal_repository import JournalRepository


def test_create_entry_writes_journal_and_event():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    session_id = uuid.uuid4()
    with Session(engine) as session:
        repo = JournalRepository(session)
        entry = repo.create_entry(
            content="sample 4 became cloudy",
            entry_type="observation",
            session_id=session_id,
            metadata={"source": "test"},
            created_by="pytest",
        )

        assert isinstance(entry.id, uuid.UUID)
        assert entry.entry_type == "observation"
        assert entry.created_by == "pytest"

        stored_entry = session.execute(
            select(JournalEntry).where(JournalEntry.id == entry.id)
        ).scalar_one()
        assert stored_entry.content == "sample 4 became cloudy"

        event = session.execute(
            select(Event).where(Event.aggregate_id == entry.id)
        ).scalar_one()
        assert event.event_type == "journal_entry_created"
        assert event.aggregate_type == "journal_entry"
        assert event.payload["entry_type"] == "observation"
        assert event.metadata_json["source"] == "test"

        revision = session.execute(
            select(JournalRevision).where(JournalRevision.id == entry.id)
        ).scalar_one()
        assert revision.session_id == session_id
        assert revision.entry_type == "observation"
        assert revision.created_by == "pytest"

        session_row = session.execute(
            select(JournalSession).where(JournalSession.id == session_id)
        ).scalar_one()
        assert session_row.head_revision_id == revision.id
