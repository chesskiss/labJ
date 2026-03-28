"""Thin orchestration FastAPI service for module integration."""

from __future__ import annotations

import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi import File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import requests

from context_action_plan.llm_parser import (
    get_default_llm_parser,
    parse_transcript_with_fallback,
)
from executor_runtime.executor import execute_validated_output
from orchestration_api.mic_manager import get_mic_manager
from orchestration_api.runtime import get_runtime
from orchestration_api.schemas import (
    HealthResponse,
    MicControlResponse,
    MicEventsResponse,
    MicStartRequest,
    MicStatusResponse,
    ProcessAudioResponse,
    ProcessTextRequest,
    ProcessTextResponse,
    RuntimeStateResponse,
)
from plan_validation.validator import validate_parsed_output

load_dotenv()

app = FastAPI(title="labJ Orchestration API")

cors_origins = os.getenv("ORCHESTRATION_API_CORS_ORIGINS", "*").strip()
allow_origins = (
    [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
    if cors_origins != "*"
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    runtime = get_runtime()
    return HealthResponse(
        status="ok",
        service="orchestration_api",
        components={
            "parser_loaded": True,
            "llm_parser_configured": get_default_llm_parser().is_configured,
            "validator_loaded": True,
            "executor_loaded": True,
            "journal_tool_configured": runtime.journal_write_tool is not None,
        },
    )


@app.post("/process_text", response_model=ProcessTextResponse)
def process_text(payload: ProcessTextRequest) -> ProcessTextResponse:
    try:
        requested_session_id = _parse_optional_session_id(payload.session_id)
        parsed, validation, execution = _run_pipeline(
            payload.text,
            session_id=requested_session_id,
            request_metadata=payload.metadata,
        )
        return ProcessTextResponse(
            parsed=parsed, validation=validation, execution=execution
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "PROCESS_TEXT_FAILED", "message": str(exc)},
        ) from exc


@app.get("/runtime_state", response_model=RuntimeStateResponse)
def runtime_state() -> RuntimeStateResponse:
    runtime = get_runtime()
    return RuntimeStateResponse(
        active_session_exists=runtime.active_session_exists,
        mock_journal_entries_count=len(runtime.journal_entries),
        mock_observations_count=len(runtime.observations),
        journal_tool_enabled=runtime.journal_write_tool is not None,
    )


@app.post("/mic/start", response_model=MicControlResponse)
def mic_start(payload: MicStartRequest) -> MicControlResponse:
    runtime = get_runtime()
    runtime.mic_draft_active = True
    runtime.mic_draft_base_content = None
    runtime.mic_draft_base_initialized = False
    manager = get_mic_manager()
    ok, message = manager.start(
        _run_pipeline,
        language=payload.language,
        stt_api_url=payload.stt_api_url,
        silence_duration=payload.silence_duration,
        silence_threshold=payload.silence_threshold,
    )
    return MicControlResponse(
        ok=ok, message=message, running=manager.status()["running"]
    )


@app.post("/mic/stop", response_model=MicControlResponse)
def mic_stop() -> MicControlResponse:
    runtime = get_runtime()
    runtime.mic_draft_active = False
    runtime.mic_draft_base_content = None
    runtime.mic_draft_base_initialized = False
    manager = get_mic_manager()
    ok, message, full_text = manager.stop()
    return MicControlResponse(
        ok=ok,
        message=message,
        running=manager.status()["running"],
        full_text=full_text,
    )


@app.get("/mic/status", response_model=MicStatusResponse)
def mic_status() -> MicStatusResponse:
    manager = get_mic_manager()
    status = manager.status()
    return MicStatusResponse(**status)


@app.get("/mic/events", response_model=MicEventsResponse)
def mic_events() -> MicEventsResponse:
    manager = get_mic_manager()
    return MicEventsResponse(events=manager.events())


@app.post("/process_audio", response_model=ProcessAudioResponse)
async def process_audio(
    file: UploadFile = File(...),
    language: str | None = Query(default=None),
    beam_size: int = Query(default=5, ge=1, le=10),
    word_timestamps: bool = Query(default=False),
    vad_filter: bool = Query(default=True),
    initial_prompt: str | None = Query(default=None),
) -> ProcessAudioResponse:
    stt_api_url = os.getenv("STT_API_URL", "http://localhost:8001/transcribe")
    try:
        audio_bytes = await file.read()
        files = {
            "file": (
                file.filename or "audio.wav",
                audio_bytes,
                file.content_type or "application/octet-stream",
            )
        }
        params: dict[str, str | int] = {
            "vad_filter": str(vad_filter).lower(),
            "beam_size": beam_size,
            "word_timestamps": str(word_timestamps).lower(),
        }
        if language:
            params["language"] = language
        if initial_prompt:
            params["initial_prompt"] = initial_prompt

        stt_response = requests.post(
            stt_api_url, files=files, params=params, timeout=120
        )
        stt_response.raise_for_status()
        transcription = stt_response.json()

        transcript_text = transcription.get("text", "")
        parsed, validation, execution = _run_pipeline(transcript_text)
        return ProcessAudioResponse(
            transcription=transcription,
            parsed=parsed,
            validation=validation,
            execution=execution,
        )
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail={"error_code": "STT_REQUEST_FAILED", "message": str(exc)},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error_code": "PROCESS_AUDIO_FAILED", "message": str(exc)},
        ) from exc


def _parse_optional_session_id(raw_value: str | None) -> uuid.UUID | None:
    if raw_value is None:
        return None
    trimmed = raw_value.strip()
    if not trimmed:
        return None
    try:
        return uuid.UUID(trimmed)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INVALID_SESSION_ID",
                "message": f"session_id must be a valid UUID: {raw_value}",
            },
        ) from exc


def _run_pipeline(
    text: str,
    session_id: uuid.UUID | None = None,
    request_metadata: dict | None = None,
    context_window_text: str | None = None,
    source: str = "direct",
) -> tuple[dict, dict, dict]:
    metadata = dict(request_metadata or {})
    metadata.setdefault("pipeline_source", source)
    parsed_model = parse_transcript_with_fallback(
        text, context_window_text=context_window_text
    )
    validation_model = validate_parsed_output(parsed_model)
    runtime = get_runtime()
    if session_id is not None:
        runtime.active_session_id = session_id

    runtime.note_capture_metadata = metadata
    title = metadata.get("title")
    runtime.note_capture_title = title if isinstance(title, str) else None

    try:
        execution_model = execute_validated_output(
            parsed_model, validation_model, runtime
        )
        return (
            parsed_model.model_dump(mode="json"),
            validation_model.model_dump(mode="json"),
            execution_model.model_dump(mode="json"),
        )
    finally:
        runtime.note_capture_metadata = {}
        runtime.note_capture_title = None
