"""Request/response schemas for journal API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


JournalSource = Literal["ui_manual", "ui_command"]
JournalEntryType = Literal["general", "observation", "value"]


class HealthResponse(BaseModel):
    status: str
    service: str


class JournalWriteRequest(BaseModel):
    session_id: uuid.UUID
    title: str = Field(min_length=1, max_length=256)
    content: str
    entry_type: JournalEntryType = "general"
    source: JournalSource = "ui_manual"
    metadata: dict[str, Any] = Field(default_factory=dict)


class JournalEntryResponse(BaseModel):
    entry_id: uuid.UUID
    session_id: uuid.UUID
    title: str
    content: str
    entry_type: str
    created_by: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionSummaryResponse(BaseModel):
    session_id: uuid.UUID
    title: str
    latest_created_at: datetime
    latest_entry_id: uuid.UUID
    latest_entry_type: str


class SessionListResponse(BaseModel):
    sessions: list[SessionSummaryResponse]


class HistoryResponse(BaseModel):
    entries: list[JournalEntryResponse]
