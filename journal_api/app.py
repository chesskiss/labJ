"""Standalone journal API for manual UI<->DB integration."""

from __future__ import annotations

import os
import uuid
import logging
import time
from datetime import datetime
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request

from db.connection import create_db_engine, create_session_factory
from db.models import Base
from db.repositories.journal_repository import JournalRepository
from journal_api.schemas import (
    HealthResponse,
    HistoryResponse,
    JournalEntryResponse,
    JournalWriteRequest,
    SessionListResponse,
    SessionSummaryResponse,
)

DEFAULT_SQLITE_URL = "sqlite+pysqlite:///data/journal.sqlite"

logger = logging.getLogger("journal_api")


def resolve_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)


@lru_cache(maxsize=1)
def _session_factory_cached():
    database_url = resolve_database_url()
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine, checkfirst=True)
    return create_session_factory(database_url)


def reset_journal_api_state_for_tests() -> None:
    _session_factory_cached.cache_clear()


def _metadata_title(metadata: dict) -> str:
    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return "Untitled Session"


def _open_session():
    session_factory = _session_factory_cached()
    return session_factory()


def _to_entry_response(
    session_id: uuid.UUID,
    entry,
    metadata: dict,
) -> JournalEntryResponse:
    return JournalEntryResponse(
        entry_id=entry.id,
        session_id=session_id,
        title=_metadata_title(metadata),
        content=entry.content,
        entry_type=entry.entry_type,
        created_by=entry.created_by,
        created_at=entry.created_at,
        metadata=metadata,
    )


app = FastAPI(title="labJ Journal API")

cors_origins = os.getenv("JOURNAL_API_CORS_ORIGINS", "*").strip()
allow_origins = (
    ["*"]
    if cors_origins == "*"
    else [o.strip() for o in cors_origins.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    started_at = time.perf_counter()
    logger.info("request:start method=%s path=%s", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "request:exception method=%s path=%s elapsed_ms=%s",
            request.method,
            request.url.path,
            elapsed_ms,
        )
        raise
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info(
        "request:done method=%s path=%s status=%s elapsed_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="journal_api")


@app.post("/journal/entries", response_model=JournalEntryResponse)
def create_journal_entry(payload: JournalWriteRequest) -> JournalEntryResponse:
    logger.info(
        "journal:create_entry session_id=%s source=%s entry_type=%s content_len=%s",
        payload.session_id,
        payload.source,
        payload.entry_type,
        len(payload.content),
    )
    metadata = dict(payload.metadata)
    metadata["source"] = payload.source
    metadata["title"] = payload.title

    with _open_session() as session:
        repo = JournalRepository(session)
        entry = repo.create_entry(
            content=payload.content,
            entry_type=payload.entry_type,
            session_id=payload.session_id,
            metadata=metadata,
            created_by=payload.source,
        )
        return _to_entry_response(payload.session_id, entry, metadata)


@app.get("/journal/sessions", response_model=SessionListResponse)
def list_sessions(
    limit: int = Query(default=100, ge=1, le=500),
) -> SessionListResponse:
    logger.info("journal:list_sessions limit=%s", limit)
    with _open_session() as session:
        repo = JournalRepository(session)
        summaries = repo.list_session_summaries(limit=limit)

    payload = [
        SessionSummaryResponse(
            session_id=item["session_id"],
            title=item["title"],
            latest_created_at=item["latest_created_at"],
            latest_entry_id=item["latest_entry_id"],
            latest_entry_type=item["latest_entry_type"],
        )
        for item in summaries
    ]
    return SessionListResponse(sessions=payload)


@app.get("/journal/sessions/{session_id}/latest", response_model=JournalEntryResponse)
def latest_entry_for_session(session_id: uuid.UUID) -> JournalEntryResponse:
    logger.info("journal:latest_entry session_id=%s", session_id)
    with _open_session() as session:
        repo = JournalRepository(session)
        result = repo.get_latest_entry_by_session(session_id)

    if result is None:
        logger.warning("journal:latest_entry_missing session_id=%s", session_id)
        raise HTTPException(status_code=404, detail="Session has no journal entries")

    entry, metadata = result
    return _to_entry_response(session_id, entry, metadata)


@app.get("/journal/sessions/{session_id}/history", response_model=HistoryResponse)
def session_history(
    session_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=500),
    before: datetime | None = Query(default=None),
) -> HistoryResponse:
    logger.info(
        "journal:session_history session_id=%s limit=%s before=%s",
        session_id,
        limit,
        before.isoformat() if before else None,
    )
    with _open_session() as session:
        repo = JournalRepository(session)
        rows = repo.list_entries_by_session(
            session_id=session_id, limit=limit, before=before
        )

    entries = [
        _to_entry_response(session_id, entry, metadata) for entry, metadata in rows
    ]
    return HistoryResponse(entries=entries)
