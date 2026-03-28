"""Request/response models for orchestration API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProcessTextRequest(BaseModel):
    """Input payload for transcript processing."""

    text: str
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProcessTextResponse(BaseModel):
    """End-to-end orchestration response."""

    parsed: dict[str, Any]
    validation: dict[str, Any]
    execution: dict[str, Any]


class ProcessAudioResponse(BaseModel):
    """Audio-to-orchestration response."""

    transcription: dict[str, Any]
    parsed: dict[str, Any]
    validation: dict[str, Any]
    execution: dict[str, Any]


class HealthResponse(BaseModel):
    """Health endpoint response."""

    status: str
    service: str
    components: dict[str, bool]


class RuntimeStateResponse(BaseModel):
    """Runtime observability response."""

    active_session_exists: bool
    mock_journal_entries_count: int
    mock_observations_count: int
    journal_tool_enabled: bool


class MicStartRequest(BaseModel):
    """Start mic session configuration."""

    language: str | None = None
    stt_api_url: str | None = None
    silence_duration: float | None = None
    silence_threshold: float | None = None


class MicControlResponse(BaseModel):
    """Mic start/stop endpoint response."""

    ok: bool
    message: str
    running: bool
    full_text: str | None = None


class MicStatusResponse(BaseModel):
    """Current mic session state."""

    running: bool
    queue_length: int
    enqueued_chunks: int
    processed_chunks: int
    last_transcript_at: str | None = None


class MicEventsResponse(BaseModel):
    """Recent bounded mic events."""

    events: list[dict[str, Any]]
