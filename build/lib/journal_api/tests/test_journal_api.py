from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import journal_api.app as app_module
from db.models import Base, Event, JournalEntry


def _client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "journal_api.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    app_module.reset_journal_api_state_for_tests()
    return TestClient(app_module.app)


def test_health(tmp_path: Path):
    client = _client(tmp_path)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "journal_api"}


def test_create_entry_writes_journal_and_event(tmp_path: Path):
    client = _client(tmp_path)
    session_id = str(uuid.uuid4())
    base_revision_id = str(uuid.uuid4())

    response = client.post(
        "/journal/entries",
        json={
            "session_id": session_id,
            "base_revision_id": base_revision_id,
            "title": "Manual Session",
            "content": "<p>Manual note</p>",
            "entry_type": "general",
            "source": "ui_manual",
            "metadata": {"notes": "from test"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == session_id
    assert payload["created_by"] == "ui_manual"
    assert payload["title"] == "Manual Session"
    assert payload["revision_kind"] == "manual_edit"
    assert payload["parent_revision_id"] is None
    assert payload["metadata"]["base_revision_id"] == base_revision_id

    engine = create_engine(os.environ["DATABASE_URL"], future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        entries = session.execute(select(JournalEntry)).scalars().all()
        events = session.execute(select(Event)).scalars().all()

    assert len(entries) == 1
    assert len(events) == 1
    assert events[0].metadata_json["source"] == "ui_manual"
    assert events[0].metadata_json["title"] == "Manual Session"
    assert events[0].metadata_json["base_revision_id"] == base_revision_id


def test_sessions_latest_and_history(tmp_path: Path):
    client = _client(tmp_path)
    session_a = str(uuid.uuid4())
    session_b = str(uuid.uuid4())

    r1 = client.post(
        "/journal/entries",
        json={
            "session_id": session_a,
            "title": "Session A",
            "content": "<p>A1</p>",
            "entry_type": "general",
            "source": "ui_manual",
        },
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/journal/entries",
        json={
            "session_id": session_a,
            "title": "Session A Updated",
            "content": "<p>A2</p>",
            "entry_type": "general",
            "source": "ui_manual",
        },
    )
    assert r2.status_code == 200

    r3 = client.post(
        "/journal/entries",
        json={
            "session_id": session_b,
            "title": "Session B",
            "content": "<p>B1</p>",
            "entry_type": "value",
            "source": "ui_command",
        },
    )
    assert r3.status_code == 200

    sessions_response = client.get("/journal/sessions")
    assert sessions_response.status_code == 200
    sessions_payload = sessions_response.json()["sessions"]
    assert len(sessions_payload) == 2

    by_session = {item["session_id"]: item for item in sessions_payload}
    assert by_session[session_a]["title"] == "Session A Updated"
    assert by_session[session_b]["latest_entry_type"] == "value"
    assert by_session[session_a]["latest_revision_kind"] == "manual_edit"
    assert by_session[session_b]["latest_revision_kind"] == "llm_edit"
    assert by_session[session_a]["head_revision_id"] is not None

    latest_response = client.get(f"/journal/sessions/{session_a}/latest")
    assert latest_response.status_code == 200
    latest_payload = latest_response.json()
    assert latest_payload["content"] == "<p>A2</p>"
    assert latest_payload["revision_kind"] == "manual_edit"
    assert latest_payload["parent_revision_id"] is not None

    history_response = client.get(
        f"/journal/sessions/{session_a}/history", params={"limit": 1}
    )
    assert history_response.status_code == 200
    history_entries = history_response.json()["entries"]
    assert len(history_entries) == 1
    assert history_entries[0]["content"] == "<p>A2</p>"

    before_value = history_entries[0]["created_at"]
    history_before_response = client.get(
        f"/journal/sessions/{session_a}/history",
        params={"before": before_value, "limit": 5},
    )
    assert history_before_response.status_code == 200
    older_entries = history_before_response.json()["entries"]
    assert older_entries
    assert older_entries[0]["content"] == "<p>A1</p>"


def test_latest_returns_404_for_missing_session(tmp_path: Path):
    client = _client(tmp_path)
    missing_session = str(uuid.uuid4())

    response = client.get(f"/journal/sessions/{missing_session}/latest")
    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == "session_not_found"
    assert payload["details"]["session_id"] == missing_session


def test_create_entry_conflict_on_base_revision_id_mismatch(tmp_path: Path):
    client = _client(tmp_path)
    session_id = str(uuid.uuid4())

    first = client.post(
        "/journal/entries",
        json={
            "session_id": session_id,
            "title": "Session",
            "content": "<p>v1</p>",
            "entry_type": "general",
            "source": "ui_manual",
        },
    )
    assert first.status_code == 200

    conflict = client.post(
        "/journal/entries",
        json={
            "session_id": session_id,
            "base_revision_id": str(uuid.uuid4()),
            "title": "Session",
            "content": "<p>v2</p>",
            "entry_type": "general",
            "source": "ui_manual",
        },
    )
    assert conflict.status_code == 409
    conflict_payload = conflict.json()
    assert conflict_payload["code"] == "revision_conflict"
    assert conflict_payload["details"]["session_id"] == session_id
    assert (
        conflict_payload["details"]["current_head_revision_id"]
        == first.json()["entry_id"]
    )


def test_validation_errors_use_structured_response(tmp_path: Path):
    client = _client(tmp_path)

    response = client.post(
        "/journal/entries",
        json={
            "session_id": str(uuid.uuid4()),
            "title": "",
            "content": "<p>bad</p>",
            "entry_type": "general",
            "source": "ui_manual",
        },
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "validation_error"
    assert "errors" in payload["details"]
