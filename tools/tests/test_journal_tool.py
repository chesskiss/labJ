from pathlib import Path
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from db.models import Base, Event, JournalEntry
from tools.journal_tool import JournalWriteTool


def test_journal_tool_writes_entry_and_event(tmp_path: Path):
    db_path = tmp_path / "journal_tool_test.sqlite"
    database_url = f"sqlite+pysqlite:///{db_path}"

    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)

    tool = JournalWriteTool(database_url=database_url)
    payload = tool.write_entry(
        content="result 5.2 mL",
        entry_type="value",
        metadata={"source": "tool_test"},
    )

    assert payload["status"] == "success"
    assert payload["entry_type"] == "value"

    with Session(engine) as session:
        entries = session.execute(select(JournalEntry)).scalars().all()
        events = session.execute(select(Event)).scalars().all()
        assert len(entries) == 1
        assert len(events) == 1
        assert entries[0].content == "result 5.2 mL"
        assert events[0].event_type == "journal_entry_created"


def test_get_latest_session_id_returns_latest_non_null(tmp_path: Path):
    db_path = tmp_path / "journal_tool_latest.sqlite"
    database_url = f"sqlite+pysqlite:///{db_path}"

    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)

    tool = JournalWriteTool(database_url=database_url)
    session_a = uuid.uuid4()
    session_b = uuid.uuid4()

    tool.write_entry(
        content="older",
        entry_type="general",
        metadata={"source": "tool_test"},
        session_id=session_a,
    )
    tool.write_entry(
        content="newer",
        entry_type="general",
        metadata={"source": "tool_test"},
        session_id=session_b,
    )

    assert tool.get_latest_session_id() == session_b
