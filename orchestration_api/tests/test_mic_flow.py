from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

import orchestration_api.app as app_module
from orchestration_api.mic_manager import reset_mic_manager_for_tests
from orchestration_api.runtime import reset_runtime_for_tests


class _FakeSTTClient:
    def __init__(self, on_transcription=None, **kwargs):  # noqa: ANN003
        del kwargs
        self.on_transcription = on_transcription
        self._started = False

    def start(self) -> None:
        self._started = True

    def stop(self) -> str:
        self._started = False
        return "full fake transcript"

    def emit(self, text: str) -> None:
        if self.on_transcription:
            self.on_transcription(text)


def _client_with_sqlite(tmp_path: Path) -> TestClient:
    import os

    db_path = tmp_path / "orchestrator_mic.sqlite"
    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("GROQ_API_KEY", None)
    reset_runtime_for_tests()
    reset_mic_manager_for_tests()
    return TestClient(app_module.app)


def test_mic_lifecycle_idempotent(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("orchestration_api.mic_manager.STTClient", _FakeSTTClient)
    client = _client_with_sqlite(tmp_path)

    start = client.post("/mic/start", json={})
    assert start.status_code == 200
    assert start.json()["ok"] is True
    assert start.json()["running"] is True

    start_again = client.post("/mic/start", json={})
    assert start_again.status_code == 200
    assert start_again.json()["ok"] is False
    assert start_again.json()["message"] == "already_running"

    status = client.get("/mic/status").json()
    assert status["running"] is True

    stop = client.post("/mic/stop")
    assert stop.status_code == 200
    assert stop.json()["ok"] is True
    assert stop.json()["running"] is False

    stop_again = client.post("/mic/stop")
    assert stop_again.status_code == 200
    assert stop_again.json()["ok"] is False
    assert stop_again.json()["message"] == "already_stopped"


def test_mic_chunk_processing_records_events(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("orchestration_api.mic_manager.STTClient", _FakeSTTClient)
    client = _client_with_sqlite(tmp_path)
    response = client.post("/mic/start", json={})
    assert response.status_code == 200

    manager = app_module.get_mic_manager()
    fake_client = manager._client
    assert isinstance(fake_client, _FakeSTTClient)
    fake_client.emit("sample 4 became cloudy after heating")
    time.sleep(0.1)

    events_resp = client.get("/mic/events")
    assert events_resp.status_code == 200
    events = events_resp.json()["events"]
    assert any(evt.get("type") == "chunk_processed" for evt in events)
    chunk = [evt for evt in events if evt.get("type") == "chunk_processed"][-1]
    assert chunk["parsed"]["kind"] in {
        "note_capture",
        "action_plan",
        "clarification_needed",
    }
    assert "validation" in chunk
    assert "execution" in chunk

    client.post("/mic/stop")


def test_mic_processing_failure_does_not_kill_session(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("orchestration_api.mic_manager.STTClient", _FakeSTTClient)
    client = _client_with_sqlite(tmp_path)
    client.post("/mic/start", json={})

    def _boom(text: str):  # noqa: ANN001
        raise RuntimeError(f"boom: {text}")

    manager = app_module.get_mic_manager()
    manager._pipeline = _boom
    fake_client = manager._client
    assert isinstance(fake_client, _FakeSTTClient)
    fake_client.emit("one")
    fake_client.emit("two")
    time.sleep(0.1)

    events = client.get("/mic/events").json()["events"]
    failures = [evt for evt in events if evt.get("type") == "chunk_processing_failed"]
    assert len(failures) >= 1
    assert client.get("/mic/status").json()["running"] is True
    client.post("/mic/stop")


def test_mic_context_window_carries_recent_chunks_and_resets_on_stop(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setattr("orchestration_api.mic_manager.STTClient", _FakeSTTClient)
    client = _client_with_sqlite(tmp_path)
    client.post("/mic/start", json={})

    captured_contexts: list[str] = []

    def _capture_pipeline(
        text: str, context_window_text: str | None = None, source: str = "direct"
    ):
        del text, source
        captured_contexts.append(context_window_text or "")
        return {"kind": "note_capture"}, {"is_valid": True}, {"status": "succeeded"}

    manager = app_module.get_mic_manager()
    manager._pipeline = _capture_pipeline
    fake_client = manager._client
    assert isinstance(fake_client, _FakeSTTClient)

    fake_client.emit("sample 4 became cloudy after heating")
    fake_client.emit("and then it became clearer")
    time.sleep(0.15)

    assert len(captured_contexts) >= 2
    assert "[current] sample 4 became cloudy after heating" in captured_contexts[0]
    assert "[recent] sample 4 became cloudy after heating" in captured_contexts[1]
    assert "[current] and then it became clearer" in captured_contexts[1]

    client.post("/mic/stop")
    client.post("/mic/start", json={})
    manager = app_module.get_mic_manager()
    manager._pipeline = _capture_pipeline
    fake_client = manager._client
    assert isinstance(fake_client, _FakeSTTClient)
    fake_client.emit("new session first chunk")
    time.sleep(0.1)
    client.post("/mic/stop")

    assert "[recent] sample 4 became cloudy after heating" not in captured_contexts[-1]
