"""Mic session manager for continuous STT -> orchestration processing."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
import os
import queue
import threading
from typing import Any, Callable

from stt.stt import STTClient

PipelineFn = Callable[[str], tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]

DEFAULT_STT_TRANSCRIBE_URL = "http://localhost:8001/transcribe"

_MANAGER_SINGLETON: "MicSessionManager | None" = None


class MicSessionManager:
    """Owns a process-wide STT client session and serial processing worker."""

    def __init__(self, max_events: int = 100) -> None:
        self._lock = threading.RLock()
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._client: STTClient | None = None
        self._running = False
        self._pipeline: PipelineFn | None = None
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._processed_count = 0
        self._enqueued_count = 0
        self._last_transcript_at: str | None = None

    def start(
        self,
        pipeline: PipelineFn,
        *,
        language: str | None = None,
        stt_api_url: str | None = None,
        silence_duration: float | None = None,
        silence_threshold: float | None = None,
    ) -> tuple[bool, str]:
        """Start mic session and background worker."""
        with self._lock:
            if self._running:
                return False, "already_running"
            self._pipeline = pipeline
            self._running = True
            self._queue = queue.Queue()
            self._worker = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker.start()

            client_kwargs: dict[str, Any] = {
                "on_transcription": self._on_transcription,
                "language": language,
                "api_url": self._resolve_transcribe_url(stt_api_url),
            }
            if silence_duration is not None:
                client_kwargs["silence_duration"] = silence_duration
            if silence_threshold is not None:
                client_kwargs["silence_threshold"] = silence_threshold

            self._client = STTClient(**client_kwargs)
            self._client.start()
            self._append_event({"type": "session_started"})
            return True, "started"

    def stop(self) -> tuple[bool, str, str]:
        """Stop mic session and worker."""
        with self._lock:
            if not self._running:
                return False, "already_stopped", ""
            self._running = False
            client = self._client
            self._client = None
            self._queue.put(None)

        full_text = ""
        if client is not None:
            full_text = client.stop()
        if self._worker is not None:
            self._worker.join(timeout=30)
            self._worker = None

        self._append_event({"type": "session_stopped", "full_text": full_text})
        return True, "stopped", full_text

    def status(self) -> dict[str, Any]:
        """Return current mic processing state."""
        with self._lock:
            return {
                "running": self._running,
                "queue_length": self._queue.qsize(),
                "processed_chunks": self._processed_count,
                "enqueued_chunks": self._enqueued_count,
                "last_transcript_at": self._last_transcript_at,
            }

    def events(self) -> list[dict[str, Any]]:
        """Return recent bounded event list."""
        with self._lock:
            return list(self._events)

    def _on_transcription(self, text: str) -> None:
        cleaned = (text or "").strip()
        if not cleaned:
            return
        with self._lock:
            self._enqueued_count += 1
            self._last_transcript_at = datetime.now(UTC).isoformat()
            self._append_event({"type": "transcript_enqueued", "text": cleaned})
        self._queue.put(cleaned)

    def _worker_loop(self) -> None:
        while True:
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                with self._lock:
                    if not self._running:
                        break
                continue

            if item is None:
                break

            pipeline = self._pipeline
            if pipeline is None:
                continue

            try:
                parsed, validation, execution = pipeline(item)
                with self._lock:
                    self._processed_count += 1
                    self._append_event(
                        {
                            "type": "chunk_processed",
                            "text": item,
                            "parsed": parsed,
                            "validation": validation,
                            "execution": execution,
                        }
                    )
            except Exception as exc:
                with self._lock:
                    self._append_event(
                        {
                            "type": "chunk_processing_failed",
                            "text": item,
                            "error": {
                                "code": "PIPELINE_ERROR",
                                "message": str(exc),
                                "exception_type": type(exc).__name__,
                            },
                        }
                    )

    def _append_event(self, event: dict[str, Any]) -> None:
        enriched = {
            "timestamp": datetime.now(UTC).isoformat(),
            **event,
        }
        self._events.append(enriched)

    @staticmethod
    def _resolve_transcribe_url(stt_api_url: str | None) -> str:
        raw = stt_api_url or os.getenv("STT_API_URL") or DEFAULT_STT_TRANSCRIBE_URL
        cleaned = raw.rstrip("/")
        if cleaned.endswith("/transcribe"):
            return cleaned
        return f"{cleaned}/transcribe"


def get_mic_manager() -> MicSessionManager:
    """Return process-wide mic manager singleton."""
    global _MANAGER_SINGLETON
    if _MANAGER_SINGLETON is None:
        _MANAGER_SINGLETON = MicSessionManager()
    return _MANAGER_SINGLETON


def reset_mic_manager_for_tests() -> None:
    """Reset mic manager singleton for tests."""
    global _MANAGER_SINGLETON
    if _MANAGER_SINGLETON is not None:
        _MANAGER_SINGLETON.stop()
    _MANAGER_SINGLETON = None
