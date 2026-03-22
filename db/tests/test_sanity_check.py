import uuid
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from db.models import Base, JournalSession
from db.repositories.journal_repository import JournalRepository
from db.sanity_check import run_sanity_check


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path}"


def test_sanity_check_passes_on_consistent_rows(tmp_path: Path):
    db_path = tmp_path / "sanity_ok.sqlite"
    db_url = _sqlite_url(db_path)
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)

    session_id = uuid.uuid4()
    with Session(engine) as session:
        repo = JournalRepository(session)
        repo.create_entry(
            content="<p>entry</p>",
            entry_type="general",
            session_id=session_id,
            metadata={"source": "pytest", "title": "Pytest Session"},
            created_by="ui_manual",
        )

    report = run_sanity_check(db_url)
    assert report.ok
    assert report.stats is not None
    assert report.stats.entries == 1
    assert report.stats.revisions == 1


def test_sanity_check_detects_non_latest_head(tmp_path: Path):
    db_path = tmp_path / "sanity_bad.sqlite"
    db_url = _sqlite_url(db_path)
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)

    session_id = uuid.uuid4()
    with Session(engine) as session:
        repo = JournalRepository(session)
        first = repo.create_entry(
            content="<p>v1</p>",
            entry_type="general",
            session_id=session_id,
            metadata={"source": "pytest", "title": "Pytest Session"},
            created_by="ui_manual",
        )
        repo.create_entry(
            content="<p>v2</p>",
            entry_type="general",
            session_id=session_id,
            metadata={"source": "pytest", "title": "Pytest Session"},
            created_by="ui_manual",
        )

        session_row = session.execute(
            select(JournalSession).where(JournalSession.id == session_id)
        ).scalar_one()
        session_row.head_revision_id = first.id
        session.commit()

    report = run_sanity_check(db_url)
    assert not report.ok
    assert any(issue.code == "session_head_not_latest" for issue in report.errors)
