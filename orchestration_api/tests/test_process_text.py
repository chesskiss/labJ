from __future__ import annotations

from pathlib import Path
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import orchestration_api.app as app_module
from context_action_plan.enums import IntentName, NoteType
from context_action_plan.schemas import (
    EntityBundle,
    IntentInfo,
    NoteCapture,
    NotePayload,
)
from context_action_plan.llm_parser import reset_default_llm_parser_for_tests
from db.models import Event, JournalEntry
from orchestration_api.runtime import reset_runtime_for_tests


def _client_with_sqlite(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "orchestrator.sqlite"
    # Ensure runtime uses a deterministic local DB for note persistence tests.
    import os

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("GROQ_API_KEY", None)
    reset_default_llm_parser_for_tests()
    reset_runtime_for_tests()
    return TestClient(app_module.app)


def test_process_text_action_plan(tmp_path: Path):
    client = _client_with_sqlite(tmp_path)
    response = client.post(
        "/process_text",
        json={
            "text": "take result from calculator 1, add 2, convert liters to mL, write to journal"
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["parsed"]["kind"] == "action_plan"
    assert payload["validation"]["is_executable"] is True
    # Runtime can fail/succeed depending on slot state; both are valid orchestration outputs.
    assert payload["execution"]["status"] in {"succeeded", "failed"}


def test_process_text_note_capture_persists(tmp_path: Path):
    client = _client_with_sqlite(tmp_path)
    response = client.post(
        "/process_text",
        json={"text": "sample 4 became cloudy after heating"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["parsed"]["kind"] == "note_capture"
    assert payload["execution"]["status"] == "succeeded"
    assert payload["execution"]["final_output"]["status"] == "success"
    assert "entry_id" in payload["execution"]["final_output"]
    assert payload["execution"]["final_output"]["entry_type"] == "observation"


def test_process_text_note_capture_respects_session_id_and_metadata(tmp_path: Path):
    client = _client_with_sqlite(tmp_path)
    requested_session_id = "22222222-2222-2222-2222-222222222222"
    response = client.post(
        "/process_text",
        json={
            "text": "sample 7 became clearer after cooling",
            "session_id": requested_session_id,
            "metadata": {"title": "Cooling Session", "operator": "arnold"},
        },
    )
    assert response.status_code == 200

    db_url = f"sqlite+pysqlite:///{tmp_path / 'orchestrator.sqlite'}"
    engine = create_engine(db_url, future=True)
    with Session(engine) as session:
        entry = session.execute(select(JournalEntry)).scalars().one()
        event = (
            session.execute(select(Event).where(Event.aggregate_id == entry.id))
            .scalars()
            .one()
        )

    assert str(entry.session_id) == requested_session_id
    assert event.metadata_json["source"] == "executor_note_capture"
    assert event.metadata_json["title"] == "Cooling Session"
    assert event.metadata_json["operator"] == "arnold"


def test_process_text_note_capture_appends_within_session(tmp_path: Path):
    client = _client_with_sqlite(tmp_path)
    requested_session_id = "33333333-3333-3333-3333-333333333333"
    requested_session_uuid = uuid.UUID(requested_session_id)

    first = client.post(
        "/process_text",
        json={
            "text": "sample 4 became cloudy after heating",
            "session_id": requested_session_id,
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/process_text",
        json={
            "text": "sample 4 became clearer after cooling",
            "session_id": requested_session_id,
        },
    )
    assert second.status_code == 200

    db_url = f"sqlite+pysqlite:///{tmp_path / 'orchestrator.sqlite'}"
    engine = create_engine(db_url, future=True)
    with Session(engine) as session:
        rows = (
            session.execute(
                select(JournalEntry)
                .where(JournalEntry.session_id == requested_session_uuid)
                .order_by(JournalEntry.created_at.asc())
            )
            .scalars()
            .all()
        )

    assert len(rows) == 2
    assert rows[0].content == "sample 4 became cloudy after heating"
    assert (
        rows[1].content
        == "sample 4 became cloudy after heating\nsample 4 became clearer after cooling"
    )


def test_process_text_not_a_command(tmp_path: Path):
    client = _client_with_sqlite(tmp_path)
    response = client.post("/process_text", json={"text": "hello how are you"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["parsed"]["kind"] == "clarification_needed"
    assert payload["parsed"]["status"] == "not_a_command"
    assert payload["validation"]["is_executable"] is False
    assert payload["execution"]["status"] == "not_executed"


def test_process_text_invalid_session_id_returns_422(tmp_path: Path):
    client = _client_with_sqlite(tmp_path)
    response = client.post(
        "/process_text",
        json={"text": "sample 4 became cloudy", "session_id": "not-a-uuid"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error_code"] == "INVALID_SESSION_ID"


def test_runtime_state_endpoint(tmp_path: Path):
    client = _client_with_sqlite(tmp_path)
    response = client.get("/runtime_state")
    assert response.status_code == 200
    payload = response.json()
    assert "active_session_exists" in payload
    assert "mock_journal_entries_count" in payload
    assert "mock_observations_count" in payload
    assert "journal_tool_enabled" in payload
    assert payload["journal_tool_enabled"] is True


def test_process_audio_success(tmp_path: Path, monkeypatch):
    client = _client_with_sqlite(tmp_path)

    class _FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "text": "sample 4 became cloudy after heating",
                "segments": [],
                "language": "en",
                "language_probability": 0.99,
                "duration_seconds": 1.0,
                "processing_time_seconds": 0.1,
            }

    def _fake_post(*args, **kwargs):
        del args, kwargs
        return _FakeResponse()

    monkeypatch.setattr(app_module.requests, "post", _fake_post)

    response = client.post(
        "/process_audio",
        files={"file": ("test.wav", b"fake-bytes", "audio/wav")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["transcription"]["text"] == "sample 4 became cloudy after heating"
    assert payload["parsed"]["kind"] == "note_capture"
    assert payload["execution"]["status"] == "succeeded"
    assert payload["execution"]["final_output"]["entry_type"] == "observation"


def test_process_audio_stt_failure(tmp_path: Path, monkeypatch):
    client = _client_with_sqlite(tmp_path)

    def _fake_post(*args, **kwargs):
        del args, kwargs
        raise app_module.requests.RequestException("connection failed")

    monkeypatch.setattr(app_module.requests, "post", _fake_post)

    response = client.post(
        "/process_audio",
        files={"file": ("test.wav", b"fake-bytes", "audio/wav")},
    )
    assert response.status_code == 502
    detail = response.json()["detail"]
    assert detail["error_code"] == "STT_REQUEST_FAILED"


def test_process_text_uses_llm_parser_function(tmp_path: Path, monkeypatch):
    client = _client_with_sqlite(tmp_path)

    def _fake_llm_parser(text: str):
        del text
        return NoteCapture(
            user_text="from llm parser",
            intent=IntentInfo(name=IntentName.RECORD_OBSERVATION, confidence=0.91),
            note=NotePayload(note_type=NoteType.OBSERVATION, content="from llm parser"),
            entities=EntityBundle(free_text_value="from llm parser"),
        )

    monkeypatch.setattr(app_module, "parse_transcript_with_fallback", _fake_llm_parser)
    response = client.post("/process_text", json={"text": "anything"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["parsed"]["kind"] == "note_capture"
    assert payload["parsed"]["user_text"] == "from llm parser"
