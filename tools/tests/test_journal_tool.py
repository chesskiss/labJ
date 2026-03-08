from pathlib import Path

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
